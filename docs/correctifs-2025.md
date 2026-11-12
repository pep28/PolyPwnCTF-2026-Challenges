# Correctifs 2025

Ces deux correctifs sont prévus pour le commit 2025 `606c0158e7cbffa5bc4f65c7a82e5edbccfe2ec4`. Ils n'ont pas été appliqués au dépôt officiel.

- `2025-images.patch` fixe les images flottantes aux digests observés lors des builds précédents.
- `interstellar-2025.patch` corrige le build Interstellar2 et fixe ses dépendances.

Ils ont été appliqués temporairement sur une copie des sources pendant les tests. Les archives de Trésor National et Up - Photos souvenirs manquent toujours. Les images exMachinhack, hackladdin1 et hackladdin2 restent à examiner avec l'équipe.

Dans une copie de travail du dépôt 2025 placée sur le commit ci-dessus, appliquer les deux correctifs avec `git apply`. Vérifier les changements et relancer la CI avant de les proposer à PolyCyber.
