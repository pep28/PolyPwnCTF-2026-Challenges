import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

import yaml

from validate_challenges import validate


COMPOSE = ('compose.yaml', 'compose.yml', 'docker-compose.yaml', 'docker-compose.yml')


def run(args, cwd=None, capture=False, timeout=600, env=None):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.STDOUT if capture else None, timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:4])} : {result.stdout or 'commande échouée'}")
    return result.stdout.strip() if capture else ''


def check_image(image):
    if image == 'scratch' or image.startswith('${'):
        if image != 'scratch':
            raise ValueError(f'Image non résolue : {image}')
        return
    name = image.split('@', 1)[0]
    tag = name.rsplit('/', 1)[-1]
    if '@sha256:' not in image and (':' not in tag or not re.search(r'\d', tag.rsplit(':', 1)[1])):
        raise ValueError(f'Image sans version explicite : {image}')
    run(['docker', 'buildx', 'imagetools', 'inspect', image], capture=True, timeout=120)


def dockerfile_images(path):
    stages = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?', line, re.I)
        if match:
            image, stage = match.groups()
            if image.lower() not in stages:
                check_image(image)
            if stage:
                stages.add(stage.lower())


def wait(container, ports):
    deadline = time.monotonic() + 120
    error = 'Service non disponible'
    while time.monotonic() < deadline:
        info = json.loads(run(['docker', 'inspect', container], capture=True))[0]
        state = info['State']
        if state['Status'] in ('exited', 'dead'):
            raise RuntimeError(f"Conteneur arrêté : {state['ExitCode']}")
        addresses = [item.get('IPAddress') for item in info['NetworkSettings']['Networks'].values()]
        address = next((ip for ip in addresses if ip), None)
        health = state.get('Health', {}).get('Status')
        try:
            if state['Status'] != 'running' or health not in (None, 'healthy'):
                raise RuntimeError(f"État : {state['Status']}, santé : {health}")
            if ports and not address:
                raise RuntimeError('Adresse du conteneur absente.')
            for port in ports:
                with socket.create_connection((address, port), timeout=2):
                    pass
            return address
        except (OSError, RuntimeError) as exc:
            error = str(exc)
            time.sleep(2)
    raise RuntimeError(f'Délai de démarrage dépassé : {error}')


def solution(directory, data, host, port):
    scripts = sorted((directory / 'solution').glob('solve.*'))
    if not scripts:
        print('Solution ignorée : aucun fichier solution/solve.*.')
        return
    if len(scripts) != 1:
        raise ValueError('Un seul fichier solution/solve.* est attendu.')
    script = scripts[0]
    requirements = script.parent / 'requirements.txt'
    if requirements.is_file():
        run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)])
    commands = {'.py': [sys.executable, str(script)], '.sh': ['bash', str(script)]}
    if script.suffix not in commands:
        raise ValueError(f'Langage de solution non pris en charge : {script.suffix}')
    env = os.environ | {'CHALLENGE_HOST': host or '', 'CHALLENGE_PORT': str(port or '')}
    output = run(commands[script.suffix], cwd=script.parent, capture=True, timeout=90, env=env)
    print(output)
    flags = data.get('flags', [])
    if isinstance(flags, str):
        flags = [flags]
    for flag in flags:
        if isinstance(flag, str) and flag in output:
            return
        if isinstance(flag, dict):
            value = flag.get('content', '')
            if flag.get('type') == 'regex' and re.search(value, output):
                return
            if flag.get('type') != 'regex' and value and value in output:
                return
    raise ValueError('Solution terminée, mais aucun flag trouvé dans sa sortie.')


def main():
    root = (Path(os.environ['GITHUB_WORKSPACE']) / 'challenges').resolve()
    directory = (root / os.environ['CHEMIN']).resolve()
    if not directory.is_relative_to(root) or not (directory / 'challenge.yml').is_file():
        raise ValueError('Chemin de challenge invalide.')
    manifest = directory / 'challenge.yml'
    errors = validate(manifest, os.environ.get('POLYCYBER', 'true') == 'true')
    if errors:
        raise ValueError('\n'.join(errors))
    data = yaml.safe_load(manifest.read_text(encoding='utf-8'))
    print('Manifeste valide.', flush=True)
    compose_file = next((directory / name for name in COMPOSE if (directory / name).is_file()), None)
    dockerfile = directory / 'Dockerfile'
    params = data.get('deploy_parameters') or {}
    image = params.get('image') if isinstance(params, dict) else None
    if not compose_file and not dockerfile.is_file() and not image:
        if data.get('type') == 'zync':
            raise ValueError('Déploiement déclaré sans recette ou image identifiable.')
        solution(directory, data, None, None)
        return
    name = 'ci-' + str(os.getpid())
    containers = []
    compose = None
    try:
        if compose_file:
            compose = ['docker', 'compose', '-p', name, '-f', str(compose_file)]
            definition = json.loads(run(compose + ['config', '--format', 'json'], cwd=directory, capture=True))
            for service in definition['services'].values():
                build = service.get('build')
                if build:
                    context = Path(build.get('context', directory)) if isinstance(build, dict) else Path(build)
                    if not context.is_absolute():
                        context = directory / context
                    recipe = build.get('dockerfile', 'Dockerfile') if isinstance(build, dict) else 'Dockerfile'
                    dockerfile_images(context / recipe)
                elif service.get('image'):
                    check_image(service['image'])
                else:
                    raise ValueError('Service Compose sans image ni build.')
            run(compose + ['up', '-d', '--build'], cwd=directory, timeout=1200)
            addresses = []
            for name_service, service in definition['services'].items():
                ids = run(compose + ['ps', '-q', name_service], cwd=directory, capture=True).splitlines()
                if len(ids) != 1:
                    raise ValueError(f'{name_service} : un conteneur attendu, {len(ids)} trouvé(s).')
                containers.extend(ids)
                ports = [int(p['target']) for p in service.get('ports', []) if p.get('protocol', 'tcp') == 'tcp']
                address = wait(ids[0], ports)
                addresses.append((address, ports[0] if ports else None))
            host, port = next(((h, p) for h, p in addresses if p), addresses[0])
        else:
            if dockerfile.is_file():
                dockerfile_images(dockerfile)
                run(['docker', 'build', '-t', name, str(directory)], timeout=1200)
                image = name
            else:
                check_image(image)
                run(['docker', 'pull', image], timeout=300)
            container = run(['docker', 'run', '-d', '--name', name, image], capture=True)
            containers.append(container)
            info = json.loads(run(['docker', 'inspect', container], capture=True))[0]
            ports = [int(p.split('/')[0]) for p in (info['Config'].get('ExposedPorts') or {}) if p.endswith('/tcp')]
            host = wait(container, ports)
            port = ports[0] if ports else None
        print('Démarrage vérifié.', flush=True)
        solution(directory, data, host, port)
    finally:
        for container in containers:
            subprocess.run(['docker', 'logs', '--tail', '50', container], check=False)
        if compose:
            subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], cwd=directory, check=False)
        elif containers:
            subprocess.run(['docker', 'rm', '-f', *containers], check=False)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        print(f'Échec : {exc}', file=sys.stderr)
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a', encoding='utf-8') as output:
                output.write(f"### Échec : {os.environ.get('CHEMIN', '')}\n\n{exc}\n")
        sys.exit(1)
