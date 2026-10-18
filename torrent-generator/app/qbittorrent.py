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
        mapping_to: str = "/mnt/Plex/Plex/films",
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
        Translates a local path inside the generator container into the path expected by qBittorrent.
        For example: /data/Films/Movie.mkv -> /mnt/Plex/Plex/films/Movie.mkv
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
        login_url = f"{self.base_url}/api/v2/auth/login"
        data = {
            "username": self.username,
            "password": self.password
        }
        resp = await client.post(login_url, data=data)
        if resp.status_code != 200 or "Fails" in resp.text:
            await client.aclose()
            raise PermissionError(f"Échec d'authentification qBittorrent (HTTP {resp.status_code}): {resp.text}")
        return client

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
        paused: bool = False
    ) -> Dict[str, Any]:
        """
        Injects the generated .torrent file into qBittorrent pointing to the translated media directory.
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
                "skip_checking": "false",  # Forces checking at 100%
                "autoTMM": "false"
            }

            resp = await client.post(add_url, data=data, files=files)
            await client.aclose()

            if resp.status_code == 200 and "Fails" not in resp.text:
                return {
                    "success": True,
                    "message": f"Torrent ajouté à qBittorrent avec succès (dossier: {save_path}) !",
                    "save_path": save_path
                }
            else:
                return {
                    "success": False,
                    "message": f"qBittorrent a renvoyé : {resp.text} (HTTP {resp.status_code})"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors de l'ajout à qBittorrent : {str(e)}"
            }
