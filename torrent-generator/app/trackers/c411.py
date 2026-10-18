import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import httpx
from app.trackers.base import BaseTracker

C411_CATEGORIES = [
    {
        "id": 2000,
        "name": "Films & Vidéos",
        "sub": [
            {"id": 2000, "name": "Films & Vidéos (Général)"},
            {"id": 2010, "name": "Films Collection"},
            {"id": 2030, "name": "Films Foreign"},
            {"id": 2050, "name": "Vidéo-clips"},
            {"id": 2060, "name": "Films Animation"},
            {"id": 2070, "name": "Films Documentaire"},
            {"id": 2080, "name": "Films Spectacle"},
            {"id": 2090, "name": "Films Concert"},
        ]
    },
    {
        "id": 5000,
        "name": "Séries TV",
        "sub": [
            {"id": 5000, "name": "Série TV (Général)"},
            {"id": 5070, "name": "Animation Série"},
            {"id": 5080, "name": "Emission TV"},
            {"id": 5060, "name": "Sport"},
        ]
    },
    {
        "id": 3000,
        "name": "Audio",
        "sub": [
            {"id": 3010, "name": "Musique"},
            {"id": 3030, "name": "Audiobooks"},
            {"id": 3050, "name": "Karaoké & Podcast Radio & Samples"},
        ]
    },
    {
        "id": 7000,
        "name": "Ebooks",
        "sub": [
            {"id": 7020, "name": "Livres"},
            {"id": 7010, "name": "Presse"},
            {"id": 7030, "name": "BDs & Comics & Manga"},
        ]
    },
    {
        "id": 4000,
        "name": "Applications",
        "sub": [
            {"id": 4000, "name": "Windows & Nulled"},
            {"id": 4030, "name": "Linux & MacOS"},
            {"id": 4040, "name": "Formation"},
            {"id": 4060, "name": "Android Mobile"},
            {"id": 4070, "name": "iOS Mobile"},
        ]
    },
    {
        "id": 1000,
        "name": "Jeux Vidéo & Émulation",
        "sub": [
            {"id": 1030, "name": "Nintendo"},
            {"id": 1040, "name": "Microsoft"},
            {"id": 1080, "name": "Sony"},
            {"id": 1090, "name": "Autre & ROM/ISO"},
            {"id": 4050, "name": "Jeux PC (Linux / MacOS / Divers)"},
        ]
    },
    {
        "id": 8010,
        "name": "Autre",
        "sub": [
            {"id": 8010, "name": "Imprimante 3D & Objets & Pack"},
        ]
    },
    {
        "id": 6000,
        "name": "Adulte (+18)",
        "sub": [
            {"id": 6010, "name": "3X Films"},
            {"id": 6070, "name": "Hentai"},
            {"id": 6050, "name": "3X Ebooks"},
            {"id": 6060, "name": "3X Images"},
            {"id": 6080, "name": "3X Jeux"},
        ]
    }
]

