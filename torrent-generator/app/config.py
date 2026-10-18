import os
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel

CONFIG_DIR = os.getenv("CONFIG_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config"))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

class AppConfig(BaseModel):
    # Server
    web_port: int = 30017
    
    # Paths
    data_dir: str = os.getenv("DATA_DIR", "/data")
    output_dir: str = os.getenv("OUTPUT_DIR", "/output")
    
    # C411 Settings
    c411_passkey: str = ""
    c411_api_key: str = ""
    c411_base_url: str = "https://c411.org"
    c411_announce_primary: str = "https://c411.org/announce/"
    c411_announce_backup: str = "https://tk.c411.tw/announce/"
    c411_default_tag: str = "NOTAG"
    c411_anonymous: bool = False
    
    # qBittorrent Settings
    qbittorrent_enabled: bool = True
    qbittorrent_url: str = "http://localhost:8080"
    qbittorrent_username: str = "admin"
    qbittorrent_password: str = ""
    qbittorrent_category: str = "c411"
    qbittorrent_tags: str = "c411,upload"
    qbittorrent_path_mapping_from: str = "/data"
    qbittorrent_path_mapping_to: str = "/mnt/Plex/Plex/films"
    qbittorrent_start_paused: bool = False
    
    # TMDB Settings
    tmdb_api_key: str = ""
    
    # Generator Settings
    piece_size_mode: str = "auto"  # auto follows C411 rules

_current_config: Optional[AppConfig] = None

def get_config() -> AppConfig:
    global _current_config
    if _current_config is None:
        _current_config = load_config()
    return _current_config

def load_config() -> AppConfig:
    global _current_config
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _current_config = AppConfig(**data)
                return _current_config
        except Exception as e:
            print(f"[Config] Error loading config: {e}. Using defaults.")
    _current_config = AppConfig()
    save_config(_current_config)
    return _current_config

def save_config(new_config: AppConfig) -> bool:
    global _current_config
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(new_config.model_dump(), f, indent=4)
        _current_config = new_config
        return True
    except Exception as e:
        print(f"[Config] Error saving config: {e}")
        return False
