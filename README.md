# CI des challenges

Ce dépôt contient le workflow réutilisable et les scripts de validation des challenges. Le dépôt appelant conserve uniquement un workflow GitHub Actions avec ses déclencheurs et ses permissions.

Le workflow détecte les challenges modifiés et leurs stacks partagées, puis vérifie pour chacun le manifeste, les images, le build, le démarrage, les contrôles de santé et la solution disponible. Chaque challenge est testé dans un job indépendant.

## Utilisation

L'adresse ci-dessous est celle du prototype public. Elle sera remplacée par celle du dépôt central PolyCyber lors du transfert.

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main, qa-branch]
permissions:
  contents: read
  actions: read
  pull-requests: write
jobs:
  ci:
    uses: pep28/PolyPwnCTF-2026-Challenges/.github/workflows/challenge-ci.yml@COMMIT_DU_WORKFLOW
```

Fixer `COMMIT_DU_WORKFLOW` au commit publié. Le workflow récupère ses scripts au commit indiqué dans ses deux étapes `actions/checkout`. Lors d'une mise à jour, publier les scripts, remplacer ce commit dans le workflow, puis mettre à jour la référence dans le dépôt appelant. Le transfert vers un nouveau dépôt nécessite aussi d'actualiser ces deux champs `repository` une seule fois dans le workflow central.

L'option `polycyber: false` désactive les contrôles propres aux champs de déploiement PolyCyber. L'option `tous: true` teste tous les challenges ; par défaut, seuls les challenges modifiés et ceux qui dépendent d'une stack modifiée sont testés.

Un fichier `.challenge-ci.yml` facultatif dans un challenge permet d'indiquer une stack partagée, un override Compose, le service et le port cibles, des contrôles supplémentaires ou une raison de ne pas exécuter une solution. Les solutions exécutables se nomment `solution/solve.py` ou `solution/solve.sh` et reçoivent `CHALLENGE_HOST` et `CHALLENGE_PORT`. Une solution absente est indiquée comme ignorée. Les règles complètes et les exemples sont dans le document `CI-changes.md` et les exemples du dépôt 2026.

## Tests locaux

```sh
python -m pip install PyYAML==6.0.2
PYTHONPATH=. python -m unittest discover -s tests
```

Les tests de déploiement nécessitent un environnement Linux isolé avec Docker et Docker Compose. Les images et les services des challenges sont construits et exécutés pendant la CI.
