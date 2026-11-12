# CI générique : branche de travail

Cette branche prépare un workflow réutilisable dans `.github/workflows/challenge-ci.yml`. La CI actuelle reste active et les protections existantes ne sont pas modifiées.

Le workflow récupère le dépôt appelant et le code de la CI séparément. Il repère les challenges modifiés, les teste en parallèle et fournit un résultat global stable. Pour chaque challenge, il valide le manifeste, contrôle les versions des images, construit et démarre les services détectés, puis cherche une solution `solution/solve.py` ou `solution/solve.sh`. Le flag de sortie peut être statique ou une expression régulière.

La branche est une étape de développement. L'adresse `pep28/PolyPwnCTF-2026-Challenges@ci/generic-shared` est provisoire et doit être remplacée par le dépôt central avant distribution. Le workflow récupère ses scripts à un commit précis. Lors d'une modification des scripts, leur commit doit être mis à jour dans le workflow, puis l'appelant doit référencer le commit du nouveau workflow.

Les déclencheurs se définissent dans le dépôt appelant. Pour les conserver sur le fork 2026 :

```yaml
name: CI générique
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
    uses: pep28/PolyPwnCTF-2026-Challenges/.github/workflows/challenge-ci.yml@ci/generic-shared
```

## À terminer avant adoption

- Tester le workflow sur les autres challenges des éditions 2025 et 2026. Labo Rinthe, Vault13 et les deux CatLab ont passé leurs tests de déploiement et de solution sur GitHub Actions, dans une branche de test.
- Vérifier sur les autres challenges les ports des manifestes et Compose, les tests de santé spécifiques, les stacks partagées et les overrides.
- Prendre en charge les définitions Compose intégrées aux manifestes, les arguments `FROM` et les images construites par plusieurs Dockerfiles. Valider l'accès aux registres réels.
- Migrer les solutions existantes vers `solution/solve.*` et tester leurs dépendances ainsi que leurs cibles. Une solution absente est signalée comme ignorée.
- Vérifier la mise à jour du commentaire de PR en cas d'échec et les permissions pour les PR provenant de forks.
- Épingler les images existantes et corriger les références privées avec l'équipe. Supprimer `deployments.yml` seulement après avoir retrouvé la couverture de la CI actuelle.
- Publier le code central dans un dépôt accessible aux projets utilisateurs et mettre à jour les appels et les protections GitHub après validation.

## Vérifications locales

```sh
python -m pip install PyYAML==6.0.2
python -m unittest discover -s tests
```

## Options par challenge

Le fichier facultatif `.challenge-ci.yml` peut définir `stack` (chemin de la stack partagée depuis la racine), `service` et `port` (cible de la solution), `compose_override` (chemin relatif au challenge) et `ignore_solution` (raison de l'absence de test). `checks` peut définir des contrôles `http`, TCP ou `command` par service. Ces options sont en cours de validation et ne remplacent pas encore les contrôles de la CI existante.
