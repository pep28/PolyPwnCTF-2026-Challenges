# Présentation de la CI générique

La revue se fait sur la [PR 8 du fork](https://github.com/pep28/PolyPwnCTF-2026-Challenges/pull/8). Elle est en brouillon et n'est pas fusionnée. Le dépôt officiel n'est pas modifié.

## Ce qui a changé

| Demande | Résultat |
| --- | --- |
| Une seule CI réutilisable | Workflow `workflow_call` et scripts réunis dans une branche autonome ; un appel dans le dépôt 2026 |
| Plus d'inventaire écrit à la main | Suppression de `deployments.yml`, détection des manifestes, Dockerfiles, Compose et stacks partagées |
| Un traitement par challenge modifié | Matrice automatique, arrêt du challenge au premier échec, autres challenges indépendants |
| Versions des images | Images externes contrôlées, références flottantes corrigées, builds locaux prioritaires |
| Contrôles conservés | Contrôles particuliers déplacés près des challenges, healthchecks et ports détectés |
| Solutions portables | Cible par variables d'environnement, six solutions automatisées, sauts justifiés, flags regex pris en charge |
| Rapport de PR | Commentaire mis à jour, résumé par job, protections existantes conservées |
| Confidentialité des sorties | Sorties brutes non affichées par le moteur ; pas de logs copiés dans le commentaire |

## Démo en cinq minutes

1. Ouvrir [le workflow appelant](https://github.com/pep28/PolyPwnCTF-2026-Challenges/blob/ci/integration-generique/.github/workflows/ci-generique.yml). Montrer `uses:` : le dépôt de challenges ne contient pas les scripts du moteur. Les trois jobs supplémentaires assurent seulement la compatibilité avec les checks déjà obligatoires.
2. Ouvrir [la branche autonome](https://github.com/pep28/PolyPwnCTF-2026-Challenges/tree/ci/central-autonome). Elle contient uniquement le workflow, les scripts, leurs tests et le README. Le README décrit l'installation et le transfert vers le dépôt central.
3. Ouvrir [les checks de la PR](https://github.com/pep28/PolyPwnCTF-2026-Challenges/pull/8/checks). Montrer la matrice et `ci / resultat`. Une modification du workflow sélectionne tous les challenges, ce qui vérifie aussi les mises à jour de CI.
4. Comparer le résumé de Dexter 3, dont la solution est exécutée, avec un challenge sans script : son résumé indique « ignorée ». Le résultat de la solution est distinct du succès des vérifications de build et de démarrage. Ne pas afficher de flag ou de logs historiques pendant la démo.
5. Montrer les checks du [test de manifeste invalide](https://github.com/pep28/PolyPwnCTF-2026-Challenges/actions/runs/43343968635), puis du [même test corrigé](https://github.com/pep28/PolyPwnCTF-2026-Challenges/actions/runs/43344085654). Les trois checks obligatoires échouent puis passent avec la CI partagée. Ces tests historiques précèdent la limitation des sorties.

Phrase de présentation : « J'ai déplacé le moteur de CI à un seul endroit. Chaque dépôt l'appelle avec un petit workflow, et les challenges sont détectés automatiquement. Les cas particuliers restent à côté du challenge. Les déclencheurs et les vérifications déjà validés sont conservés. »

## Résultats à lire correctement

Le moteur comporte 26 tests unitaires. La dernière exécution de la PR donne l'état exact de la révision proposée ; la description de la PR contient les liens des validations finales.

La précédente validation complète 2026 avait passé 56 challenges. Cela ne signifiait pas 56 solutions exécutées. Six solutions sont automatisées dans la version proposée ; les autres sont signalées comme absentes ou ignorées.

Sur 2025, la validation complète du moteur après application temporaire des correctifs avait donné 52 réussites sur 57. Les sources officielles sont seulement récupérées dans un runner de test. Les correctifs restent sur [ci/correctifs-2025](https://github.com/pep28/PolyPwnCTF-2026-Challenges/tree/ci/correctifs-2025), sans modification du dépôt officiel.

Les cinq blocages connus sont :

| Challenge ou référence | Blocage |
| --- | --- |
| `Forensic/TresorNational` | Archive `files/chall.zip` absente des sources récupérées |
| `Forensic/Up - Photos souvenirs` | Archive `files/UpChall.zip` absente des sources récupérées |
| `exmachinhack` | Image sans version explicite |
| `hackladdin1` | Image sans version explicite |
| `hackladdin2` | Image sans version explicite |

La vérification de version arrête ces trois derniers cas avant le contrôle du registre. Leur accessibilité actuelle n'est donc pas établie par ce test. Aucun challenge n'a été retiré pour rendre la CI verte.

## Ce qui reste pour l'adoption

Le code est préparé pour la revue. Le déploiement définitif demande encore :

- La création du dépôt central avec la visibilité choisie par l'équipe, puis l'export des seuls fichiers de CI. Aucun historique ou fichier de challenge ne doit être copié dans le dépôt central public.
- La mise à jour des deux checkouts internes du workflow et de l'adresse appelée. Un tag majeur `v1` permet ensuite de diffuser les correctifs depuis le dépôt central ; un SHA fixe exige une mise à jour volontaire des appelants.
- Un vrai test d'appel entre deux dépôts. Le prototype et l'appelant 2026 sont actuellement dans le même fork, sur des références séparées. Le test 2025 valide le moteur sur d'autres sources, pas encore cette distribution entre dépôts.
- La confirmation des noms d'images locales pour le déploiement PolyCyber et la résolution des cinq blocages 2025 avec les fichiers ou références autorisés.

Les droits disponibles dans cette session ne permettent pas de créer le dépôt central. La PR n'est pas fusionnée tant que les points d'intégration ci-dessus ne sont pas validés.
