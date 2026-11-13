# CI des challenges

La CI valide les challenges modifiés lors des pull requests et des pushs sur `main` et `qa-branch`. Le fichier `.github/workflows/ci-generique.yml` appelle le workflow partagé à un commit précis.

La source partagée est provisoirement hébergée sur la branche `ci/central-autonome` du fork. Son transfert vers le dépôt central PolyCyber et la mise à jour du commit appelé restent nécessaires avant adoption.

## Vérifications

Pour chaque challenge, la CI valide `challenge.yml`, détecte le déploiement, vérifie les images, construit et démarre les services, puis vérifie leur santé et la solution disponible. Les images de registre doivent être accessibles et fixées par version ou digest. Un Dockerfile ou un build Compose local est prioritaire.

Un fichier facultatif `.challenge-ci.yml` à côté du manifeste peut définir des contrôles spécifiques `checks`, un `compose_override`, une `stack` partagée, le `service` et le `port` de la solution ou une raison `ignore_solution`. Les fichiers existants donnent des exemples.

Une solution automatisée utilise `solution/solve.py` ou `solution/solve.sh`, lit `CHALLENGE_HOST` et `CHALLENGE_PORT` et affiche un flag du manifeste. Ses dépendances Python sont déclarées dans `solution/requirements.txt`. Une solution absente ou explicitement ignorée est indiquée dans les journaux et le résumé du challenge.

## Pull requests

La CI produit un résultat global `ci / resultat`, un résumé par job et un commentaire mis à jour sur la PR lorsque les permissions le permettent. Les contributions provenant de forks peuvent disposer d'un jeton en lecture seule : dans ce cas le commentaire peut être indisponible, mais les résultats des jobs restent visibles.

Les protections du fork demandent encore les checks `validate`, `docker-build` et `compose-build`. Trois jobs de compatibilité reprennent ces noms et échouent si le workflow partagé échoue. Ils conservent la protection existante. Un administrateur pourra ensuite demander le check global `ci / resultat` et retirer ces jobs.

## Validation

La version précédente du workflow a passé les 56 challenges 2026. Les contrôles spécifiques des 18 challenges concernés ont ensuite été testés avec la CI générique. Les tests de non-régression du moteur s'exécutent dans le workflow partagé.
