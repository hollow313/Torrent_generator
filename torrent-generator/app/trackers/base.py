from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseTracker(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tracker (e.g. C411)."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Verify API key or connectivity."""
        pass

    @abstractmethod
    async def search(self, query: str, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search existing torrents to prevent duplicates."""
        pass

    @abstractmethod
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
        """Upload torrent to the tracker."""
        pass
