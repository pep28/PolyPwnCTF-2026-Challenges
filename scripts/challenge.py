import json
import http.client
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time

import yaml

from validate_challenges import validate


COMPOSE = ('compose.yaml', 'compose.yml', 'docker-compose.yaml', 'docker-compose.yml')
etape = 'manifeste'
logs = []


def run(args, cwd=None, capture=False, timeout=600, env=None):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, timeout=timeout, env=env)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:4])} : {(result.stdout or '') + (result.stderr or '') or 'commande échouée'}")
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
    try:
        run(['docker', 'buildx', 'imagetools', 'inspect', image], capture=True, timeout=120)
    except RuntimeError as exc:
        raise ValueError(f'Image introuvable ou privée : {image}. Vérifier le nom ou ajouter un build local.') from exc


def manifest_ports(data):
    params = data.get('deploy_parameters') or {}
    if not isinstance(params, dict):
        return []
    ports = []
    for key in ('http_port', 'tcp_port', 'port'):
        if isinstance(params.get(key), int):
            ports.append(params[key])
    for item in params.get('published_ports', []):
        if isinstance(item, int):
            ports.append(item)
        elif isinstance(item, str) and item.split(':')[-1].isdigit():
            ports.append(int(item.split(':')[-1]))
    return sorted(set(ports))


def compose_ports(service, exposed=()):
    ports = [int(p['target']) for p in service.get('ports', []) if p.get('protocol', 'tcp') == 'tcp']
    for value in list(service.get('expose', [])) + list(exposed):
        value = str(value)
        port, _, protocol = value.partition('/')
        if port.isdigit() and protocol in ('', 'tcp'):
            ports.append(int(port))
    return sorted(set(ports))


def service_ports(data, service):
    params = data.get('deploy_parameters') or {}
    if not isinstance(params, dict) or not isinstance(params.get('expose', []), list):
        return []
    return [item['port'] for item in params.get('expose', [])
            if isinstance(item, dict) and item.get('service') == service
            and item.get('type') in ('http', 'tcp') and isinstance(item.get('port'), int)]


def selected_ports(service, declared, configured, inherited):
    if not declared and not configured and not compose_ports(service):
        declared = inherited
    return sorted(set(compose_ports(service, declared) + configured))


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


def dockerfile_ports(path):
    ports = []
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\s*EXPOSE\s+(.+?)\s*$', line, re.I)
        if match:
            ports.extend(compose_ports({}, match.group(1).split()))
    return sorted(set(ports))


def probe(container, host, check):
    if 'command' in check:
        run(['docker', 'exec', container, *check['command']], capture=True, timeout=10)
    elif 'http' in check:
        conn = http.client.HTTPConnection(host, check['port'], timeout=5)
        try:
            conn.request('GET', check['http'])
            response = conn.getresponse()
            body = response.read().decode(errors='replace')
            if response.status != check.get('status', 200) or check.get('contains', '') not in body:
                raise RuntimeError(f"Réponse HTTP inattendue : {response.status}")
        finally:
            conn.close()
    else:
        with socket.create_connection((host, check['port']), timeout=5) as conn:
            if check.get('send'):
                conn.sendall(check['send'].encode())
            if check.get('contains') and check['contains'].encode() not in conn.recv(65536):
                raise RuntimeError('Réponse TCP inattendue.')


def wait(container, ports, checks=()):
    deadline = time.monotonic() + 120
    error = 'Service non disponible'
    successes = 0
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
            for check in checks:
                probe(container, address, check)
            successes += 1
            if successes == 2:
                return address
            time.sleep(2)
        except (OSError, RuntimeError, subprocess.SubprocessError, http.client.HTTPException) as exc:
            error = str(exc)
            successes = 0
            time.sleep(2)
    raise RuntimeError(f'Délai de démarrage dépassé : {error}')


def solution(directory, data, host, port, config=None):
    config = config or {}
    if config.get('ignore_solution'):
        print(f"Solution ignorée : {config['ignore_solution']}")
        return
    scripts = sorted(path for path in (directory / 'solution').glob('solve.*')
                     if path.suffix.lower() not in ('.md', '.txt'))
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
    try:
        output = run(commands[script.suffix], cwd=script.parent, capture=True, timeout=90, env=env)
    except RuntimeError as exc:
        raise ValueError(f'La solution a échoué : {exc}') from exc
    print(output)
    flags = data.get('flags', [])
    if isinstance(flags, str):
        flags = [flags]
    for flag in flags:
        if isinstance(flag, str) and flag in output:
            return
        if isinstance(flag, dict):
            value = flag.get('content', '')
            options = re.IGNORECASE if flag.get('data') == 'case_insensitive' else 0
            if flag.get('type') == 'regex' and re.search(value, output, options):
                return
            if flag.get('type') != 'regex' and value and re.search(re.escape(value), output, options):
                return
    raise ValueError('Solution terminée, mais aucun flag trouvé dans sa sortie.')


