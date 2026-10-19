import os
from typing import Dict, Any, Optional
import httpx

class QBittorrentClient:
    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        mapping_from: str = "/data",
        mapping_to: str = "",
        category: str = "c411",
        tags: str = "c411,upload"
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.mapping_from = mapping_from
        self.mapping_to = mapping_to
        self.category = category
        self.tags = tags

    def translate_path(self, local_path: str) -> str:
        """
        Translates a local path inside the generator container into the path expected by the torrent client.
        For example: /data/films/Movie.mkv -> /chemin/serveur/films/Movie.mkv
        """
        normalized_local = local_path.replace("\\", "/")
        norm_from = self.mapping_from.replace("\\", "/").rstrip("/")
        norm_to = self.mapping_to.replace("\\", "/").rstrip("/")

        if norm_from and normalized_local.startswith(norm_from):
            rel = normalized_local[len(norm_from):].lstrip("/")
            target = f"{norm_to}/{rel}" if norm_to else rel
            return target
        return local_path

    async def _get_authenticated_client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(timeout=15.0, verify=False)
        try:
            # 1. Vérifier si l'accès est déjà autorisé sans authentification (cas du réseau local / bypass auth qBittorrent)
            test_resp = await client.get(f"{self.base_url}/api/v2/app/version")
            if test_resp.status_code == 200:
                # Accès direct sans authentification autorisé
                return client

            # Si l'IP est bannie par qBittorrent
            if "bannie" in test_resp.text.lower() or "banned" in test_resp.text.lower():
                await client.aclose()
                raise PermissionError(
                    "Votre adresse IP a été temporairement bannie par qBittorrent suite à des tentatives infructueuses. "
                    "Redémarrez simplement votre conteneur qBittorrent sur TrueNAS pour réinitialiser le blocage immédiatement."
                )

            # 2. Si une authentification est requise (HTTP 403 Forbidden ou redirection)
            # IMPORTANT: Si aucun identifiant n'est fourni, NE PAS poster d'identifiants vides !
            # Cela évite d'incrémenter le compteur d'échecs de qBittorrent et de provoquer un ban.
            if not self.username and not self.password:
                await client.aclose()
                raise PermissionError(
                    "qBittorrent exige une authentification pour ce conteneur (le conteneur a une IP interne Docker distincte de votre réseau local). "
                    "Veuillez renseigner votre nom d'utilisateur et mot de passe qBittorrent dans les paramètres, "
                    "ou ajouter le sous-réseau Docker (ex: 172.16.0.0/12) dans les sous-réseaux approuvés de qBittorrent."
                )

            login_url = f"{self.base_url}/api/v2/auth/login"
            data = {
                "username": self.username,
                "password": self.password
            }
            resp = await client.post(login_url, data=data)
            if resp.status_code == 200 and "Fails" not in resp.text:
                return client

            await client.aclose()
            if "bannie" in resp.text.lower() or "banned" in resp.text.lower():
                raise PermissionError(
                    "Votre adresse IP a été temporairement bannie par qBittorrent suite à trop de tentatives. "
                    "Redémarrez le conteneur qBittorrent sur votre serveur pour lever le blocage."
                )
            error_msg = resp.text.strip() if resp.text else f"Code HTTP {resp.status_code}"
            raise PermissionError(f"Identifiants qBittorrent refusés ({error_msg}).")
        except Exception as e:
            await client.aclose()
            raise e

    async def test_connection(self) -> Dict[str, Any]:
        """Tests connection and credentials against qBittorrent Web API."""
        try:
            client = await self._get_authenticated_client()
            version_resp = await client.get(f"{self.base_url}/api/v2/app/version")
            api_version_resp = await client.get(f"{self.base_url}/api/v2/app/webapiVersion")
            
            qb_version = version_resp.text if version_resp.status_code == 200 else "Unknown"
            api_version = api_version_resp.text if api_version_resp.status_code == 200 else "Unknown"
            await client.aclose()

            return {
                "success": True,
                "message": f"Connecté à qBittorrent v{qb_version} (API Web v{api_version})",
                "version": qb_version
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur de connexion à qBittorrent : {str(e)}"
            }

    async def add_torrent(
        self,
        torrent_file_path: str,
        source_data_path: str,
        paused: bool = False,
        info_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Injects the generated .torrent file into qBittorrent pointing to the translated media directory.
        Automatically triggers a hash recheck so existing files verify to 100% and start seeding immediately.
        """
        if not os.path.exists(torrent_file_path):
            return {"success": False, "message": f"Fichier .torrent introuvable : {torrent_file_path}"}

        # Calculate savepath: qBittorrent needs the parent directory of the file or folder
        translated_path = self.translate_path(source_data_path)
        
        # If it's a file, savepath is its parent folder
        if os.path.isfile(source_data_path):
            save_path = os.path.dirname(translated_path)
        else:
            # If it's a folder, savepath is the parent directory so qBittorrent finds the folder inside
            save_path = os.path.dirname(translated_path)

        try:
            client = await self._get_authenticated_client()
            add_url = f"{self.base_url}/api/v2/torrents/add"

            files = {}
            with open(torrent_file_path, "rb") as f:
                files["torrents"] = (os.path.basename(torrent_file_path), f.read(), "application/x-bittorrent")

            data = {
                "savepath": save_path,
                "category": self.category,
                "tags": self.tags,
                "paused": "true" if paused else "false",
                "skip_checking": "false",
                "autoTMM": "false"
            }

            resp = await client.post(add_url, data=data, files=files)

            if resp.status_code == 200 and "Fails" not in resp.text:
                # Trigger automatic recheck so qBittorrent verifies the file on disk to 100%
                if info_hash:
                    try:
                        import asyncio
                        await asyncio.sleep(0.5)
                        await client.post(f"{self.base_url}/api/v2/torrents/recheck", data={"hashes": info_hash})
                    except Exception as recheck_err:
                        print(f"[qBittorrent] Auto-recheck error: {recheck_err}")

                await client.aclose()
                return {
                    "success": True,
                    "message": f"Torrent ajouté à qBittorrent avec succès (dossier: {save_path}) ! Vérification du seed lancée.",
                    "save_path": save_path
                }
            else:
                await client.aclose()
                return {
                    "success": False,
                    "message": f"qBittorrent a renvoyé : {resp.text} (HTTP {resp.status_code})"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors de l'ajout à qBittorrent : {str(e)}"
            }
