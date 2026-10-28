import argparse
from pathlib import Path
import re
import sys

import yaml


class Loader(yaml.SafeLoader):
    pass


def mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise yaml.YAMLError('Les clés doivent être du texte.')
        if key in result:
            raise yaml.YAMLError(f'Clé répétée : {key}')
        result[key] = loader.construct_object(value_node)
    return result


Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value):
    return type(value) is int and value >= 0


def validate(path):
    errors = []
    try:
        data = yaml.load(path.read_text(encoding='utf-8'), Loader=Loader)
    except (yaml.YAMLError, OSError, UnicodeError) as exc:
        return [f'YAML invalide : {exc}']
    if not isinstance(data, dict):
        return ['Le document doit être un objet YAML.']
    for key in ('name', 'author', 'category', 'type', 'description'):
        if not text(data.get(key)):
            errors.append(f'{key} doit être du texte non vide.')
    if not integer(data.get('value')):
        errors.append('value doit être un entier positif ou nul.')
    for key in ('attempts',):
        if key in data and not integer(data[key]):
            errors.append(f'{key} doit être un entier positif ou nul.')
    for key in ('image', 'host', 'protocol', 'connection_info', 'attribution', 'version', 'module'):
        if data.get(key) is not None and not text(data[key]):
            errors.append(f'{key} doit être du texte non vide ou null.')
    for key, choices in [('state', ('hidden', 'visible')), ('logic', ('any', 'all', 'team'))]:
        if key in data and data[key] not in choices:
            errors.append(f'{key} doit être parmi {choices}.')
    flags = data.get('flags')
    if isinstance(flags, str):
        flags = [flags]
    if not isinstance(flags, list) or not flags:
        errors.append('flags doit contenir au moins un flag.')
    else:
        for flag in flags:
            if isinstance(flag, str):
                if not text(flag):
                    errors.append('Un flag est vide.')
            elif isinstance(flag, dict):
                if not text(flag.get('type')) or not text(flag.get('content')):
                    errors.append('Chaque flag objet doit avoir type et content non vides.')
                if 'data' in flag and not isinstance(flag['data'], str):
                    errors.append('flag.data doit être du texte.')
                if flag.get('type') == 'regex' and text(flag.get('content')):
                    try:
                        re.compile(flag['content'])
                    except re.error:
                        errors.append('Expression régulière de flag invalide.')
            else:
                errors.append('Un flag doit être du texte ou un objet.')
    for key in ('tags', 'topics', 'files'):
        if key in data and (not isinstance(data[key], list) or not all(text(item) for item in data[key])):
            errors.append(f'{key} doit être une liste de textes non vides.')
    if 'file' in data:
        errors.append('Utiliser files, pas file.')
    if isinstance(data.get('files'), list):
        for item in data['files']:
            if not text(item):
                continue
            target = (path.parent / item).resolve()
            if not target.is_relative_to(path.parent.resolve()) or not target.is_file():
                errors.append(f'Fichier absent ou hors du challenge : {item}')
    hints = data.get('hints', [])
    if not isinstance(hints, list):
        errors.append('hints doit être une liste.')
    else:
        for hint in hints:
            if isinstance(hint, str) and text(hint):
                continue
            if not isinstance(hint, dict) or not text(hint.get('content')):
                errors.append('Un hint doit contenir du texte non vide.')
            elif 'cost' in hint and not integer(hint['cost']):
                errors.append('hint.cost doit être un entier positif ou nul.')
    requirements = data.get('requirements', [])
    if isinstance(requirements, dict):
        if 'anonymize' in requirements and type(requirements['anonymize']) is not bool:
            errors.append('requirements.anonymize doit être un booléen.')
        requirements = requirements.get('prerequisites')
    if not isinstance(requirements, list) or not all(text(item) or (type(item) is int and item > 0) for item in requirements):
        errors.append('requirements doit contenir des noms ou des identifiants de challenges.')
    extra = data.get('extra', {})
    if not isinstance(extra, dict):
        errors.append('extra doit être un objet.')
    elif data.get('type') == 'dynamic':
        if not all(integer(extra.get(key)) for key in ('initial', 'decay', 'minimum')) or extra.get('decay', 0) == 0:
            errors.append('extra doit définir initial, decay > 0 et minimum pour un challenge dynamic.')
        elif extra['minimum'] > extra['initial']:
            errors.append('extra.minimum ne peut pas dépasser extra.initial.')
    if data.get('type') == 'zync' or 'deploy_parameters' in data:
        if not text(data.get('playbook_name')):
            errors.append('playbook_name doit être du texte non vide.')
        params = data.get('deploy_parameters')
        if not isinstance(params, dict):
            errors.append('deploy_parameters doit être un objet.')
        else:
            if 'unique' in params and type(params['unique']) is not bool:
                errors.append('deploy_parameters.unique doit être un booléen.')
            if data.get('playbook_name') == 'custom_compose':
                definition = params.get('compose_definition')
                try:
                    if isinstance(definition, str):
                        definition = yaml.load(definition, Loader=Loader)
                    if not isinstance(definition, dict) or not isinstance(definition.get('services'), dict) or not definition['services']:
                        errors.append('compose_definition doit définir des services.')
                except yaml.YAMLError as exc:
                    errors.append(f'compose_definition invalide : {exc}')
            elif not text(params.get('image')):
                errors.append('deploy_parameters.image doit être du texte non vide.')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', type=Path, default=Path('.'))
    args = parser.parse_args()
    files = sorted(args.root.rglob('challenge.yml'))
    errors = [f'{path}: {error}' for path in files for error in validate(path)]
    if not files:
        errors.append('Aucun challenge.yml trouvé.')
    print('\n'.join(errors) if errors else f'{len(files)} challenge.yml valides.')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
