import os
from typing import Dict, Any, List, Optional
import httpx

class TmdbClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key.strip()
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/w500"

    async def search(self, query: str, year: Optional[str] = None, media_type: str = "movie") -> List[Dict[str, Any]]:
        """
        Searches TMDB for a movie or TV show in French.
        """
        if not self.api_key:
            return []

        endpoint = f"{self.base_url}/search/{media_type}" if media_type in ["movie", "tv"] else f"{self.base_url}/search/multi"
        params = {
            "api_key": self.api_key,
            "query": query.strip(),
            "language": "fr-FR",
            "include_adult": "false"
        }
        if year and media_type == "movie":
            params["year"] = year
        elif year and media_type == "tv":
            params["first_air_date_year"] = year

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, params=params)
                if resp.status_code != 200:
                    return []
                results = resp.json().get("results", [])
                
                formatted = []
                for item in results[:10]:
                    m_type = item.get("media_type", media_type)
                    title = item.get("title") or item.get("name") or ""
                    orig_title = item.get("original_title") or item.get("original_name") or ""
                    release_date = item.get("release_date") or item.get("first_air_date") or ""
                    item_year = release_date.split("-")[0] if release_date else ""
                    poster_path = item.get("poster_path")
                    poster_url = f"{self.image_base_url}{poster_path}" if poster_path else ""

                    formatted.append({
                        "id": item.get("id"),
                        "media_type": m_type,
                        "title": title,
                        "original_title": orig_title,
                        "year": item_year,
                        "synopsis": item.get("overview", ""),
                        "poster_url": poster_url,
                        "vote_average": item.get("vote_average", 0)
                    })
                return formatted
        except Exception as e:
            print(f"[TMDB] Search error: {e}")
            return []

    async def get_details(self, tmdb_id: int, media_type: str = "movie") -> Optional[Dict[str, Any]]:
        """Fetches full details including external IDs (IMDB ID)."""
        if not self.api_key:
            return None

        endpoint = f"{self.base_url}/{media_type}/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "language": "fr-FR",
            "append_to_response": "external_ids"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                
                external_ids = data.get("external_ids", {})
                imdb_id = external_ids.get("imdb_id")
                poster_path = data.get("poster_path")
                poster_url = f"{self.image_base_url}{poster_path}" if poster_path else ""

                return {
                    "id": data.get("id"),
                    "imdb_id": imdb_id,
                    "title": data.get("title") or data.get("name") or "",
                    "original_title": data.get("original_title") or data.get("original_name") or "",
                    "synopsis": data.get("overview", ""),
                    "poster_url": poster_url,
                    "genres": [g["name"] for g in data.get("genres", [])]
                }
        except Exception as e:
            print(f"[TMDB] Get details error: {e}")
            return None
