import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from app.config import get_config, save_config, AppConfig, CONFIG_DIR
from app.torrent import TorrentBuilder, calculate_c411_piece_size
from app.media import MediaAnalyzer
from app.namer import ReleaseNamer
from app.nfo import NfoGenerator
from app.bbcode import BBCodeGenerator
from app.trackers.c411 import C411Tracker, C411_CATEGORIES
from app.qbittorrent import QBittorrentClient
from app.tmdb import TmdbClient

app = FastAPI(title="Torrent Generator C411", version="1.0.0")

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def load_history() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history_item(item: Dict[str, Any]):
    history = load_history()
    # Prepend new item
    history.insert(0, item)
    # Keep last 100 items
    history = history[:100]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[History] Error saving: {e}")

# Models
class ConfigUpdateModel(BaseModel):
    web_port: int
    data_dir: str
    output_dir: str
    c411_passkey: str
    c411_api_key: str
    c411_base_url: str
    c411_announce_primary: str
    c411_announce_backup: str
    c411_default_tag: str
    c411_anonymous: bool
    qbittorrent_enabled: bool
    qbittorrent_url: str
    qbittorrent_username: str
    qbittorrent_password: Optional[str] = ""
    qbittorrent_category: str
    qbittorrent_tags: str
    qbittorrent_path_mapping_from: str
    qbittorrent_path_mapping_to: str
    qbittorrent_start_paused: bool
    tmdb_api_key: Optional[str] = ""
    piece_size_mode: Optional[str] = "auto"

class AnalyzeRequest(BaseModel):
    path: str
    release_mode: Optional[str] = "single"  # single, episode, season_pack, integrale, manga_pack

class CheckDuplicatesRequest(BaseModel):
    title: str
    resolution: Optional[str] = ""
    source: Optional[str] = ""
    tag: Optional[str] = ""
    category_id: Optional[str] = None

class GenerateRequest(BaseModel):
    source_path: str
    release_name: str
    category_id: int
    piece_size: Optional[int] = None
    nfo_content: str
    bbcode_content: str
    source_type: str = "WEB"
    vod_platform: Optional[str] = ""
    tag: str = "NOTAG"
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    poster_url: Optional[str] = None
    rename_on_disk: Optional[bool] = False
    release_mode: Optional[str] = "single"

class SearchC411Request(BaseModel):
    query: str
    category_id: Optional[str] = None

class UploadC411Request(BaseModel):
    torrent_path: str
    nfo_path: str
    name: str
    category_id: int
    description: str
    mediainfo_text: str
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    anonymous: bool = False

class AddQBittorrentRequest(BaseModel):
    torrent_path: str
    source_path: str
    paused: Optional[bool] = None

class TmdbSearchRequest(BaseModel):
    query: str
    year: Optional[str] = None
    media_type: str = "movie"

class MassScanRequest(BaseModel):
    folder_path: str
    scan_mode: Optional[str] = "auto"  # auto, films, series_season, series_episode, mangas
    limit: Optional[int] = 30

def render_template(template_name: str, request: Request, context: Optional[Dict[str, Any]] = None):
    ctx = dict(context or {})
    ctx["request"] = request
    try:
        # Starlette >= 0.36 (request as keyword / first arg)
        return templates.TemplateResponse(request=request, name=template_name, context=ctx)
    except TypeError:
        # Starlette < 0.36 (name as first arg)
        return templates.TemplateResponse(name=template_name, context=ctx)

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    config = get_config()
    return render_template("index.html", request, {
        "config": config,
        "categories": C411_CATEGORIES
    })

@app.get("/api/config")
async def get_app_config():
    cfg = get_config()
    data = cfg.model_dump()
    # Mask password for security
    if data.get("qbittorrent_password"):
        data["qbittorrent_password"] = "******"
    return data

