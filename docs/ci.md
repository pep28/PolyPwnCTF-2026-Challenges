# CI des challenges

La CI valide les challenges modifiés lors des pull requests et des pushs sur `main` et `qa-branch`. `.github/workflows/ci-generique.yml` appelle un workflow partagé à un commit précis. Il ne reste aucun script de CI à recopier dans le dépôt de challenges et aucun inventaire `deployments.yml`.

Le code partagé est provisoirement sur la branche `ci/central-autonome` du fork. Le moteur est indépendant des challenges 2026. La création du dépôt central PolyCyber, son premier appel depuis un autre dépôt et la mise à jour de l'adresse appelée restent à faire avant adoption.

## Vérifications

Pour chaque challenge : manifeste, détection du déploiement, images, build, démarrage, santé puis solution. Le premier échec arrête ce challenge. Les autres jobs continuent. Un changement de stack sélectionne aussi les challenges qui en dépendent ; un changement de workflow relance tous les challenges.

Un Dockerfile ou un build Compose local est prioritaire. Les images externes doivent être publiques et versionnées. Le manifeste peut aussi contenir une définition Compose. Les ports viennent du manifeste, de Compose ou d'EXPOSE. Les healthchecks existants sont pris en compte.

Le fichier facultatif `.challenge-ci.yml` définit les cas particuliers : `checks`, `compose_override`, `stack`, `service`, `port` ou une raison textuelle `ignore_solution`. Les contrôles des 18 challenges déjà couverts ont été déplacés à côté de leurs manifestes.

Une solution utilise `solution/solve.py` ou `solution/solve.sh`, reçoit `CHALLENGE_HOST` et `CHALLENGE_PORT` et écrit un flag du manifeste. Les dépendances Python sont dans `solution/requirements.txt`. Les flags statiques et regex sont reconnus sur stdout et stderr. Un code non nul et un flag absent donnent deux erreurs distinctes.

Six solutions sont automatisées : Labo Rinthe, Vault13, CatLab 1, CatLab 2, Dexter 2 et Dexter 3. Une solution absente ou explicitement ignorée est indiquée comme telle dans le résumé. Un job vert ne signifie donc pas que toutes les solutions ont été exécutées.

## Pull requests

La CI produit `ci / resultat`, des résumés par job et un commentaire mis à jour sur la PR. Pour une contribution provenant d'un fork, le commentaire peut être indisponible avec le jeton en lecture seule ; les checks restent visibles.

Les protections actuelles demandent `validate`, `docker-build` et `compose-build`. Trois petits jobs de compatibilité portent ces noms et échouent si la CI partagée échoue. Les protections existantes restent effectives. Leur suppression nécessite que l'administrateur exige d'abord le check global de la nouvelle CI.

## Confidentialité

Le moteur n'affiche plus les sorties des solutions, des builds, de l'installation de leurs dépendances ou des conteneurs. Il ne reprend pas ces sorties dans les erreurs. Les erreurs YAML indiquent la ligne et la colonne sans copier le fichier. Le commentaire de PR contient les statuts, l'étape du job en échec et les liens, sans extrait de logs.

Les tests tournent sans secret de déploiement ou de registre transmis. Les checkouts ne conservent pas leurs identifiants. L'écriture sur les PR est limitée au job de rapport, qui ne récupère ni n'exécute le code des challenges. Les noms de challenges et les raisons rédigées dans leur configuration restent visibles selon les permissions du dépôt. Aucun changement de visibilité n'est effectué. Les anciennes exécutions ne sont pas nettoyées par cette modification.

## Validation et intégration

Le moteur possède 26 tests unitaires, dont des tests de non-publication des sorties et des flags. Ils s'exécutent aussi dans GitHub Actions. Les résultats de la révision proposée sont dans l'onglet Checks de la PR. Le guide `presentation-ci.md` rassemble la démonstration et les points restant à valider par l'équipe.

Les noms d'images locales des manifestes doivent être confirmés avec le système de déploiement PolyCyber avant fusion. Cette CI vérifie les builds et le fonctionnement local ; elle ne publie pas les images et ne déploie pas en production.
