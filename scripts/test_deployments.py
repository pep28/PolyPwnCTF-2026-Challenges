import argparse
import hashlib
import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import time

import yaml


COMPOSE_NAMES = ('compose.yaml', 'compose.yml', 'docker-compose.yaml', 'docker-compose.yml')


def run(*args, capture=False, timeout=600):
    result = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None, timeout=timeout)
    return result.stdout.strip() if capture else None


def inspect(container):
    return json.loads(run('docker', 'inspect', container, capture=True))[0]


def probe(container, check):
    if 'command' in check:
        run('docker', 'exec', container, *check['command'], capture=True, timeout=5)
        return
    info = inspect(container)
    host = next(net['IPAddress'] for net in info['NetworkSettings']['Networks'].values() if net['IPAddress'])
    port = check['port']
    if 'http' in check:
        conn = http.client.HTTPConnection(host, port, timeout=3)
        try:
            conn.request(check.get('method', 'GET'), check['http'], headers=check.get('headers', {}))
            response = conn.getresponse()
            body = response.read(1048576).decode(errors='replace')
            if response.status != check.get('status', 200):
                raise RuntimeError(f'HTTP {response.status} on {port}{check["http"]}')
        finally:
            conn.close()
    else:
        with socket.create_connection((host, port), timeout=5) as conn:
            if 'send' in check:
                conn.sendall(check['send'].encode())
            if check.get('eof'):
                conn.shutdown(socket.SHUT_WR)
            data = b''
            while len(data) < 65536:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if check.get('contains', '').encode() in data:
                    break
            body = data.decode(errors='replace')
            if not body and not check.get('eof'):
                raise RuntimeError(f'No response on TCP {port}')
    if check.get('contains', '') not in body:
        raise RuntimeError(f'Unexpected response on port {port}')


def wait_ready(containers, checks, timeout=120):
    deadline = time.monotonic() + timeout
    error = 'Services not ready'
    successes = 0
    while time.monotonic() < deadline:
        try:
            for service, container in containers.items():
                state = inspect(container)['State']
                if state['Status'] in ('exited', 'dead'):
                    raise ValueError(f'{service}: container exited ({state["ExitCode"]})')
                if state['Status'] != 'running':
                    raise RuntimeError(f'{service}: {state["Status"]}')
                health = state.get('Health')
                if health and health['Status'] != 'healthy':
                    raise RuntimeError(f'{service}: {health["Status"]}')
                if not checks.get(service) and not health:
                    raise ValueError(f'{service}: no healthcheck or response test configured')
                for check in checks.get(service, []):
                    probe(container, check)
            successes += 1
            if successes == 2:
                return
        except (OSError, RuntimeError, subprocess.SubprocessError, http.client.HTTPException) as exc:
            error = str(exc)
            successes = 0
        time.sleep(2)
    raise RuntimeError(f'Readiness timeout: {error}')


def test(root, path, config, mode):
    directory = root / path
    name = 'ci-' + hashlib.sha256(path.encode()).hexdigest()[:12]
    containers = {}
    compose = None
    try:
        if mode == 'compose':
            compose_file = next(directory / f for f in COMPOSE_NAMES if (directory / f).is_file())
            compose = ['docker', 'compose', '-p', name, '-f', str(compose_file)]
            if config.get('override'):
                compose += ['-f', str(root / config['override'])]
            definition = json.loads(run(*compose, 'config', '--format', 'json', capture=True))
            expected = set(definition['services'])
            if set(config['services']) != expected:
                raise ValueError(f'Service checks must cover {sorted(expected)}')
            run(*compose, 'up', '-d', '--build', timeout=1200)
            for service in expected:
                ids = run(*compose, 'ps', '-a', '-q', service, capture=True).splitlines()
                if len(ids) != 1:
                    raise ValueError(f'{service}: expected one container, got {len(ids)}')
                containers[service] = ids[0]
            checks = config['services']
        else:
            image = name
            if (directory / 'Dockerfile').is_file():
                run('docker', 'build', '-t', name, str(directory), timeout=1200)
            else:
                image = config['image']
                run('docker', 'pull', image, timeout=300)
            args = ['docker', 'run', '-d', '--name', name]
            for port in config.get('publish', []):
                args += ['-p', f'127.0.0.1:{port}:{port}']
            containers['app'] = run(*args, image, capture=True)
            checks = {'app': config['checks']}
        wait_ready(containers, checks)
        for solution in config.get('solutions', []):
            run(sys.executable, str(Path(__file__).with_name('check_solution.py')), str(root / solution[0]), str(root / solution[1]), timeout=500)
        print(f'PASS: {path}', flush=True)
    finally:
        for container in containers.values():
            subprocess.run(['docker', 'logs', '--tail', '50', container], check=False, timeout=15)
        if compose:
            subprocess.run([*compose, 'logs', '--tail', '30', '--no-color'], check=False, timeout=30)
            run(*compose, 'down', '--volumes', '--remove-orphans', timeout=60)
        else:
            subprocess.run(['docker', 'rm', '-f', name], check=False, timeout=30)
            if (directory / 'Dockerfile').is_file():
                subprocess.run(['docker', 'image', 'rm', name], check=False, timeout=30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['docker', 'compose'])
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--config', type=Path, default=Path('.github/ci/deployments.yml'))
    args = parser.parse_args()
    root = args.root.resolve()
    config = yaml.safe_load(args.config.read_text())
    discovered = set()
    for manifest in root.rglob('challenge.yml'):
        directory = manifest.parent
        compose = any((directory / f).is_file() for f in COMPOSE_NAMES)
        data = yaml.safe_load(manifest.read_text())
        deployed = isinstance(data, dict) and data.get('type') == 'zync'
        if (args.mode == 'compose' and compose) or (args.mode == 'docker' and not compose and ((directory / 'Dockerfile').is_file() or deployed)):
            discovered.add(directory.relative_to(root).as_posix())
    entries = config[args.mode]
    if set(entries) != discovered:
        print(f'Deployment inventory mismatch: missing={sorted(discovered - set(entries))}, extra={sorted(set(entries) - discovered)}')
        return 1
    failures = []
    for path, settings in entries.items():
        print(f'::group::{path}', flush=True)
        try:
            test(root, path, settings, args.mode)
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            failures.append(path)
            print(f'::error::{path}: {exc}', flush=True)
        finally:
            print('::endgroup::', flush=True)
    print(f'{len(entries) - len(failures)}/{len(entries)} deployments passed; failed: {failures}')
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
