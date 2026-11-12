import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


def discover(root, event):
    files = sorted(root.rglob('challenge.yml'))
    if not files:
        raise ValueError('Aucun challenge.yml trouvé.')
    if event.get('pull_request'):
        base = event['pull_request']['base']['sha']
    else:
        base = event.get('before', '')
    if not base or set(base) == {'0'}:
        return [str(path.parent.relative_to(root)) for path in files]
    result = subprocess.run(
        ['git', '-C', str(root), 'diff', '--name-only', '-z', base, 'HEAD'],
        check=True, stdout=subprocess.PIPE,
    )
    changed = [Path(os.fsdecode(path)) for path in result.stdout.split(b'\0') if path]
    for item in changed:
        if item.name == 'challenge.yml' and not (root / item).exists() and (root / item.parent).is_dir():
            raise ValueError(f'Manifeste supprimé alors que le dossier existe encore : {item}')
    selected = set()
    for path in files:
        directory = path.parent.relative_to(root)
        config_file = path.parent / '.challenge-ci.yml'
        config = yaml.safe_load(config_file.read_text(encoding='utf-8')) if config_file.is_file() else {}
        if not isinstance(config, dict):
            raise ValueError(f'{config_file} doit être un objet YAML.')
        stack = Path(config.get('stack', str(directory)))
        if any(item == candidate or candidate in item.parents for item in changed for candidate in (directory, stack)):
            selected.add(str(directory))
    return sorted(selected)


def main():
    root = Path(os.environ['GITHUB_WORKSPACE']) / 'challenges'
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    paths = discover(root, event)
    print(f'{len(paths)} challenge(s) modifié(s).')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'matrix={json.dumps(paths, ensure_ascii=True)}\n')
        output.write(f'count={len(paths)}\n')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        print(f'Échec de la détection : {exc}', file=sys.stderr)
        sys.exit(1)