@app.post("/api/config")
async def update_app_config(update_data: ConfigUpdateModel):
    cfg = get_config()
    data_dict = update_data.model_dump()
    
    # Keep existing password if masked
    if data_dict.get("qbittorrent_password") == "******":
        data_dict["qbittorrent_password"] = cfg.qbittorrent_password

    new_cfg = AppConfig(**data_dict)
    if save_config(new_cfg):
        return {"success": True, "message": "Configuration sauvegardée avec succès !"}
    else:
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde de la configuration.")

@app.get("/api/browse")
async def browse_directory(path: Optional[str] = None):
    cfg = get_config()
    base_dir = os.path.abspath(cfg.data_dir)
    
    current_path = os.path.abspath(path) if path else base_dir
    
    # Prevent traversal outside allowed data_dir if desired, or allow browsing
    if not os.path.exists(current_path):
        current_path = base_dir

    if not os.path.exists(current_path):
        os.makedirs(current_path, exist_ok=True)

    items = []
    try:
        with os.scandir(current_path) as entries:
            for entry in entries:
                try:
                    stat = entry.stat()
                    is_dir = entry.is_dir()
                    sz = stat.st_size if not is_dir else 0
                    
                    # Human size
                    sz_mb = sz / (1024 * 1024)
                    size_str = f"{sz_mb / 1024:.2f} Go" if sz_mb >= 1024 else f"{sz_mb:.2f} Mo"
                    
                    items.append({
                        "name": entry.name,
                        "path": entry.path.replace("\\", "/"),
                        "is_dir": is_dir,
                        "size": size_str if not is_dir else "--",
                        "size_bytes": sz,
                        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
                    })
                except Exception:
                    continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'accès au dossier: {str(e)}")

    # Sort: folders first, then files
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    # Calculate parent path
    parent_path = os.path.dirname(current_path).replace("\\", "/") if current_path != base_dir else None

    return {
        "current_path": current_path.replace("\\", "/"),
        "parent_path": parent_path,
        "items": items
    }

@app.post("/api/analyze")
async def analyze_file(req: AnalyzeRequest):
    if not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail="Fichier ou dossier introuvable.")

    # 1. MediaInfo analysis
    media_info = MediaAnalyzer.analyze(req.path)
    lower_path = req.path.lower()
    is_dir = os.path.isdir(req.path)

    # Detect video vs book
    is_video = any(lower_path.endswith(ext) for ext in [".mkv", ".mp4", ".avi", ".ts", ".m2ts"]) or bool(media_info.get("video_codec"))
    is_book = any(lower_path.endswith(ext) for ext in [".cbz", ".cbr", ".pdf", ".epub"]) or (media_info.get("container") in ["EPUB", "PDF", "CBZ", "CBR"])

    # Determine recommended category & release mode
    suggested_category_id = 2000  # Default: Films
    suggested_mode = "single"

    if "/mangas/" in lower_path or "manga" in lower_path:
        if is_book:
            suggested_category_id = 7030  # BDs & Comics & Manga (Ebook / Scans)
            suggested_mode = "manga_pack" if is_dir else "manga_tome"
        else:
            suggested_category_id = 5070  # Animation Série (Anime)
            suggested_mode = "season_pack" if is_dir else "episode"
    elif "/series/" in lower_path or any(k in lower_path for k in ["s01", "s02", "s03", "saison", "season", "serie", "tv"]):
        suggested_category_id = 5000  # Séries TV
        suggested_mode = "season_pack" if is_dir else "episode"
    elif "/books/" in lower_path or is_book:
        suggested_category_id = 7020  # Livres
        suggested_mode = "single"
    elif "/emissions/" in lower_path:
        suggested_category_id = 5080  # Emission TV
        suggested_mode = "single"
    elif "/spectacles/" in lower_path:
        suggested_category_id = 2080  # Films Spectacle
        suggested_mode = "single"
    elif any(lower_path.endswith(ext) for ext in [".flac", ".mp3", ".wav", ".aac"]):
        suggested_category_id = 3010  # Musique
        suggested_mode = "single"
    elif any(lower_path.endswith(ext) for ext in [".exe", ".iso", ".dmg"]):
        suggested_category_id = 4000  # Applications
        suggested_mode = "single"
    else:
        suggested_category_id = 2000
        suggested_mode = "single"

    effective_mode = req.release_mode if (req.release_mode and req.release_mode != "auto") else suggested_mode

    # 2. Release name formatting according to C411 standards
    raw_name = os.path.basename(req.path)
    if os.path.isdir(req.path) and effective_mode == "single" and media_info.get("main_file_name"):
        raw_name = media_info["main_file_name"]
    cat_name = "E-Books" if suggested_category_id == 1000 else "Films & Vidéos"
    namer_res = ReleaseNamer.format_c411_title(raw_name, media_info, category=cat_name, release_mode=effective_mode)

    # 3. Piece size calculation
    total_bytes = media_info.get("file_size", 0)
    suggested_piece_size = calculate_c411_piece_size(total_bytes)

    # 4. Generate default NFO & BBCode
    release_title = namer_res["title"]
    default_nfo = NfoGenerator.generate(
        release_title=release_title,
        media_info=media_info,
        source=namer_res["source"],
        tag=namer_res["final_tag"]
    )
    
    default_bbcode = BBCodeGenerator.generate(
        release_title=release_title,
        media_info=media_info,
        source=namer_res["source"],
        tag=namer_res["final_tag"],
        nfo_text=default_nfo
    )

    return {
        "media_info": media_info,
        "namer": namer_res,
        "suggested_piece_size": suggested_piece_size,
        "suggested_category_id": suggested_category_id,
        "suggested_release_mode": suggested_mode,
        "nfo": default_nfo,
        "bbcode": default_bbcode
    }

