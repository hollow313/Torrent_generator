import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import httpx

def format_french_date(d_str: str) -> str:
    """Formats 'YYYY-MM-DD' into French long date (e.g. 'lundi 29 novembre 2021')."""
    if not d_str:
        return ""
    try:
        dt = datetime.strptime(d_str[:10], "%Y-%m-%d")
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        return f"{days[dt.weekday()]} {dt.day} {months[dt.month - 1]} {dt.year}"
    except Exception:
        return d_str

def format_duration(minutes: Any) -> str:
    """Formats runtime minutes into 'XhXXmin' or 'XXmin'."""
    if not minutes:
        return ""
    try:
        m = int(minutes)
        h = m // 60
        mins = m % 60
        if h > 0:
            return f"{h}h{mins:02d}min" if mins > 0 else f"{h}h"
        return f"{mins}min"
    except Exception:
        return str(minutes)

class TmdbClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key.strip()
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/w500"

    def _get_auth(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Supports both TMDB v3 API Key (32 hex chars) and v4 API Read Access Token (JWT starting with eyJ).
        """
        headers = {"Accept": "application/json"}
        params = {}
        if not self.api_key:
            return headers, params

        # If it's a JWT Bearer token (starts with eyJ or length > 40)
        if self.api_key.startswith("eyJ") or len(self.api_key) > 40:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            params["api_key"] = self.api_key

        return headers, params

    async def search(self, query: str, year: Optional[str] = None, media_type: str = "movie") -> List[Dict[str, Any]]:
        """
        Searches TMDB for a movie or TV show in French.
        """
        if not self.api_key:
            return []

        endpoint = f"{self.base_url}/search/{media_type}" if media_type in ["movie", "tv"] else f"{self.base_url}/search/multi"
        headers, params = self._get_auth()
        params.update({
            "query": query.strip(),
            "language": "fr-FR",
            "include_adult": "false"
        })
        if year and media_type == "movie":
            params["year"] = year
        elif year and media_type == "tv":
            params["first_air_date_year"] = year

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=headers, params=params)
                if resp.status_code != 200:
                    print(f"[TMDB] Search error status {resp.status_code}: {resp.text}")
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
            print(f"[TMDB] Search exception: {e}")
            return []

    async def get_details(self, tmdb_id: int, media_type: str = "movie") -> Optional[Dict[str, Any]]:
        """Fetches full details including external IDs (IMDb ID) and credits (director, cast)."""
        if not self.api_key:
            return None

        endpoint = f"{self.base_url}/{media_type}/{tmdb_id}"
        headers, params = self._get_auth()
        params.update({
            "language": "fr-FR",
            "append_to_response": "external_ids,credits"
        })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(endpoint, headers=headers, params=params)
                if resp.status_code != 200:
                    print(f"[TMDB] get_details error {resp.status_code}: {resp.text}")
                    return None
                data = resp.json()
                
                external_ids = data.get("external_ids", {})
                imdb_id = external_ids.get("imdb_id")
                poster_path = data.get("poster_path")
                poster_url = f"{self.image_base_url}{poster_path}" if poster_path else ""

                release_date_raw = data.get("release_date") or data.get("first_air_date") or ""
                item_year = release_date_raw.split("-")[0] if release_date_raw else ""
                release_date_formatted = format_french_date(release_date_raw)

                # Duration / Runtime
                runtime = data.get("runtime")
                if not runtime:
                    ep_runtimes = data.get("episode_run_time") or []
                    if ep_runtimes:
                        runtime = ep_runtimes[0]
                    else:
                        runtime = (data.get("last_episode_to_air") or {}).get("runtime")
                duration_str = format_duration(runtime) if runtime else ""

                # Production country
                countries = [c.get("name") for c in data.get("production_countries", []) if c.get("name")]
                if not countries and data.get("origin_country"):
                    countries = data.get("origin_country")
                country_str = ", ".join(countries) if countries else "France"

                # Genres
                genres_list = [g.get("name") for g in data.get("genres", []) if g.get("name")]
                genres_str = ", ".join(genres_list) if genres_list else "Non renseigné"

                # Credits (Directors & Cast)
                credits_data = data.get("credits", {})
                crew = credits_data.get("crew", [])
                directors = [m.get("name") for m in crew if m.get("job") in ["Director", "Réalisateur"]]
                if not directors:
                    directors = [c.get("name") for c in data.get("created_by", []) if c.get("name")]
                directors_str = ", ".join(directors) if directors else "Non renseigné"

                cast_list = [c.get("name") for c in credits_data.get("cast", [])[:6] if c.get("name")]
                cast_str = ", ".join(cast_list) if cast_list else "Non renseigné"

                vote_avg = round(float(data.get("vote_average", 0) or 0), 1)

                imdb_url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else ""

                return {
                    "id": data.get("id"),
                    "imdb_id": imdb_id,
                    "imdb_url": imdb_url,
                    "media_type": media_type,
                    "title": data.get("title") or data.get("name") or "",
                    "original_title": data.get("original_title") or data.get("original_name") or "",
                    "year": item_year,
                    "synopsis": data.get("overview", ""),
                    "poster_url": poster_url,
                    "genres": genres_list,
                    "genres_str": genres_str,
                    "country": country_str,
                    "release_date": release_date_raw,
                    "release_date_formatted": release_date_formatted,
                    "duration": duration_str,
                    "directors": directors_str,
                    "cast": cast_str,
                    "vote_average": vote_avg
                }
        except Exception as e:
            print(f"[TMDB] Get details error: {e}")
            return None

    async def find_by_imdb(self, imdb_id: str) -> Optional[Dict[str, Any]]:
        """Looks up a title on TMDB using an IMDb ID (e.g. tt1234567)."""
        if not self.api_key or not imdb_id:
            return None
        clean_imdb = imdb_id.strip()
        url = f"{self.base_url}/find/{clean_imdb}"
        headers, params = self._get_auth()
        params.update({
            "external_source": "imdb_id",
            "language": "fr-FR"
        })
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                movie_res = data.get("movie_results", [])
                tv_res = data.get("tv_results", [])
                if movie_res:
                    return await self.get_details(movie_res[0]["id"], "movie")
                elif tv_res:
                    return await self.get_details(tv_res[0]["id"], "tv")
                return None
        except Exception as e:
            print(f"[TMDB] find_by_imdb error: {e}")
            return None

    async def lookup_by_url_or_id(self, input_str: str) -> Optional[Dict[str, Any]]:
        """
        Parses a TMDB URL, IMDb URL, or direct ID (tmdb or imdb) and returns full movie/tv details.
        """
        s = input_str.strip()
        if not s:
            return None

        # 1. Match TMDB URL (e.g. https://www.themoviedb.org/movie/38700-bad-boys-for-life or /tv/1399)
        tmdb_url_match = re.search(r"themoviedb\.org/(movie|tv)/(\d+)", s, re.IGNORECASE)
        if tmdb_url_match:
            m_type = tmdb_url_match.group(1).lower()
            t_id = int(tmdb_url_match.group(2))
            details = await self.get_details(t_id, m_type)
            if not details:
                # Try the other type if not found
                alt_type = "tv" if m_type == "movie" else "movie"
                details = await self.get_details(t_id, alt_type)
            return details

        # 2. Match IMDb URL or ID (e.g. https://www.imdb.com/title/tt0137523/ or tt0137523)
        imdb_match = re.search(r"(tt\d{7,8})", s, re.IGNORECASE)
        if imdb_match:
            return await self.find_by_imdb(imdb_match.group(1))

        # 3. Match pure integer ID (treat as TMDB ID)
        if s.isdigit():
            t_id = int(s)
            details = await self.get_details(t_id, "movie")
            if not details:
                details = await self.get_details(t_id, "tv")
            return details

        return None

