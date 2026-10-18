import re
from typing import Dict, Any, Tuple, Optional

try:
    from unidecode import unidecode
except ImportError:
    import unicodedata
    def unidecode(text: str) -> str:
        return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')



class ReleaseNamer:
    # Known team or group regex at the end of filenames
    TAG_REGEX = re.compile(r"-([A-Za-z0-9_]+)(?:\.[a-zA-Z0-9]+)?$")
    
    # Common video sources
    SOURCES = ["BluRay", "BDRip", "BRRip", "WEB-DL", "WEBRip", "WEB", "HDTV", "DVDRip", "DVD", "REMUX", "UHD.BluRay"]
    
    # Known languages
    LANG_TAGS = ["MULTI.TRUEFRENCH", "MULTI.VFF", "MULTI.VF2", "MULTI.VFQ", "MULTI.VFI", "MULTI.VOSTFR", "MULTI", "TRUEFRENCH", "VFF", "VF2", "VFQ", "VFI", "VOF", "VOSTFR", "FRENCH", "ENGLISH"]

    @classmethod
    def clean_title(cls, text: str) -> str:
        """Removes accents, replaces spaces and underscores with dots, cleans illegal characters."""
        # Unidecode accents (e.g. "é" -> "e", "œ" -> "oe")
        ascii_text = unidecode(text)
        # Replace spaces, dashes (except team dash), underscores with dots
        cleaned = re.sub(r"[\s_\-]+", ".", ascii_text)
        # Remove unwanted punctuation
        cleaned = re.sub(r"[^\w\.]", "", cleaned)
        # Collapse multiple dots
        cleaned = re.sub(r"\.+", ".", cleaned).strip(".")
        return cleaned

    @classmethod
    def extract_existing_tag(cls, filename: str) -> Tuple[Optional[str], str]:
        """
        Attempts to extract an existing release group/author tag from a filename.
        Returns: (tag, filename_without_tag)
        """
        # Strip extension first
        name_no_ext = filename
        if "." in filename:
            name_no_ext = ".".join(filename.split(".")[:-1])

        # Match -TEAM at the end
        match = re.search(r"-([A-Za-z0-9]+)$", name_no_ext)
        if match:
            tag = match.group(1)
            # Exclude known false positives (e.g. -x264, -1080p, -H264)
            if tag.lower() not in ["x264", "x265", "h264", "h265", "hevc", "avc", "1080p", "720p", "2160p", "aac"]:
                base = name_no_ext[:match.start()]
                return tag, base

        return None, name_no_ext

    @classmethod
    def format_c411_title(
        cls,
        raw_name: str,
        media_info: Dict[str, Any],
        category: str = "Films & Vidéos",
        custom_year: Optional[str] = None,
        custom_source: Optional[str] = None,
        custom_lang: Optional[str] = None,
        custom_tag: Optional[str] = None,
        release_mode: str = "single"  # single, episode, season_pack, integrale, manga_pack
    ) -> Dict[str, Any]:
        """
        Generates a compliant C411 release name and validates anti-detag rules.
        Recovers original tags from embedded MKV title, parent folder or companion NFO if Sonarr/Radarr renamed files.
        """
        # 1. First check filename
        existing_tag, base_name = cls.extract_existing_tag(raw_name)
        tag_source = "nom de fichier" if existing_tag else None

        # 2. If no tag in filename, check embedded MKV title (frequent with Sonarr/Radarr)
        if not existing_tag and media_info.get("embedded_title"):
            emb_tag, emb_base = cls.extract_existing_tag(media_info["embedded_title"])
            if emb_tag:
                existing_tag = emb_tag
                tag_source = "métadonnées MKV internes (restauré après renommage Sonarr/Radarr)"

        # 3. Check parent folder name
        if not existing_tag and media_info.get("parent_folder"):
            p_tag, _ = cls.extract_existing_tag(media_info["parent_folder"])
            if p_tag:
                existing_tag = p_tag
                tag_source = "dossier parent d'origine"

        # 4. Check companion .nfo file
        if not existing_tag and media_info.get("companion_nfo_tag"):
            existing_tag = media_info["companion_nfo_tag"]
            tag_source = "fichier .nfo associé"

        # Anti-detag decision
        chosen_tag = existing_tag if existing_tag else (custom_tag or "NOTAG")
        if existing_tag:
            detag_warning = f"Tag d'origine détecté ({tag_source}) : '{existing_tag}'. Il a été conservé conformément aux règles anti-DETAG de C411."
        else:
            detag_warning = "Aucun tag d'origine détecté (fichier potentiellement renommé par Radarr/Sonarr). Par défaut, le suffixe '-NOTAG' est appliqué comme requis par C411."

        # Year detection
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_name)
        if not year_match and media_info.get("embedded_title"):
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", media_info["embedded_title"])
        year = custom_year or (year_match.group(1) if year_match else "")

        # Resolution
        resolution = media_info.get("resolution", "1080p")

        # Source
        source = custom_source or "WEB"
        for s in cls.SOURCES:
            if re.search(rf"\b{re.escape(s)}\b", raw_name, re.IGNORECASE):
                source = s
                break

        # Video codec
        video_codec = media_info.get("video_codec", "x264")

        # Audio spec (e.g. EAC3.5.1, AC3.5.1, AAC.2.0, DTS.5.1)
        audio_spec = "AAC.2.0"
        audio_tracks = media_info.get("audio_tracks", [])
        if audio_tracks:
            first_audio = audio_tracks[0]
            fmt = first_audio.get("format", "AAC").upper()
            if "E-AC-3" in fmt or "EAC3" in fmt:
                fmt_tag = "EAC3"
            elif "AC-3" in fmt or "AC3" in fmt:
                fmt_tag = "AC3"
            elif "DTS-HD" in fmt:
                fmt_tag = "DTS.HD.MA"
            elif "DTS" in fmt:
                fmt_tag = "DTS"
            elif "TRUEHD" in fmt:
                fmt_tag = "TrueHD"
            elif "FLAC" in fmt:
                fmt_tag = "FLAC"
            else:
                fmt_tag = "AAC"
            
            channels = first_audio.get("channels", "2.0")
            audio_spec = f"{fmt_tag}.{channels}"

        # HDR tags
        hdr_tags = media_info.get("hdr_tags", [])
        hdr_str = ".".join(hdr_tags) if hdr_tags else ""

        # Language tag
        lang_tag = custom_lang or media_info.get("detected_lang_tag", "MULTI.VFF")

        # Detect Season / Episode / Tome tokens (e.g. S01E05, S01, E1050, T01, T01-T20)
        se_match = re.search(r"\b(S\d{1,2}E\d{1,4})\b", raw_name, re.IGNORECASE)
        s_match = re.search(r"\b(S\d{1,2})\b", raw_name, re.IGNORECASE)
        e_match = re.search(r"\b(?:E|Ep|Episode[\s\.]*)(\d{1,4})\b", raw_name, re.IGNORECASE)
        t_match = re.search(r"\b(?:T|Tome|Vol|Volume[\s\.]*)(\d{1,3})\b", raw_name, re.IGNORECASE)
        t_range_match = re.search(r"\b(T\d{1,3}[\-\.]T\d{1,3})\b", raw_name, re.IGNORECASE)

        if not se_match and media_info.get("embedded_title"):
            se_match = re.search(r"\b(S\d{1,2}E\d{1,4})\b", media_info["embedded_title"], re.IGNORECASE)
        if not s_match and media_info.get("embedded_title"):
            s_match = re.search(r"\b(S\d{1,2})\b", media_info["embedded_title"], re.IGNORECASE)

        # Clean title base (strip SxxExx, year, qualities, codecs)
        title_clean = base_name
        # Remove SxxExx, Sxx, Exx, Txx, INTEGRALE from title base
        title_clean = re.sub(r"\b(S\d{1,2}E\d{1,4}|S\d{1,2}|E\d{1,4}|Ep\d{1,4}|Episode[\s\.]*\d+|T\d{1,3}|Tome[\s\.]*\d+|INTEGRALE)\b", "", title_clean, flags=re.IGNORECASE)
        if year:
            title_clean = title_clean.split(year)[0]

        # Strip common trailing tags/qualities from title_clean
        title_clean = re.sub(r"\b(2160p|1080p|720p|576p|480p|BluRay|BDRip|BRRip|WEB-DL|WEBRip|WEB|HDTV|DVDRip|REMUX|x264|x265|HEVC|AVC|AAC|AC3|DTS|MULTI|VFF|VF2|VFQ|VFI|VOSTFR|TRUEFRENCH|FRENCH)\b.*$", "", title_clean, flags=re.IGNORECASE)

        title_part = cls.clean_title(title_clean)
        if not title_part:
            title_part = "Release"

        # Construct final title based on C411 category & mode schema:
        parts = [title_part]
        
        if release_mode == "episode":
            if year:
                parts.append(year)
            if se_match:
                parts.append(se_match.group(1).upper())
            elif s_match and e_match:
                s_num = int(re.sub(r"[^\d]", "", s_match.group(1)))
                e_num = int(e_match.group(1))
                parts.append(f"S{s_num:02d}E{e_num:02d}")
            elif e_match:
                e_num = int(e_match.group(1))
                parts.append(f"E{e_num:02d}" if e_num < 100 else f"E{e_num}")
            else:
                parts.append("S01E01")
        elif release_mode == "season_pack":
            token = s_match.group(1).upper() if s_match else "S01"
            parts.append(token)
        elif release_mode == "integrale":
            if year:
                parts.append(year)
            parts.append("INTEGRALE")
        elif release_mode == "manga_tome":
            if t_match:
                t_num = int(t_match.group(1))
                parts.append(f"T{t_num:02d}")
            else:
                parts.append("T01")
        elif release_mode == "manga_pack":
            if t_range_match:
                parts.append(t_range_match.group(1).upper())
            else:
                parts.append("INTEGRALE")
        elif release_mode == "single":
            if year:
                parts.append(year)

        # Append technical specs (audio, video, etc.)
        is_book = release_mode in ["manga_tome", "manga_pack"] or (category and ("ebook" in category.lower() or "livre" in category.lower() or "bd" in category.lower()))
        if is_book:
            if lang_tag:
                parts.append(lang_tag)
            # Books don't need resolution / video codecs
        else:
            if lang_tag:
                parts.append(lang_tag)
            if resolution and resolution != "Autre":
                parts.append(resolution)
            if source:
                parts.append(source)
            if hdr_str:
                parts.append(hdr_str)
            if audio_spec:
                parts.append(audio_spec)
            if video_codec:
                parts.append(video_codec)

        full_title = ".".join(parts) + f"-{chosen_tag}"

        return {
            "title": full_title,
            "detected_tag": existing_tag,
            "final_tag": chosen_tag,
            "detag_warning": detag_warning,
            "year": year,
            "resolution": resolution,
            "source": source,
            "language": lang_tag,
            "video_codec": video_codec,
            "audio_spec": audio_spec
        }
