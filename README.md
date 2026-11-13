# CI des challenges

Ce code contient un workflow GitHub Actions réutilisable et ses scripts. Chaque dépôt de challenges conserve un petit workflow d'appel, sans copie des scripts et sans inventaire `deployments.yml`.

Le prototype est hébergé sur la branche `ci/central-autonome` de `pep28/PolyPwnCTF-2026-Challenges`. Ce n'est pas encore un dépôt central distinct.

## Utilisation

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

Remplacer `COMMIT_DU_WORKFLOW` par le commit publié. Le dépôt appelant garde ses déclencheurs. `polycyber: false` désactive les règles de manifeste propres à PolyCyber. `tous: true` force la vérification de tous les challenges.

Les modifications d'un challenge ou de sa stack sélectionnent les challenges concernés. Une modification des workflows relance tous les challenges, pour vérifier aussi les mises à jour de CI. Chaque challenge s'arrête au premier échec ; les autres continuent dans leurs jobs séparés.

## Vérifications

Le moteur valide le manifeste et ses fichiers, détecte Docker ou Compose, contrôle les images, construit les services, attend leur démarrage et lance la solution disponible. Un build local est prioritaire sur une image de registre. Les images externes doivent être publiques et avoir une version explicite ou un digest. Les références d'images non résolues sont refusées.

Les ports viennent du manifeste, de Compose ou d'EXPOSE. Le contrôle attend un conteneur actif, son healthcheck s'il existe et les ports TCP déclarés. Les contrôles supplémentaires restent facultatifs.

Une solution utilise `solution/solve.py` ou `solution/solve.sh`, lit `CHALLENGE_HOST` et `CHALLENGE_PORT`, puis écrit le flag sur stdout ou stderr avec un code de sortie nul. Les dépendances Python sont dans `solution/requirements.txt`. Les flags statiques et regex sont pris en charge. Une solution absente est indiquée comme ignorée : un job vert ne signifie donc pas forcément que le challenge a été résolu.

## Options du challenge

Un fichier `.challenge-ci.yml` à côté du manifeste peut définir :

| Champ | Rôle |
| --- | --- |
| `stack` | Chemin de la stack partagée depuis la racine du dépôt |
| `compose_override` | Fichier Compose supplémentaire, relatif au challenge |
| `service` | Service à utiliser comme cible de la solution |
| `port` | Port cible de la solution |
| `ignore_solution` | Raison textuelle du saut de la solution |
| `checks` | Contrôles supplémentaires, regroupés par service ; `app` pour un Dockerfile seul |

```yaml
service: web
port: 8080
checks:
  web:
    - port: 8080
      http: /health
      status: 200
      contains: ready
```

Un contrôle TCP définit `port`, éventuellement `send` et `contains`. Un contrôle exécuté dans le conteneur définit `command` sous forme de liste. Les chemins de stack et d'override doivent rester dans le dépôt.

## Rapports et confidentialité

Le résumé du job indique l'étape et la raison de l'échec. Le commentaire de PR est mis à jour avec les statuts et les liens des jobs, si les permissions le permettent. La CI ne recopie pas les logs dans ce commentaire. Les sorties des solutions, des builds, des dépendances et des conteneurs ne sont pas affichées par le moteur, y compris en cas d'échec. Les erreurs YAML indiquent la position sans reprendre le contenu du fichier. Le diagnostic détaillé d'une commande se fait dans un environnement local autorisé.

Les jobs qui exécutent les challenges ont un jeton en lecture seule et ne conservent pas les identifiants du checkout. Seul le job de rapport demande l'écriture sur les PR ; il ne récupère ni n'exécute le code du challenge. Aucun secret de déploiement ou de registre n'est nécessaire ni transmis par le workflow. Ne pas ajouter `secrets: inherit` ou exécuter les contributions avec `pull_request_target`.

Le dépôt central peut être public sans y copier les challenges. Le code du challenge reste récupéré dans le contexte de son dépôt appelant. Les noms, configurations et messages saisis dans ce dépôt restent soumis à sa visibilité. Ces précautions ne remplacent pas la revue de ce qui est commité et ne nettoient pas les anciennes exécutions.

## Publication dans le dépôt central

Exporter uniquement `.github/workflows/challenge-ci.yml`, `scripts/`, `tests/` et ce README depuis cette branche, sans copier l'historique ni les fichiers des challenges. Créer un dépôt central vide avec la visibilité décidée par l'équipe.

1. Publier les scripts et les tests dans ce dépôt.
2. Dans les deux checkouts du workflow central, remplacer `repository` par le nouveau dépôt et `ref` par le commit des scripts.
3. Publier le workflow et tester un appel depuis un second dépôt.
4. Publier une version `v1`, puis remplacer l'adresse du prototype dans les appelants.

Un tag majeur `v1` maintenu par l'équipe permet de diffuser les correctifs depuis le seul dépôt central. Un SHA fixe fige exactement une révision, mais sa mise à jour doit être reportée dans les appelants. Le prototype utilise un SHA pour rendre les validations reproductibles.

## Tests

```sh
python -m pip install PyYAML==6.0.2
PYTHONPATH=. python -m unittest discover -s tests
```

Les tests de déploiement demandent un runner Linux isolé avec Docker et Docker Compose. Le code des challenges et des solutions y est exécuté ; les tests de PR ne doivent pas recevoir d'identifiants de production.
