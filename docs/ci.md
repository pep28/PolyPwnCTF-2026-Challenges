# CI des challenges

La pipeline tourne sur les pull requests et sur les pushes vers `main` et `qa-branch`.

## Contrôles

| Job | Vérifications |
| --- | --- |
| `validate` | Tests de non-régression, structure des 56 manifestes, champs imbriqués et présence des fichiers distribués. |
| `docker-build` | Build, démarrage et réponses des 11 challenges sans Compose, puis solution de Labo Rinthe. |
| `compose-build` | Build et démarrage des six projets Compose, santé de chaque service, puis solutions de CatLab 1, CatLab 2 et Vault13. |

Les champs suivent l'[exemple ctfcli](https://github.com/CTFd/ctfcli/blob/master/ctfcli/spec/challenge-example.yml), avec les champs PolyCyber `playbook_name` et `deploy_parameters`. Le validateur vérifie les flags simples et objets, tags, topics, hints, requirements, fichiers, score dynamique, état et métadonnées de déploiement. Les clés YAML répétées sont refusées. L'ancien format Compose avec `deploy_parameters.expose` est accepté si un fichier Compose existe.

Ce validateur ne remplace pas l'installation sur CTFd : il ne vérifie pas les plugins du serveur, les références entre challenges, le calcul CFSS ou le contenu des archives. Pour Git LFS, la présence du fichier suivi est vérifiée, pas le téléchargement de son contenu.

## Démarrage et santé

`scripts/test_deployments.py` utilise `.github/ci/deployments.yml`. L'inventaire doit correspondre aux Dockerfiles et fichiers Compose placés à côté des `challenge.yml`, ainsi qu'aux challenges `zync` utilisant une image préconstruite. Un nouveau déploiement découvert sans entrée dans cet inventaire fait échouer le job. Les Dockerfiles imbriqués sont construits lorsqu'un Compose les référence ; les recettes alternatives imbriquées ne sont pas lancées séparément.

Chaque service Compose doit avoir ses propres contrôles ou un healthcheck Docker. Aucun projet n'est ignoré parce qu'il utilise une image préconstruite : Docker doit pouvoir la récupérer et la démarrer.

Les tests attendent au maximum 120 secondes, puis exigent deux passages réussis espacés de deux secondes. Ils vérifient les réponses HTTP, les bannières ou réponses TCP, les healthchecks Docker et certaines commandes internes. Un conteneur arrêté échoue immédiatement. Les tests couvrent aussi le backend de DNA Visualizer, les deux services de Vault13, MariaDB et SSH dans Rabb-IT, la base CatLab et son service interne.

Les conteneurs sont supprimés après chaque test, y compris en cas d'erreur. Les volumes Compose sont supprimés. Exécuter ces tests dans un environnement dédié, sans services ni données de travail à conserver. Les tests utilisent les adresses du réseau Docker et ciblent un runner Linux.

Les solutions sont exécutées par `scripts/check_solution.py` : sortie sans erreur et présence d'un flag du manifeste. Le script effectue au maximum cinq essais de 90 secondes. Les quatre solutions testées ne prouvent pas la résolution de tous les challenges ; les contrôles de santé vérifient leur disponibilité.

## Passage par QA

1. Créer une branche de travail depuis `qa-branch`.
2. Ouvrir une PR vers `qa-branch`.
3. Corriger les erreurs jusqu'à ce que `validate`, `docker-build` et `compose-build` passent.
4. Après la revue QA, ouvrir une PR de `qa-branch` vers `main`.

Les deux branches du fork sont protégées par la règle [Require CI on main](https://github.com/pep28/PolyPwnCTF-2026-Challenges/rules/25928381). Elle impose une PR et les trois contrôles GitHub Actions, interdit les suppressions et les force-pushes, sans contournement. Le chemin par QA est une convention documentée ; la règle ne bloque pas une PR directe vers main et n'impose pas de revue humaine. Les protections GitHub ne sont pas copiées avec le code.

## Tester

Depuis la racine du dépôt, avec Python 3.12 et Docker Compose :

```sh
python -m pip install PyYAML requests
python -m unittest discover -s tests
python scripts/validate_challenges.py
python scripts/test_deployments.py docker
python scripts/test_deployments.py compose
```

Pour un nouveau service, ajouter ses contrôles dans `.github/ci/deployments.yml`. Utiliser une route HTTP normale et son code attendu, une réponse TCP stable ou une commande interne qui échoue si le service n'est pas prêt. Ajouter un test pour chaque service, même sans port publié. Les ports publiés fixes sont réservés aux scripts de solution qui en ont besoin.

## Résultats et intégration

La [PR de test #2](https://github.com/pep28/PolyPwnCTF-2026-Challenges/pull/2) a confirmé qu'un manifeste invalide bloque la fusion. Les contrôles de démarrage et la validation renforcée sont dans la [PR #5](https://github.com/pep28/PolyPwnCTF-2026-Challenges/pull/5).

Cette CI teste les challenges sur les runners GitHub. Elle ne déploie pas l'infrastructure PolyCyber. L'intégration au dépôt officiel nécessite une revue de l'équipe et une PR ; ses protections doivent être configurées par un administrateur.
