# CI des challenges

Le workflow `.github/workflows/validate-challenges.yml` tourne sur les pull requests et sur les pushes vers `main` et `qa-branch`.

## Contrôles

| Job | Ce qui est vérifié |
| --- | --- |
| `validate` | Lecture des `challenge.yml`, champs obligatoires et types des valeurs. |
| `docker-build` | Build des `Dockerfile` placés à côté d'un `challenge.yml`, puis démarrage et résolution de Labo Rinthe. |
| `compose-build` | Configuration des fichiers Compose, build et démarrage des projets constructibles localement, puis résolution de CatLab 1, CatLab 2 et Vault13. |

Le validateur demande `name`, `author`, `category`, `type`, `value`, `description` et `flags`. Il contrôle aussi les types de `tags`, `files`, `hints`, `attempts`, `playbook_name` et `deploy_parameters` lorsqu'ils sont présents. Ce sont des contrôles de structure, pas une validation complète du schéma ctfcli ou du contenu des fichiers référencés.

Compose attend au maximum 120 secondes le démarrage des services. Les healthchecks sont pris en compte lorsqu'ils existent ; sans healthcheck, un conteneur démarré ne garantit pas que l'application répond. Pour CatLab, `.github/ci/catlab-compose.yml` ajoute les builds locaux et un healthcheck HTTP pour le service web.

Les solutions sont lancées avec `scripts/check_solution.py`. Le script exige une sortie sans erreur et la présence d'un flag déclaré dans le manifeste. Il effectue au maximum cinq essais de 90 secondes, espacés de deux secondes.

## Passage par QA

1. Créer une branche de travail depuis `qa-branch`.
2. Ouvrir une PR vers `qa-branch`.
3. Corriger les erreurs jusqu'à ce que `validate`, `docker-build` et `compose-build` soient verts, puis fusionner.
4. Ouvrir une PR de `qa-branch` vers `main` pour intégrer les changements validés.

Dans le fork `pep28/PolyPwnCTF-2026-Challenges`, les deux branches sont protégées par la règle [Require CI on main](https://github.com/pep28/PolyPwnCTF-2026-Challenges/rules/25928381). Elle impose une PR et les trois contrôles GitHub Actions, interdit les suppressions et les force-pushes, et ne prévoit aucun contournement. Les règles de protection sont des réglages GitHub : elles ne sont pas copiées avec le code.

## Tester localement

Depuis la racine du dépôt, avec Python 3.12 :

```sh
python -m pip install PyYAML requests
python scripts/validate_challenges.py
```

Pour reproduire les tests CatLab avec Docker et Compose :

```sh
docker compose -f "Web/CatLab 1/docker-compose.yml" -f .github/ci/catlab-compose.yml up -d --build --wait --wait-timeout 120
python scripts/check_solution.py "Web/CatLab 1" "Web/CatLab 1/solution/solve.py"
python scripts/check_solution.py "Pwn/CatLab 2" "Pwn/CatLab 2/solution/solve.py"
docker compose -f "Web/CatLab 1/docker-compose.yml" -f .github/ci/catlab-compose.yml down --volumes --remove-orphans
```

La dernière commande supprime les conteneurs et les volumes de cette instance de test. Utiliser une instance dédiée si des données locales doivent être conservées.

## En cas d'échec

Ouvrir le job en échec dans l'onglet Actions. `validate` indique le fichier et le champ concernés. Pour Docker, lire l'erreur de build ou les logs du service. Pour une solution, vérifier que le service est prêt, que le script fonctionne sans saisie interactive et que sa sortie correspond au flag du manifeste. Corriger la branche de travail et pousser un nouveau commit relance la CI de la PR.

## Couverture et limites

- Les 56 manifestes présents lors de la mise en place passent la validation. Les 16 Dockerfiles à la racine des challenges sont construits et les six projets Compose démarrent dans la CI du fork.
- Quatre solutions sont exécutées : CatLab 1, CatLab 2, Vault13 et Labo Rinthe. Les autres ne sont pas encore couvertes par un test de résolution.
- Un projet Compose dont au moins un service n'a pas de build local est vérifié et ses builds disponibles sont lancés, mais son démarrage est ignoré avec un message explicite.
- Un `Dockerfile` imbriqué n'est pas construit automatiquement par `docker-build` ; il doit être référencé par un projet Compose pour être couvert par ce workflow.
- Cette CI teste les challenges sur les runners GitHub. Elle ne déploie pas l'infrastructure PolyCyber.

## Vérification du blocage

Le 27 octobre 2026, la [PR de test #2](https://github.com/pep28/PolyPwnCTF-2026-Challenges/pull/2) a introduit un manifeste temporaire dont `value` était une chaîne. Le job `validate` a échoué avec `value doit être un entier.` et GitHub a placé la PR dans l'état `blocked`.

Résultats : [exécution du test négatif](https://github.com/pep28/PolyPwnCTF-2026-Challenges/actions/runs/40445100021). La [CI initiale sur main](https://github.com/pep28/PolyPwnCTF-2026-Challenges/actions/runs/40443277868) avait passé les trois contrôles.

## Intégration chez PolyCyber

Ouvrir une PR depuis le fork vers le dépôt officiel pour proposer les fichiers du workflow, les scripts, les corrections de challenges et cette documentation. Un administrateur du dépôt officiel doit ensuite configurer les protections sur `main` et `qa-branch`, avec les contrôles `validate`, `docker-build` et `compose-build` provenant de GitHub Actions, puis reproduire le test de blocage. Aucun de ces réglages du dépôt officiel n'est appliqué depuis ce fork.