def main():
    global etape
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
    etape = 'détection du déploiement'
    config_file = directory / '.challenge-ci.yml'
    config = yaml.safe_load(config_file.read_text(encoding='utf-8')) if config_file.is_file() else {}
    if not isinstance(config, dict):
        raise ValueError('.challenge-ci.yml doit être un objet YAML.')
    stack = (root / config.get('stack', os.environ['CHEMIN'])).resolve()
    if not stack.is_relative_to(root) or not (stack / 'challenge.yml').is_file():
        raise ValueError('Stack partagée introuvable ou hors du dépôt.')
    stack_data = yaml.safe_load((stack / 'challenge.yml').read_text(encoding='utf-8'))
    compose_file = next((stack / name for name in COMPOSE if (stack / name).is_file()), None)
    dockerfile = stack / 'Dockerfile'
    params = stack_data.get('deploy_parameters') or {}
    image = params.get('image') if isinstance(params, dict) else None
    definition = params.get('compose_definition') if isinstance(params, dict) else None
    temporary = None
    if not compose_file and definition:
        definition = yaml.safe_load(definition) if isinstance(definition, str) else definition
        temporary = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', encoding='utf-8', delete=False)
        with temporary:
            yaml.safe_dump(definition, temporary)
        compose_file = Path(temporary.name)
    if not compose_file and not dockerfile.is_file() and not image:
        if data.get('type') == 'zync':
            raise ValueError('Déploiement déclaré sans recette ou image identifiable.')
        etape = 'solution'
        solution(directory, data, None, None, config)
        return
    name = 'ci-' + str(os.getpid())
    containers = []
    compose = None
    try:
        etape = 'images'
        if compose_file:
            compose = ['docker', 'compose', '-p', name, '--project-directory', str(stack), '-f', str(compose_file)]
            if config.get('compose_override'):
                override = (directory / config['compose_override']).resolve()
                if not override.is_relative_to(root) or not override.is_file():
                    raise ValueError('Override Compose introuvable ou hors du dépôt.')
                compose += ['-f', str(override)]
            definition = json.loads(run(compose + ['config', '--format', 'json'], cwd=stack, capture=True))
            declared_ports = {}
            for name_service, service in definition['services'].items():
                build = service.get('build')
                if build:
                    context = Path(build.get('context', stack)) if isinstance(build, dict) else Path(build)
                    if not context.is_absolute():
                        context = stack / context
                    recipe = build.get('dockerfile', 'Dockerfile') if isinstance(build, dict) else 'Dockerfile'
                    dockerfile_images(context / recipe)
                    declared_ports[name_service] = dockerfile_ports(context / recipe)
                elif service.get('image'):
                    check_image(service['image'])
                else:
                    raise ValueError('Service Compose sans image ni build.')
            etape = 'build et démarrage'
            print(run(compose + ['up', '-d', '--build'], cwd=stack, timeout=1200, capture=True))
            etape = 'santé des services'
            addresses = []
            for name_service, service in definition['services'].items():
                ids = run(compose + ['ps', '-q', name_service], cwd=stack, capture=True).splitlines()
                if len(ids) != 1:
                    raise ValueError(f'{name_service} : un conteneur attendu, {len(ids)} trouvé(s).')
                containers.extend(ids)
                info = json.loads(run(['docker', 'inspect', ids[0]], capture=True))[0]
                exposed = declared_ports.get(name_service, [])
                configured = service_ports(stack_data, name_service)
                inherited = (info['Config'].get('ExposedPorts') or {}).keys()
                ports = selected_ports(service, exposed, configured, inherited)
                address = wait(ids[0], ports, config.get('checks', {}).get(name_service, []))
                addresses.append((name_service, address, ports[0] if ports else None))
            target = config.get('service')
            if target and target not in [item[0] for item in addresses]:
                raise ValueError(f'Service cible inconnu : {target}')
            _, host, port = next((item for item in addresses if item[0] == target),
                                 next((item for item in addresses if item[2]), addresses[0]))
        else:
            if dockerfile.is_file():
                dockerfile_images(dockerfile)
                etape = 'build'
                print(run(['docker', 'build', '-t', name, str(stack)], timeout=1200, capture=True))
                image = name
            else:
                check_image(image)
                run(['docker', 'pull', image], timeout=300)
            etape = 'démarrage'
            container = run(['docker', 'run', '-d', '--name', name, image], capture=True)
            containers.append(container)
            info = json.loads(run(['docker', 'inspect', container], capture=True))[0]
            exposed = dockerfile_ports(dockerfile) if dockerfile.is_file() else []
            if not exposed and not manifest_ports(stack_data):
                exposed = compose_ports({}, (info['Config'].get('ExposedPorts') or {}).keys())
            ports = sorted(set(manifest_ports(stack_data) + exposed))
            etape = 'santé du service'
            host = wait(container, ports, config.get('checks', {}).get('app', []))
            port = ports[0] if ports else None
        print('Démarrage vérifié.', flush=True)
        etape = 'solution'
        solution(directory, data, host, config.get('port', port), config)
    finally:
        for container in containers:
            result = subprocess.run(['docker', 'logs', '--tail', '50', container], capture_output=True, text=True, check=False)
            logs.append((result.stdout + result.stderr)[-5000:])
            print(logs[-1])
        if compose:
            subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], cwd=stack, check=False)
        elif containers:
            subprocess.run(['docker', 'rm', '-f', *containers], check=False)
        if temporary:
            Path(temporary.name).unlink(missing_ok=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        print(f'Échec : {exc}', file=sys.stderr)
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a', encoding='utf-8') as output:
                output.write(f"### Échec : {os.environ.get('CHEMIN', '')}\n\nÉtape : {etape}\n\n{str(exc)[-5000:]}\n")
                if logs:
                    output.write('\nDerniers journaux :\n\n```text\n' + '\n'.join(logs) + '\n```\n')
        sys.exit(1)
