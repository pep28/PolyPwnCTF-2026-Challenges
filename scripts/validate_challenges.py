#!/usr/bin/env python3
"""Check challenge.yml files for valid YAML and the fields used by PolyPwn."""
from pathlib import Path
import sys
import yaml

REQUIRED = ("name", "author", "category", "type", "value", "description", "flags")

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
        if "value" in data and not isinstance(data["value"], int):
            errors.append(f"{path}: value doit être un entier.")
        if "flags" in data and not isinstance(data["flags"], (str, list)):
            errors.append(f"{path}: flags doit être une chaîne ou une liste.")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"{len(files)} challenge.yml valides.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