@app.post("/api/generate-torrent")
async def generate_torrent(req: GenerateRequest):
    cfg = get_config()
    
    if not os.path.exists(req.source_path):
        raise HTTPException(status_code=404, detail="Chemin source introuvable.")

    if not cfg.c411_passkey:
        raise HTTPException(status_code=400, detail="Votre Passkey C411 n'est pas encore renseignée dans les Paramètres.")

    # Prepare announce URLs
    primary_announce = f"{cfg.c411_announce_primary.rstrip('/')}/{cfg.c411_passkey}"
    backup_announce = f"{cfg.c411_announce_backup.rstrip('/')}/{cfg.c411_passkey}" if cfg.c411_announce_backup else None

    # Destination filenames
    out_dir = os.path.abspath(cfg.output_dir)
    os.makedirs(out_dir, exist_ok=True)
    
    torrent_filename = f"{req.release_name}.torrent"
    nfo_filename = f"{req.release_name}.nfo"
    
    torrent_path = os.path.join(out_dir, torrent_filename)
    nfo_path = os.path.join(out_dir, nfo_filename)

    # 1. Save NFO file
    with open(nfo_path, "w", encoding="utf-8", errors="replace") as nf:
        nf.write(req.nfo_content)

    # 2. Determine effective source path
    actual_source_path = req.source_path
    if os.path.isdir(req.source_path) and req.release_mode == "single":
        # Target the main video file directly so Plex artworks (backdrop.jpg, folder.jpg) are excluded
        m_info = MediaAnalyzer.get_media_info(req.source_path)
        if m_info.get("main_file_path") and os.path.exists(m_info["main_file_path"]):
            actual_source_path = m_info["main_file_path"]

    # Optional physical rename on disk if user explicitly checked the option
    if req.rename_on_disk and os.path.exists(actual_source_path):
        dir_name = os.path.dirname(actual_source_path)
        if os.path.isfile(actual_source_path):
            ext = os.path.splitext(actual_source_path)[1]
            new_path = os.path.join(dir_name, f"{req.release_name}{ext}")
        else:
            new_path = os.path.join(dir_name, req.release_name)
        if actual_source_path != new_path:
            os.rename(actual_source_path, new_path)
            actual_source_path = new_path

    # 3. Build .torrent file
    builder = TorrentBuilder(
        source_path=actual_source_path,
        release_name=req.release_name,
        primary_announce=primary_announce,
        backup_announce=backup_announce,
        piece_size=req.piece_size,
        is_private=True,
        source_tag="C411"
    )

    out_file, info_hash = builder.build(torrent_path)

    # Save to history
    history_entry = {
        "id": info_hash,
        "name": req.release_name,
        "category_id": req.category_id,
        "source_path": actual_source_path,
        "torrent_path": torrent_path.replace("\\", "/"),
        "nfo_path": nfo_path.replace("\\", "/"),
        "size_bytes": builder.total_size,
        "piece_size": builder.piece_size,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status_c411": "Prêt",
        "status_qbittorrent": "Non injecté"
    }
    save_history_item(history_entry)

    return {
        "success": True,
        "message": "Fichier .torrent et .nfo générés avec succès !",
        "torrent_path": torrent_path.replace("\\", "/"),
        "nfo_path": nfo_path.replace("\\", "/"),
        "effective_source_path": actual_source_path.replace("\\", "/"),
        "torrent_filename": torrent_filename,
        "nfo_filename": nfo_filename,
        "info_hash": info_hash,
        "piece_size": builder.piece_size
    }

