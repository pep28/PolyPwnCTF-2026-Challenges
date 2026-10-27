#!/usr/bin/env python3
"""Check challenge.yml syntax and the fields used by PolyPwn."""
from pathlib import Path
import sys
import yaml

REQUIRED = ("name", "author", "category", "type", "value", "description", "flags")
TEXT_FIELDS = ("name", "author", "category", "type", "description")

def main():
    files = sorted(Path(".").rglob("challenge.yml"))
    errors = []
    if not files:
        print("Aucun challenge.yml trouvé.")
        return 1

    for path in files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            errors.append(f"{path}: YAML invalide: {exc}")
            continue

        if not isinstance(data, dict):
            errors.append(f"{path}: le document doit être un objet YAML.")
            continue

        missing = [key for key in REQUIRED if key not in data or data[key] in (None, "")]
        if missing:
            errors.append(f"{path}: champs manquants: {', '.join(missing)}")

        for key in TEXT_FIELDS:
            if key in data and not isinstance(data[key], str):
                errors.append(f"{path}: {key} doit être du texte.")

        if "value" in data and type(data["value"]) is not int:
            errors.append(f"{path}: value doit être un entier.")

        flags = data.get("flags")
        if flags is not None:
            valid_flags = (
                isinstance(flags, str) and bool(flags.strip())
            ) or (
                isinstance(flags, list)
                and bool(flags)
                and all(isinstance(flag, (str, dict)) for flag in flags)
            )
            if not valid_flags:
                errors.append(f"{path}: flags doit être une chaîne ou une liste de flags.")

        for key in ("tags", "files", "hints"):
            value = data.get(key)
            if value is not None and not isinstance(value, list):
                errors.append(f"{path}: {key} doit être une liste.")

        attempts = data.get("attempts")
        if attempts is not None and (type(attempts) is not int or attempts < 0):
            errors.append(f"{path}: attempts doit être un entier positif ou nul.")

        for key in ("playbook_name", "deploy_parameters"):
            value = data.get(key)
            if value is not None and not isinstance(value, (str if key == "playbook_name" else dict)):
                expected = "du texte" if key == "playbook_name" else "un objet"
                errors.append(f"{path}: {key} doit être {expected}.")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"{len(files)} challenge.yml valides.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
