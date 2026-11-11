import json
import os
from pathlib import Path
import subprocess


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
    return [str(path.parent.relative_to(root)) for path in files
            if any(item == path.parent.relative_to(root) or path.parent.relative_to(root) in item.parents for item in changed)]


def main():
    root = Path(os.environ['GITHUB_WORKSPACE']) / 'challenges'
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    paths = discover(root, event)
    print(f'{len(paths)} challenge(s) modifié(s).')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'matrix={json.dumps(paths, ensure_ascii=True)}\n')
        output.write(f'count={len(paths)}\n')


if __name__ == '__main__':
    main()