class C411Tracker(BaseTracker):
    def __init__(self, api_key: str, base_url: str = "https://c411.org", passkey: str = ""):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.passkey = passkey.strip()

    @property
    def name(self) -> str:
        return "C411"

    async def test_connection(self) -> Dict[str, Any]:
        """Tests the Torznab API connectivity using user's API key."""
        if not self.api_key:
            return {"success": False, "message": "Clé API non configurée"}

        url = f"{self.base_url}/api/torznab"
        params = {"apikey": self.api_key, "t": "search", "limit": 1}

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200 and "<rss" in resp.text:
                    return {"success": True, "message": "Connexion à l'API C411 réussie !"}
                elif resp.status_code == 401:
                    return {"success": False, "message": "Clé API invalide (401 Unauthorized)"}
                elif resp.status_code == 429:
                    return {"success": False, "message": "Rate limit atteint sur C411 (429 Too Many Requests)"}
                else:
                    return {"success": False, "message": f"Erreur de réponse C411 : HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Erreur de connexion : {str(e)}"}

    async def search(self, query: str, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Searches C411 via Torznab endpoint to check if a release or movie already exists.
        Returns a list of torrents currently present on C411.
        """
        if not self.api_key:
            return []

        url = f"{self.base_url}/api/torznab"
        params = {
            "apikey": self.api_key,
            "t": "search",
            "q": query.strip(),
            "limit": 50
        }
        if category_id:
            params["cat"] = str(category_id)

        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    print(f"[C411 search] HTTP error {resp.status_code}")
                    return []

                # Parse Torznab RSS XML
                root = ET.fromstring(resp.text)
                items = []
                channel = root.find("channel")
                if channel is None:
                    return []

                for item in channel.findall("item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    size_bytes = int(item.findtext("size", "0") or 0)
                    pub_date = item.findtext("pubDate", "")
                    
                    seeders = 0
                    peers = 0
                    infohash = ""
                    for attr in item.findall("{http://torznab.com/schemas/2015/feed}attr"):
                        name = attr.get("name")
                        val = attr.get("value")
                        if name == "seeders":
                            seeders = int(val or 0)
                        elif name == "peers":
                            peers = int(val or 0)
                        elif name == "infohash":
                            infohash = val

                    # Format human readable size
                    size_mb = size_bytes / (1024 * 1024)
                    size_str = f"{size_mb / 1024:.2f} Go" if size_mb >= 1024 else f"{size_mb:.2f} Mo"

                    items.append({
                        "title": title,
                        "link": link,
                        "size": size_str,
                        "size_bytes": size_bytes,
                        "seeders": seeders,
                        "leechers": max(0, peers - seeders),
                        "infohash": infohash,
                        "date": pub_date
                    })

                return items
        except Exception as e:
            print(f"[C411 search] Exception during search: {e}")
            return []

    async def check_duplicates(
        self,
        title: str,
        resolution: str = "",
        source: str = "",
        tag: str = "",
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deep duplicate analysis on C411.
        Compares core title, resolution, source, and team tag to determine upload eligibility.
        """
        import re
        clean = title.replace(".", " ")
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean)
        year = year_match.group(1) if year_match else ""
        if year:
            core_words = clean.split(year)[0].strip() + f" {year}"
        else:
            core_words = clean.split()[0] if clean.split() else clean

        results = await self.search(core_words, category_id=category_id)
        if not results:
            return {
                "can_upload": True,
                "level": "success",
                "badge": "AUCUN DOUBLON",
                "status_text": "Aucun doublon trouvé sur C411. Vous pouvez uploader en toute confiance !",
                "exact_duplicates": [],
                "other_versions": [],
                "total_found": 0
            }

        exact_dupes = []
        other_versions = []

        res_lower = resolution.lower() if resolution else ""
        src_lower = source.lower() if source else ""
        tag_lower = tag.lower().lstrip("-") if tag else ""

        for item in results:
            item_title_lower = item["title"].lower()
            tag_match = tag_lower and tag_lower != "notag" and f"-{tag_lower}" in item_title_lower
            res_match = bool(res_lower and res_lower in item_title_lower)
            src_match = bool(src_lower and src_lower in item_title_lower)

            if (res_match and src_match) or tag_match:
                exact_dupes.append(item)
            else:
                other_versions.append(item)

        if exact_dupes:
            return {
                "can_upload": False,
                "level": "danger",
                "badge": "DOUBLON STRICT DÉTECTÉ",
                "status_text": f"⚠️ {len(exact_dupes)} release(s) avec la même qualité/source ou même team existent déjà sur C411. Risque élevé de refus par la Team Pending.",
                "exact_duplicates": exact_dupes,
                "other_versions": other_versions,
                "total_found": len(results)
            }
        else:
            return {
                "can_upload": True,
                "level": "warning",
                "badge": "VERSION DISTINCTE AUTORISÉE",
                "status_text": f"ℹ️ {len(other_versions)} version(s) trouvée(s) sur C411 mais dans une qualité ou source différente. Votre upload apporte une version distincte et est autorisé !",
                "exact_duplicates": [],
                "other_versions": other_versions,
                "total_found": len(results)
            }

    async def upload(
        self,
        torrent_path: str,
        nfo_path: str,
        name: str,
        category_id: int,
        description: str,
        mediainfo_text: str,
        tmdb_id: Optional[int] = None,
        imdb_id: Optional[str] = None,
        anonymous: bool = False
    ) -> Dict[str, Any]:
        """
        Uploads torrent via UNIT3D REST API (`POST /api/torrents/upload`).
        """
        if not self.api_key:
            return {"success": False, "message": "Clé API C411 manquante dans la configuration."}

        if not os.path.exists(torrent_path):
            return {"success": False, "message": f"Fichier .torrent introuvable : {torrent_path}"}

        upload_url = f"{self.base_url}/api/torrents/upload"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

        # Form data payload per UNIT3D specification
        data = {
            "name": name,
            "category_id": str(category_id),
            "description": description,
            "mediainfo": mediainfo_text,
            "anonymous": "1" if anonymous else "0"
        }

        if tmdb_id:
            data["tmdb"] = str(tmdb_id)
        if imdb_id:
            data["imdb"] = str(imdb_id)

        try:
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                files = {}
                with open(torrent_path, "rb") as tf:
                    files["torrent"] = (os.path.basename(torrent_path), tf.read(), "application/x-bittorrent")
                
                if os.path.exists(nfo_path):
                    with open(nfo_path, "rb") as nf:
                        files["nfo"] = (os.path.basename(nfo_path), nf.read(), "text/plain")

                resp = await client.post(upload_url, headers=headers, data=data, files=files)

                if resp.status_code in [200, 201]:
                    res_json = resp.json()
                    return {
                        "success": True,
                        "message": "Torrent uploadé avec succès sur C411 !",
                        "data": res_json
                    }
                else:
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "message": f"Erreur C411 (HTTP {resp.status_code}) : {resp.text}",
                        "web_upload_url": f"{self.base_url}/upload"
                    }

        except Exception as e:
            return {
                "success": False,
                "message": f"Erreur lors de l'upload vers C411 : {str(e)}",
                "web_upload_url": f"{self.base_url}/upload"
            }
