# Correctifs 2025

Les correctifs s'appliquent à la révision `606c0158e7cbffa5bc4f65c7a82e5edbccfe2ec4` de l'édition 2025. Depuis une copie de cette révision, avec les trois patches dans le même dossier :

```sh
git apply --check /chemin/2025-images.patch /chemin/interstellar-2025.patch /chemin/2025-dockerfiles.patch
git apply /chemin/2025-images.patch /chemin/interstellar-2025.patch /chemin/2025-dockerfiles.patch
```

- `2025-images.patch` fixe les images flottantes aux digests relevés dans les builds précédents.
- `interstellar-2025.patch` corrige le build d'Interstellar2 et fixe ses dépendances.
- `2025-dockerfiles.patch` renomme `dockerfile` en `Dockerfile` pour exMachinhack, hackladdin1 et hackladdin2. La CI construit ces trois services depuis le code du dépôt et vérifie leur démarrage. Aucune image de challenge à récupérer dans un registre.

## Vérifications

Le [test du 23 novembre](https://github.com/pep28/PolyPwnCTF-2026-Challenges/actions/runs/45250083027) applique les trois correctifs dans le runner sur une copie des sources officielles. 55 challenges sur 57 passent. Le build et le démarrage passent pour les trois services dont le fichier a été renommé.

Deux fichiers distribués aux joueurs manquent sur la révision testée :

| Challenge | Fichier attendu |
| --- | --- |
| Trésor National | `Forensic/TresorNational/files/chall.zip` |
| Up - Photos souvenirs | `Forensic/Up - Photos souvenirs/files/UpChall.zip` |

Le lien de téléchargement indiqué par le second manifeste a renvoyé une 404 lors de la vérification. Pour refaire le test avec les données d'origine, les archives doivent être fournies au runner depuis un emplacement approuvé par l'équipe. La vérification du manifeste continue d'échouer si le fichier manque.