@app.post("/api/search-c411")
async def search_c411(req: SearchC411Request):
    cfg = get_config()
    tracker = C411Tracker(api_key=cfg.c411_api_key, base_url=cfg.c411_base_url, passkey=cfg.c411_passkey)
    results = await tracker.search(query=req.query, category_id=req.category_id)
    return {
        "query": req.query,
        "count": len(results),
        "results": results
    }

@app.post("/api/check-duplicates")
async def check_duplicates(req: CheckDuplicatesRequest):
    cfg = get_config()
    tracker = C411Tracker(api_key=cfg.c411_api_key, base_url=cfg.c411_base_url, passkey=cfg.c411_passkey)
    res = await tracker.check_duplicates(
        title=req.title,
        resolution=req.resolution or "",
        source=req.source or "",
        tag=req.tag or "",
        category_id=req.category_id
    )
    return res

@app.post("/api/upload-c411")
async def upload_c411(req: UploadC411Request):
    cfg = get_config()
    tracker = C411Tracker(api_key=cfg.c411_api_key, base_url=cfg.c411_base_url, passkey=cfg.c411_passkey)
    
    result = await tracker.upload(
        torrent_path=req.torrent_path,
        nfo_path=req.nfo_path,
        name=req.name,
        category_id=req.category_id,
        description=req.description,
        mediainfo_text=req.mediainfo_text,
        tmdb_id=req.tmdb_id,
        imdb_id=req.imdb_id,
        anonymous=req.anonymous
    )
    return result

@app.post("/api/add-qbittorrent")
async def add_qbittorrent(req: AddQBittorrentRequest):
    cfg = get_config()
    if not cfg.qbittorrent_enabled:
        raise HTTPException(status_code=400, detail="qBittorrent n'est pas activé dans les paramètres.")

    client = QBittorrentClient(
        base_url=cfg.qbittorrent_url,
        username=cfg.qbittorrent_username,
        password=cfg.qbittorrent_password,
        mapping_from=cfg.qbittorrent_path_mapping_from,
        mapping_to=cfg.qbittorrent_path_mapping_to,
        category=cfg.qbittorrent_category,
        tags=cfg.qbittorrent_tags
    )

    paused = req.paused if req.paused is not None else cfg.qbittorrent_start_paused
    res = await client.add_torrent(
        torrent_file_path=req.torrent_path,
        source_data_path=req.source_path,
        paused=paused
    )
    return res

@app.post("/api/test-qbittorrent")
async def test_qbittorrent():
    cfg = get_config()
    client = QBittorrentClient(
        base_url=cfg.qbittorrent_url,
        username=cfg.qbittorrent_username,
        password=cfg.qbittorrent_password
    )
    return await client.test_connection()

@app.post("/api/test-c411")
async def test_c411():
    cfg = get_config()
    tracker = C411Tracker(api_key=cfg.c411_api_key, base_url=cfg.c411_base_url, passkey=cfg.c411_passkey)
    return await tracker.test_connection()

