# ⚡ Torrent Generator (C411 & Multi-Trackers)

[![Docker Build & Push](https://github.com/hollow313/Torrent_generator/actions/workflows/docker-build.yml/badge.svg)](https://github.com/hollow313/Torrent_generator/actions/workflows/docker-build.yml)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20ARM64%20%7C%20AMD64-blue)
![Base Image](https://img.shields.io/badge/Base-Alpine%203.12-green)
![Port](https://img.shields.io/badge/Port-30017-orange)
![User](https://img.shields.io/badge/User-apps%20(568:568)-purple)

Application web conteneurisée et automatisée conçue pour préparer, générer et uploader des releases torrents conformes aux règles strictes du tracker **C411** (et extensible à d'autres trackers), avec injection directe dans votre client de téléchargement pour le seed immédiat depuis votre serveur.

---

## 🌟 Fonctionnalités Principales

- 🖥️ **Interface Web Moderne sur le port `30017`** : Thème sombre réactif, explorateur de fichiers, éditeurs en direct NFO et BBCode.
- 📁 **Explorateur de fichiers du serveur** : Naviguez dans vos disques montés (point de montage `/data` pouvant regrouper films, séries, mangas, livres, émissions, spectacles...), sélectionnez un fichier ou un dossier complet en un clic.
- 📐 **Conformité stricte aux Règles C411** :
  - **Nommage normalisé** : Séparateur par point (`.`), suppression des accents et caractères non autorisés.
  - **Règle Anti-DETAG & Gestion des renommages automatiques** : 
    - Si un outil de gestion a renommé vos fichiers en supprimant le tag d'origine, le système inspecte automatiquement les **métadonnées internes du MKV** (titre de piste, header), le dossier parent et les éventuels fichiers `.nfo` associés pour **restaurer le tag d'origine** !
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
    - 🔴 **Doublon strict détecté** : avertissement immédiat avec le nombre de seeders actuels pour éviter un refus par la modération.
    - 🟡 **Version différente autorisée** : confirme que la qualité (ex: 2160p UHD ou Remux) apporte une version distincte légitime selon les règles C411.
    - 🟢 **Feu vert** : aucun doublon existant.
- 🎬 **Intégration TMDB** : Récupère automatiquement l'affiche officielle (poster), le synopsis en français et les identifiants TMDB/IMDb.
- 🚀 **Upload Direct C411** : Envoi automatisé vers l'API UNIT3D (`/api/torrents/upload`) ou assistance au formulaire web.
- 📥 **Injection Client Torrent avec Mappage de Chemin** :
  - Envoie le torrent généré à l'API de votre client de téléchargement.
  - Traduit les chemins locaux en chemins réels du serveur pour un contrôle d'intégrité à **100% instantané** (le fichier commence à seeder immédiatement sans retéléchargement).
- 👤 **Utilisateur Serveur 568 (apps)** : Le conteneur s'exécute nativement avec le compte `568:568` (`apps`), éliminant tout conflit de permissions sur les partages et ACLs du serveur.
- 🪶 **Linux Allégé Alpine** : Image Docker ultra-légère basée sur `python:3.12-alpine` avec support multi-architecture (`linux/amd64` et `linux/arm64`).

---

## 🚀 Déploiement Rapide (Docker & Docker Compose)

Créez un fichier `docker-compose.yml` sur votre serveur :

```yaml
services:
  torrent-generator:
    image: hollow313/torrent-generator:latest
    container_name: torrent-generator
    restart: unless-stopped
    user: "568:568"
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
      # Dossier racine de vos médias sur le serveur
      - /chemin/vers/vos/medias:/data:ro
      # Dossier où seront enregistrés les fichiers .torrent et .nfo générés
      - ./torrents:/output
```

Lancez le conteneur :
```bash
docker compose up -d
```

Accédez à l'interface web : `http://<IP_DU_SERVEUR>:30017`

---

## ⚙️ Configuration

Vous pouvez configurer l'application de deux façons :
1. **Directement depuis l'interface web** dans l'onglet **Paramètres** (avec boutons de test de connexion en direct pour C411 et qBittorrent).
2. **Ou via le fichier `config.json`** en copiant `config.json.example` vers `./config/config.json` avant de démarrer le conteneur.

### 📋 Variables du fichier `config.json`

| Variable | Statut | Valeur par défaut | Description |
| :--- | :---: | :---: | :--- |
| `web_port` | **Optionnel** | `30017` | Port d'écoute du serveur web dans le conteneur. |
| `data_dir` | **Optionnel** | `"/data"` | Dossier racine où sont montés vos médias dans le conteneur. |
| `output_dir` | **Optionnel** | `"/output"` | Dossier où sont enregistrés les fichiers `.torrent` et `.nfo` générés. |
| `c411_passkey` | **OBLIGATOIRE** | `""` | Votre passkey personnelle de 32 caractères C411 (disponible sur votre profil C411). Indispensable pour générer les URL de trackers valides dans les fichiers `.torrent`. |
| `c411_api_key` | **OBLIGATOIRE** | `""` | Votre clé API C411 (sur [C411 Intégrations API](https://c411.org/user/integrations)). Nécessaire pour la vérification automatique des doublons (Torznab) et l'upload direct. |
| `c411_base_url` | **Optionnel** | `"https://c411.org"` | URL de base du site C411. |
| `c411_announce_primary` | **Optionnel** | `"https://c411.org/announce/"` | URL du tracker d'annonce principal. |
| `c411_announce_backup` | **Optionnel** | `"https://tk.c411.tw/announce/"` | URL du tracker d'annonce de secours (conforme aux spécifications C411). |
| `c411_default_tag` | **Optionnel** | `"NOTAG"` | Tag par défaut appliqué si aucun tag de team n'est détecté dans le média (obligatoire selon les règles anti-detag C411). |
| `c411_anonymous` | **Optionnel** | `false` | Publier les torrents en mode anonyme sur C411 (`true` ou `false`). |
| `qbittorrent_enabled` | **Optionnel** | `true` | Active (`true`) ou désactive (`false`) l'injection automatique dans le client de téléchargement. |
| `qbittorrent_url` | **OBLIGATOIRE\*** | `""` | Adresse WebUI de votre client qBittorrent (ex: `http://192.168.1.50:8080/`). (\*Obligatoire si `qbittorrent_enabled: true`). |
| `qbittorrent_username` | **Optionnel** | `"admin"` | Nom d'utilisateur pour se connecter à l'interface de qBittorrent. |
| `qbittorrent_password` | **Optionnel** | `""` | Mot de passe de votre client de téléchargement (laissé vide si aucune authentification requise). |
| `qbittorrent_category` | **Optionnel** | `"c411"` | Catégorie assignée automatiquement au torrent injecté dans qBittorrent. |
| `qbittorrent_tags` | **Optionnel** | `"c411,upload"` | Tags appliqués au torrent dans qBittorrent (séparés par des virgules). |
| `qbittorrent_path_mapping_from` | **Optionnel** | `"/data"` | Chemin des fichiers tel que vu dans le conteneur Torrent Generator. |
| `qbittorrent_path_mapping_to` | **OBLIGATOIRE\*** | `""` | Chemin réel complet des fichiers tel que vu par votre client qBittorrent sur le serveur (ex: `/chemin/reel/sur/serveur`). Indispensable pour que le client trouve le fichier et démarre le seed à 100% instantanément sans retéléchargement. |
| `qbittorrent_start_paused` | **Optionnel** | `false` | Si `true`, le torrent est injecté en pause. Si `false`, il commence directement le contrôle d'intégrité et le seed. |
| `tmdb_api_key` | **Optionnel** | `""` | Clé API v3 gratuite The Movie Database. Permet l'import automatique des affiches officielles (posters) et résumés en français pour la présentation BBCode. |
| `piece_size_mode` | **Optionnel** | `"auto"` | Mode de calcul de la taille des pièces du torrent (`"auto"` applique strictement l'échelle officielle C411 : 1Mo à 16Mo selon la taille totale). |

> [!NOTE]
> Tous ces paramètres peuvent être modifiés à tout moment directement depuis l'interface Web dans l'onglet **Paramètres** sans avoir à redémarrer le conteneur.

---

## 🔒 Confidentialité & Sécurité

- Aucun identifiant, clé API, passkey, adresse IP ni mot de passe n'est enregistré dans l'image Docker ni dans le dépôt GitHub.
- Les données de configuration sont uniquement conservées localement dans votre volume `./config/config.json`.
