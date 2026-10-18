# ⚡ Torrent Generator (C411 & Multi-Trackers)

[![Docker Build & Push](https://github.com/hollow313/Torrent_generator/actions/workflows/docker-build.yml/badge.svg)](https://github.com/hollow313/Torrent_generator/actions/workflows/docker-build.yml)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20ARM64%20%7C%20AMD64-blue)
![Base Image](https://img.shields.io/badge/Base-Alpine%203.12-green)
![Port](https://img.shields.io/badge/Port-30017-orange)
![User](https://img.shields.io/badge/User-apps%20(568:568)-purple)

Application web conteneurisée et automatisée conçue pour préparer, générer et uploader des releases torrents conformes aux règles strictes du tracker **C411** (et extensible à d'autres trackers), avec injection directe dans **qBittorrent** pour le seed immédiat depuis votre NAS (TrueNAS SCALE, Synology, Unraid, etc.).

---

## 🌟 Fonctionnalités Principales

- 🖥️ **Interface Web Moderne sur le port `30017`** : Thème sombre réactif, explorateur de fichiers, éditeurs en direct NFO et BBCode.
- 📁 **Explorateur de fichiers NAS** : Naviguez dans vos disques montés (ex: `/mnt/Plex/Plex/films/`), sélectionnez un fichier ou un dossier complet en un clic.
- 📐 **Conformité stricte aux Règles C411** :
  - **Nommage normalisé** : Séparateur par point (`.`), suppression des accents et caractères non autorisés.
  - **Règle Anti-DETAG & Gestion Sonarr / Radarr** : 
    - Si Sonarr ou Radarr a renommé vos fichiers (en supprimant le tag d'origine du nom), le système inspecte automatiquement les **métadonnées internes du MKV** (titre de piste, header), le dossier parent et les éventuels fichiers `.nfo` associés pour **restaurer le tag d'origine** !
    - Si aucun tag n'est trouvable, le suffixe obligatoire `-NOTAG` est automatiquement appliqué comme requis par la Team Pending de C411.
  - **Gestion Séries & Mangas Flexible** :
    - Option de publication en **Pack Complet** (1 seul torrent pour toute la saison ou intégrale, ou pack de tomes manga).
    - Option de publication **Épisode par épisode / Tome par tome** : le système liste tous les fichiers du dossier et permet de traiter chaque épisode individuellement avec son propre NFO et son propre torrent.
  - **Taille des pièces (Pieces)** : Calcul dynamique selon le barème officiel C411 :
    - < 1 Go : **1 Mo**
    - < 2 Go : **2 Mo**
    - < 3 Go : **4 Mo**
    - < 8 Go : **8 Mo**
    - > 8 Go : **16 Mo**
  - **Tracker de secours inclus** : Annonce principale (`https://c411.org/announce/<passkey>`) et announce de secours (`https://tk.c411.tw/announce/<passkey>`).
  - **Flag Privé** : Verrouillé à `1`.
- 🔍 **Vérificateur Avancé de Doublons C411** :
  - Interroge en temps réel l'API Torznab de C411.
  - Compare la **résolution**, la **source** et la **team** :
    - 🔴 **Doublon strict détecté** : avertissement immédiat avec le nombre de seeders pour éviter un refus par la modération.
    - 🟡 **Version différente autorisée** : confirme que la qualité (ex: 2160p UHD ou Remux) apporte une version distincte légitime selon les règles C411.
    - 🟢 **Feu vert** : aucun doublon existant.
- 🎬 **Intégration TMDB** : Récupère automatiquement l'affiche officielle (poster), le synopsis en français et les identifiants TMDB/IMDb.
- 🚀 **Upload Direct C411** : Envoi automatisé vers l'API UNIT3D (`/api/torrents/upload`) ou assistance au formulaire web.
- 📥 **Injection qBittorrent avec Mappage de Chemin** :
  - Envoie le torrent généré à l'API de votre client qBittorrent.
  - Traduit les chemins locaux en chemins réels du NAS pour un contrôle d'intégrité à **100% instantané** (le fichier commence à seeder immédiatement sans retéléchargement).
- 👤 **Utilisateur TrueNAS 568 (apps)** : Le conteneur s'exécute nativement avec le compte `568:568` (`apps`), éliminant tout conflit de permissions sur les partages ZFS et ACLs de TrueNAS SCALE.
- 🪶 **Linux Allégé Alpine** : Image Docker ultra-légère basée sur `python:3.12-alpine` avec support multi-architecture (`linux/amd64` et `linux/arm64`).

---

## 🚀 Déploiement Rapide (Docker & Docker Compose)

Créez un fichier `docker-compose.yml` sur votre NAS :

```yaml
services:
  torrent-generator:
    image: hollow313/torrent-generator:latest
    container_name: torrent-generator
    restart: unless-stopped
    user: "568:568" # Utilisateur apps sur TrueNAS SCALE
    ports:
      - "30017:30017"
    environment:
      - PORT=30017
      - TZ=Europe/Paris
      - CONFIG_DIR=/config
      - DATA_DIR=/data
      - OUTPUT_DIR=/output
    volumes:
      # Configuration persistante (vos paramètres et historique)
      - ./config:/config
      # Vos dossiers de médias sur le NAS (ex: films, séries)
      - /mnt/Plex/Plex/films:/data:ro
      # Dossier où seront enregistrés les fichiers .torrent et .nfo générés
      - ./torrents:/output
```

Lancez le conteneur :
```bash
docker compose up -d
```

Accédez à l'interface web : `http://<IP_DU_NAS>:30017`

---

## ⚙️ Configuration via l'interface Web

Rendez-vous dans l'onglet **Paramètres** de l'interface web :

1. **Passkey C411** : Renseignez votre passkey personnelle (trouvable sur votre profil C411).
2. **Clé API C411** : Récupérez votre clé API sur [C411 Intégrations API](https://c411.org/user/integrations).
3. **qBittorrent** :
   - URL : `http://192.168.1.200:8079/` (ou l'adresse de votre conteneur qBittorrent)
   - Utilisateur & Mot de passe
   - **Mappage de chemins** :
     - Chemin dans ce container : `/data`
     - Chemin équivalent dans qBittorrent : `/mnt/Plex/Plex/films`
4. **TMDB (Optionnel)** : Renseignez votre clé API TMDB v3 pour l'import automatique des affiches et résumés.

---

## 🔒 Confidentialité & Sécurité

- Aucun identifiant, clé API, passkey ni mot de passe n'est enregistré dans l'image Docker ni dans le dépôt GitHub.
- Les données de configuration sont uniquement conservées localement dans votre volume `./config/config.json`.