@app.post("/api/tmdb-search")
async def search_tmdb(req: TmdbSearchRequest):
    cfg = get_config()
    client = TmdbClient(api_key=cfg.tmdb_api_key)
    
    # 1. Try direct URL or ID lookup first (e.g. TMDB link, IMDb link or ID)
    direct_match = await client.lookup_by_url_or_id(req.query)
    if direct_match:
        return {"results": [direct_match], "direct_match": True}

    # 2. Regular text search
    results = await client.search(query=req.query, year=req.year, media_type=req.media_type)
    return {"results": results, "direct_match": False}

@app.post("/api/mass-scan")
async def mass_scan(req: MassScanRequest):
    if not os.path.exists(req.folder_path):
        raise HTTPException(status_code=404, detail="Dossier introuvable sur le serveur.")

    cfg = get_config()
    tracker = C411Tracker(api_key=cfg.c411_api_key, base_url=cfg.c411_base_url, passkey=cfg.c411_passkey)

    candidates = []
    video_exts = {".mkv", ".mp4", ".avi", ".ts", ".m2ts"}
    book_exts = {".cbz", ".cbr", ".epub", ".pdf"}

    mode = req.scan_mode or "auto"
    folder_lower = req.folder_path.lower()
    if mode == "auto":
        if "film" in folder_lower:
            mode = "films"
        elif "manga" in folder_lower:
            mode = "mangas"
        elif "serie" in folder_lower:
            mode = "series_seasons"
        else:
            mode = "films"

    try:
        entries = sorted(os.scandir(req.folder_path), key=lambda e: e.name.lower())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'accès au dossier : {e}")

    limit = req.limit or 150
    for entry in entries:
        if len(candidates) >= limit:
            break

        item_path = entry.path.replace("\\", "/")
        item_name = entry.name

        if item_name.startswith("."):
            continue

        if entry.is_file():
            ext = os.path.splitext(item_name)[1].lower()
            if ext in video_exts or ext in book_exts:
                is_manga_book = ext in book_exts
                file_mode = "episode" if mode in ["series_episodes", "series_episode"] else ("manga_tome" if is_manga_book else "single")
                candidates.append({
                    "path": item_path,
                    "name": item_name,
                    "search_name": item_name,
                    "is_dir": False,
                    "size_bytes": entry.stat().st_size,
                    "mode": file_mode
                })
        elif entry.is_dir():
            sz = 0
            has_media = False
            video_count = 0
            largest_file_name = None
            largest_file_size = 0
            try:
                for root, _, files in os.walk(item_path):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in video_exts or ext in book_exts:
                            has_media = True
                            f_sz = os.path.getsize(os.path.join(root, f))
                            sz += f_sz
                            if ext in video_exts:
                                video_count += 1
                            if f_sz > largest_file_size:
                                largest_file_size = f_sz
                                largest_file_name = f
            except Exception:
                pass

            if has_media:
                if mode in ["series_episodes", "series_episode"]:
                    # Extract individual episode files inside the folder
                    try:
                        for root, _, files in os.walk(item_path):
                            for f in sorted(files):
                                if os.path.splitext(f)[1].lower() in video_exts:
                                    if len(candidates) >= limit:
                                        break
                                    fp = os.path.join(root, f).replace("\\", "/")
                                    candidates.append({
                                        "path": fp,
                                        "name": f,
                                        "search_name": f,
                                        "is_dir": False,
                                        "size_bytes": os.path.getsize(fp),
                                        "mode": "episode"
                                    })
                    except Exception:
                        pass
                else:
                    if mode in ["films", "film"]:
                        folder_mode = "single"
                    elif "manga" in mode or "/mangas" in folder_lower:
                        folder_mode = "manga_pack"
                    elif any(k in item_name.lower() for k in ["s0", "saison", "season", "s1", "s2", "s3"]):
                        folder_mode = "season_pack"
                    elif video_count > 1:
                        folder_mode = "integrale"
                    else:
                        folder_mode = "single"

                    search_name = largest_file_name if largest_file_name else item_name
                    candidates.append({
                        "path": item_path,
                        "name": item_name,
                        "search_name": search_name,
                        "is_dir": True,
                        "size_bytes": sz,
                        "mode": folder_mode
                    })

    # Query C411 for each candidate
    results = []
    for item in candidates:
        import re
        name = item.get("search_name") or item["name"]
        sz_mb = item["size_bytes"] / (1024 * 1024)
        size_str = f"{sz_mb / 1024:.2f} Go" if sz_mb >= 1024 else f"{sz_mb:.2f} Mo"

        res_match = re.search(r"\b(2160p|1080p|720p|576p|480p)\b", name, re.IGNORECASE)
        resolution = res_match.group(1).lower() if res_match else item.get("resolution", "1080p")

        src_match = re.search(r"\b(BluRay|BDRip|BRRip|WEB-DL|WEBRip|WEB|HDTV|DVDRip|REMUX)\b", name, re.IGNORECASE)
        source = src_match.group(1) if src_match else item.get("source", "WEB")

        ext_tag, _ = ReleaseNamer.extract_existing_tag(name)
        tag = ext_tag if ext_tag else "NOTAG"

        # Clean release title for presentation
        clean_title = ReleaseNamer.clean_title(item["name"])

        # Determine category for C411 Torznab query
        cat_id = None
        if "films" in folder_lower:
            cat_id = "2000"
        elif "series" in folder_lower:
            cat_id = "2010"
        elif "mangas" in folder_lower or "manga" in folder_lower:
            cat_id = "2020"

        # Check duplicates on C411
        dupe_res = await tracker.check_duplicates(
            title=name,
            resolution=resolution,
            source=source,
            tag=tag,
            category_id=cat_id
        )

        status = "green"
        status_label = "Absent de C411"
        details = "Aucun doublon trouvé."
        match_item = None

        if dupe_res.get("same_tag_duplicates"):
            status = "red"
            top = dupe_res["same_tag_duplicates"][0]
            status_label = f"Doublon Strict Team (-{dupe_res.get('matched_tag', tag)})"
            details = f"{top['title']} ({top['seeders']}S / {top['size']})"
            match_item = top
        elif dupe_res.get("same_quality_duplicates"):
            status = "yellow"
            top = dupe_res["same_quality_duplicates"][0]
            status_label = "Même Format (Autre Team)"
            details = f"{top['title']} ({top['seeders']}S / {top['size']})"
            match_item = top
        elif dupe_res.get("other_versions"):
            status = "green"
            top = dupe_res["other_versions"][0]
            status_label = "Qualité Distincte (Autorisé)"
            details = f"{top['title']} ({top['seeders']}S / {top['size']})"
            match_item = top

        results.append({
            "path": item["path"],
            "name": item["name"],
            "clean_title": clean_title,
            "is_dir": item["is_dir"],
            "size": size_str,
            "size_str": size_str,
            "size_bytes": item["size_bytes"],
            "resolution": resolution.upper(),
            "source": source,
            "tag": tag,
            "mode": item["mode"],
            "suggested_mode": item["mode"],
            "status": status,
            "status_code": status,
            "status_label": status_label,
            "details": details,
            "c411_match": match_item,
            "duplicates_info": dupe_res
        })
        await asyncio.sleep(0.04)

    return {
        "folder_path": req.folder_path,
        "scan_mode": mode,
        "total_scanned": len(results),
        "results": results,
        "items": results
    }

@app.get("/api/download")
async def download_file(path: str):
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Fichier non trouvé.")
    return FileResponse(abs_path, filename=os.path.basename(abs_path))

@app.get("/api/history")
async def get_history():
    return load_history()

if __name__ == "__main__":
    config = get_config()
    port = int(os.getenv("PORT", config.web_port or 30017))
    print(f"Démarrage de Torrent Generator sur le port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
