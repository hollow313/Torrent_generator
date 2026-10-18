# ⚡ Torrent Generator (C411 & Multi-Trackers)

[![Docker Build & Push](https://github.com/hollow313/Torrent_generator/actions/workflows/docker-build.yml/badge.svg)](https://github.com/hollow313/Torrent_generator/actions/workflows/docker-build.yml)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20ARM64%20%7C%20AMD64-blue)
![Base Image](https://img.shields.io/badge/Base-Alpine%203.12-green)
![Port](https://img.shields.io/badge/Port-30017-orange)

Application web conteneurisée et automatisée conçue pour préparer, générer et uploader des releases torrents conformes aux règles strictes du tracker **C411** (et extensible à d'autres trackers), avec injection directe dans **qBittorrent** pour le seed immédiat depuis votre NAS.

---

## 🌟 Fonctionnalités Principales

- 🖥️ **Interface Web Moderne sur le port `30017`** : Thème sombre réactif, explorateur de fichiers, éditeurs en direct NFO et BBCode.
- 📁 **Explorateur de fichiers NAS** : Naviguez dans vos disques montés (ex: `/mnt/Plex/Plex/films/`), sélectionnez un fichier ou un dossier complet en un clic.
- 📐 **Conformité stricte aux Règles C411** :
  - **Nommage normalisé** : Séparateur par point (`.`), suppression des accents et caractères non autorisés.
  - **Règle Anti-DETAG** : Détection automatique et conservation obligatoire du tag de la team/auteur d'origine. Si aucun tag n'est présent, application du suffixe `-NOTAG` comme exigé par la Team Pending de C411.
  - **Taille des pièces (Pieces)** : Calcul dynamique et automatique selon le barème officiel C411 :
    - < 1 Go : **1 Mo**
    - < 2 Go : **2 Mo**
    - < 3 Go : **4 Mo**
    - < 8 Go : **8 Mo**
    - > 8 Go : **16 Mo**
  - **Tracker de secours inclus** : Annonce principale (`https://c411.org/announce/<passkey>`) et announce de secours (`https://tk.c411.tw/announce/<passkey>`).
  - **Flag Privé** : Verrouillé à `1`.
- 📝 **Générateur Automatique de NFO & BBCode** :
  - Analyse complète via **MediaInfo** (codecs vidéo, résolutions, profils HDR/DV, pistes audio multiples, canaux 5.1/7.1, sous-titres complets/forcés).
  - Présentation BBCode soignée avec balises de mise en forme C411.
- 🔍 **Vérificateur de doublons en direct** : Interroge en temps réel l'API Torznab de C411 pour vérifier si la release existe déjà sur le tracker avant de publier.
- 🎬 **Intégration TMDB** : Récupère automatiquement l'affiche officielle (poster), le synopsis en français et les identifiants TMDB/IMDb.
- 🚀 **Upload Direct C411** : Envoi automatisé vers l'API UNIT3D (`/api/torrents/upload`) ou assistance au formulaire web.
- 📥 **Injection qBittorrent avec Mappage de Chemin** :
  - Envoie le torrent généré à l'API de votre client qBittorrent.
  - Traduit les chemins locaux en chemins réels du NAS pour un contrôle d'intégrité à **100% instantané** (le fichier commence à seeder immédiatement sans retéléchargement).
- 🧩 **Architecture Extensible** : Module de trackers modulaire (`app/trackers/`) permettant d'ajouter facilement d'autres trackers BitTorrent à l'avenir.
- 🪶 **Linux Allégé Alpine** : Image Docker ultra-légère basée sur `python:3.12-alpine` avec support multi-architecture (`linux/amd64` et `linux/arm64` pour NAS Synology, QNAP, Raspberry Pi, etc.).

---

## 🚀 Déploiement Rapide (Docker & Docker Compose)

### 1. Via Docker Compose

Créez un fichier `docker-compose.yml` sur votre NAS :

```yaml
services:
  torrent-generator:
    image: hollow313/torrent-generator:latest
    container_name: torrent-generator
    restart: unless-stopped
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

Lancez le container :
```bash
docker compose up -d
```

Accédez à l'interface web : `http://<IP_DU_NAS>:30017`

---

## ⚙️ Configuration initiale via l'interface Web

Rendez-vous dans l'onglet **Paramètres** de l'interface web :

1. **Passkey C411** : Renseignez votre passkey personnelle (trouvable sur votre profil C411).
2. **Clé API C411** : Récupérez votre clé API sur [C411 Intégrations API](https://c411.org/user/integrations).
3. **qBittorrent** :
   - URL : `http://qbittorrent:8080` ou `http://192.168.1.X:8080`
   - Utilisateur & Mot de passe
   - **Mappage de chemins** :
     - Chemin dans ce container : `/data`
     - Chemin équivalent dans qBittorrent : `/mnt/Plex/Plex/films`
4. **TMDB (Optionnel)** : Renseignez votre clé API TMDB v3 pour l'import automatique des affiches et résumés.

Cliquez sur **Tester la connexion** pour valider vos paramètres.

---

## 🛠️ Workflow d'utilisation

1. **Explorateur** : Naviguez dans votre arborescence et cliquez sur **Analyser** en face d'un fichier média ou dossier.
2. **Vérification** :
   - Le système génère le nom officiel selon le barème C411.
   - Le tag de l'auteur original est détecté et verrouillé pour respecter les règles Anti-DETAG.
   - La taille des pièces est calculée selon le poids du fichier.
   - Cliquez sur **Vérifier doublons** pour confirmer l'absence de doublon sur C411.
   - Vous pouvez ajuster le synopsis, l'affiche ou éditer le NFO à la main.
3. **Création & Upload** :
   - Cliquez sur **1. Créer le Torrent & NFO** : le fichier `.torrent` est créé avec announce principale + backup et flag privé.
   - Cliquez sur **2. Uploader sur C411** : envoi automatique via l'API.
   - Cliquez sur **3. Envoyer à qBittorrent** : le torrent est ajouté en seed à 100% sur votre client.

---

## 🔒 Sécurité & Confidentialité

- Aucune clé API, passkey, mot de passe ou token n'est inscrit dans l'image Docker ni dans le code source GitHub.
- Vos identifiants sont sauvegardés localement dans le volume monté `/config/config.json`.
- Le pipeline CI/CD GitHub Actions utilise les secrets sécurisés GitHub pour la publication sur Docker Hub.

---

## 📜 Licence

MIT License - Projet développé pour la communauté BitTorrent.
