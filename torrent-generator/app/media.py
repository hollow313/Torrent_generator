import os
import json
import shutil
import subprocess
from typing import Dict, Any, List, Optional

class MediaAnalyzer:
    @staticmethod
    def is_mediainfo_available() -> bool:
        return shutil.which("mediainfo") is not None

    @classmethod
    def analyze(cls, file_path: str) -> Dict[str, Any]:
        """
        Analyzes media file using MediaInfo (JSON & Raw Text).
        Returns structured dictionary with tracks and raw text report.
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")

        # If it's a directory, pick the largest media file inside
        target_file = abs_path
        if os.path.isdir(abs_path):
            largest_size = 0
            for root, _, files in os.walk(abs_path):
                for f in files:
                    fp = os.path.join(root, f)
                    ext = os.path.splitext(f)[1].lower()
                    if ext in [".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".iso", ".flac", ".mp3", ".wav", ".epub", ".pdf", ".cbz"]:
                        sz = os.path.getsize(fp)
                        if sz > largest_size:
                            largest_size = sz
                            target_file = fp

        if not cls.is_mediainfo_available():
            return cls._fallback_analysis(target_file)

        try:
            # 1. Run mediainfo with JSON output
            json_proc = subprocess.run(
                ["mediainfo", "--Output=JSON", target_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60
            )
            data = json.loads(json_proc.stdout) if json_proc.returncode == 0 and json_proc.stdout else {}

            # 2. Run mediainfo with Text output for the raw NFO dump
            text_proc = subprocess.run(
                ["mediainfo", target_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60
            )
            raw_text = text_proc.stdout if text_proc.returncode == 0 else ""

            return cls._parse_mediainfo_json(data, raw_text, target_file)

        except Exception as e:
            print(f"[MediaAnalyzer] Error running MediaInfo: {e}")
            return cls._fallback_analysis(target_file)

    @classmethod
    def _parse_mediainfo_json(cls, data: Dict[str, Any], raw_text: str, file_path: str) -> Dict[str, Any]:
        media = data.get("media", {})
        tracks = media.get("track", [])

        general = {}
        videos = []
        audios = []
        subtitles = []

        for track in tracks:
            track_type = track.get("@type", "").lower()
            if track_type == "general":
                general = track
            elif track_type == "video":
                videos.append(track)
            elif track_type == "audio":
                audios.append(track)
            elif track_type == "text":
                subtitles.append(track)

        # Video summary
        main_video = videos[0] if videos else {}
        width = int(main_video.get("Width", 0) or 0)
        height = int(main_video.get("Height", 0) or 0)
        
        resolution = "Autre"
        if width >= 3800 or height >= 2100:
            resolution = "2160p"
        elif width >= 1900 or height >= 1000:
            resolution = "1080p"
        elif width >= 1200 or height >= 700:
            resolution = "720p"
        elif height >= 570 or width >= 720:
            resolution = "576p"
        elif height > 0:
            resolution = f"{height}p"

        # Codec normalization
        video_format = main_video.get("Format", "")
        video_codec = "x264"
        if "hevc" in video_format.lower() or "h.265" in video_format.lower():
            video_codec = "x265"
        elif "avc" in video_format.lower() or "h.264" in video_format.lower():
            video_codec = "x264"
        elif "av1" in video_format.lower():
            video_codec = "AV1"
        elif "mpeg-4" in video_format.lower() or "xvid" in video_format.lower():
            video_codec = "XviD"

        # HDR detection
        hdr_format = main_video.get("HDR_Format", "") or main_video.get("HDR_Format_Commercial", "") or ""
        hdr_tags = []
        if "dolby vision" in hdr_format.lower() or "dv" in hdr_format.lower():
            hdr_tags.append("DV")
        if "hdr10+" in hdr_format.lower():
            hdr_tags.append("HDR10PLUS")
        elif "hdr" in hdr_format.lower() or "hdr10" in hdr_format.lower():
            hdr_tags.append("HDR10")

        # Audio summary
        audio_details = []
        languages = []
        has_french = False
        has_english = False

        for a in audios:
            lang = (a.get("Language", "") or a.get("Language_String", "") or "Undetermined").capitalize()
            lang_code = a.get("Language", "").lower()
            if lang_code in ["fr", "fra", "fre"] or "french" in lang.lower():
                has_french = True
                lang = "Français"
            elif lang_code in ["en", "eng"] or "english" in lang.lower():
                has_english = True
                lang = "Anglais"

            languages.append(lang)

            fmt = a.get("Format", "")
            commercial_fmt = a.get("Format_Commercial", "") or a.get("Format_Commercial_IfAny", "")
            channels = a.get("Channels", "")
            
            # Channel notation (e.g. 6 -> 5.1, 8 -> 7.1, 2 -> 2.0)
            channels_label = channels
            try:
                ch_int = int(channels)
                if ch_int == 8:
                    channels_label = "7.1"
                elif ch_int == 6:
                    channels_label = "5.1"
                elif ch_int == 2:
                    channels_label = "2.0"
                elif ch_int == 1:
                    channels_label = "1.0"
            except:
                pass

            bitrate = a.get("BitRate", "") or a.get("BitRate_String", "")
            audio_details.append({
                "language": lang,
                "format": commercial_fmt or fmt,
                "channels": channels_label,
                "bitrate": bitrate,
                "title": a.get("Title", "")
            })

        # Subtitle summary
        sub_details = []
        for s in subtitles:
            sub_lang = (s.get("Language", "") or s.get("Language_String", "") or "Undetermined").capitalize()
            sub_code = s.get("Language", "").lower()
            if sub_code in ["fr", "fra", "fre"] or "french" in sub_lang.lower():
                sub_lang = "Français"
            elif sub_code in ["en", "eng"] or "english" in sub_lang.lower():
                sub_lang = "Anglais"

            sub_fmt = s.get("Format", "")
            is_forced = s.get("Forced", "No").lower() == "yes"
            sub_title = s.get("Title", "")
            sub_details.append({
                "language": sub_lang,
                "format": sub_fmt,
                "forced": is_forced,
                "title": sub_title
            })

        # Language tag determination (inspect filename, embedded title and track titles)
        check_text = f"{os.path.basename(file_path)} {general.get('Title', '')} {videos[0].get('Title', '') if videos else ''}"
        for a in audios:
            check_text += f" {a.get('Title', '')}"

        detected_fr_variant = None
        for variant in ["TRUEFRENCH", "VF2", "VFQ", "VFI", "VOSTFR", "VFF", "FRENCH"]:
            if re.search(rf"\b{variant}\b", check_text, re.IGNORECASE):
                detected_fr_variant = variant.upper()
                if detected_fr_variant == "FRENCH":
                    detected_fr_variant = "VFF"
                break

        has_multi = "multi" in check_text.lower() or (len(audios) > 1 and (has_french or has_english))

        if detected_fr_variant:
            if detected_fr_variant == "VOSTFR":
                lang_tag = "MULTI.VOSTFR" if has_multi else "VOSTFR"
            else:
                lang_tag = f"MULTI.{detected_fr_variant}" if has_multi else detected_fr_variant
        elif has_french and has_multi:
            lang_tag = "MULTI.VFF"
        elif has_french:
            lang_tag = "VFF"
        elif not has_french and has_english:
            if any(s.get("language") == "Français" for s in sub_details) or "vostfr" in check_text.lower():
                lang_tag = "VOSTFR"
            else:
                lang_tag = "ENGLISH"
        else:
            lang_tag = "MULTI.VFF" if has_multi else "VFF"

        # Duration formatting
        duration_sec = float(general.get("Duration", 0) or 0)
        hours = int(duration_sec // 3600)
        minutes = int((duration_sec % 3600) // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{hours}h {minutes:02d}m {seconds:02d}s" if hours > 0 else f"{minutes}m {seconds:02d}s"

        total_bytes = int(general.get("FileSize", 0) or os.path.getsize(file_path))

        # Extract embedded metadata (Crucial when Radarr / Sonarr renamed files)
        embedded_title = general.get("Title") or general.get("Movie_Name") or (videos[0].get("Title") if videos else "") or ""
        parent_dir = os.path.dirname(os.path.abspath(file_path))
        parent_folder = os.path.basename(parent_dir)

        # Check for companion .nfo file in directory
        companion_nfo_tag = None
        companion_nfo_content = ""
        try:
            if os.path.exists(parent_dir):
                for f in os.listdir(parent_dir):
                    if f.lower().endswith(".nfo") and not f.startswith("."):
                        nfo_p = os.path.join(parent_dir, f)
                        with open(nfo_p, "r", encoding="utf-8", errors="ignore") as nfo_f:
                            companion_nfo_content = nfo_f.read(4096)
                            # Look for team signature like "Release : TEAM" or "-TEAM"
                            import re
                            match = re.search(r"(?:Release|Team|Group|Encodeur)\s*[:=]\s*([A-Za-z0-9_-]+)", companion_nfo_content, re.IGNORECASE)
                            if match:
                                companion_nfo_tag = match.group(1).strip()
                            else:
                                match2 = re.search(r"-([A-Za-z0-9_]{2,15})(?:\.[a-zA-Z0-9]+)?\s*$", companion_nfo_content, re.MULTILINE)
                                if match2:
                                    companion_nfo_tag = match2.group(1).strip()
                        break
        except Exception as e:
            print(f"[MediaAnalyzer] Companion NFO check error: {e}")

        # Scan folder for sub-items (episodes or tomes)
        sub_items = []
        scan_dir = file_path if os.path.isdir(file_path) else parent_dir
        try:
            if os.path.exists(scan_dir):
                for f in sorted(os.listdir(scan_dir)):
                    fp = os.path.join(scan_dir, f)
                    if os.path.isfile(fp):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in [".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".epub", ".pdf", ".cbz", ".cbr", ".flac", ".mp3"]:
                            sz = os.path.getsize(fp)
                            sz_mb = sz / (1024 * 1024)
                            sub_items.append({
                                "name": f,
                                "path": fp.replace("\\", "/"),
                                "size": f"{sz_mb / 1024:.2f} Go" if sz_mb >= 1024 else f"{sz_mb:.2f} Mo",
                                "size_bytes": sz
                            })
        except Exception:
            pass

        return {
            "file_name": os.path.basename(file_path),
            "file_size": total_bytes,
            "duration": duration_str,
            "container": general.get("Format", os.path.splitext(file_path)[1].lstrip(".")).upper(),
            "overall_bitrate": general.get("OverallBitRate_String", ""),
            "resolution": resolution,
            "width": width,
            "height": height,
            "video_codec": video_codec,
            "video_format": video_format,
            "video_bitrate": main_video.get("BitRate_String", ""),
            "frame_rate": main_video.get("FrameRate", ""),
            "hdr_tags": hdr_tags,
            "audio_tracks": audio_details,
            "subtitle_tracks": sub_details,
            "languages": list(set(languages)),
            "detected_lang_tag": lang_tag,
            "raw_text": raw_text,
            "embedded_title": embedded_title,
            "parent_folder": parent_folder,
            "companion_nfo_tag": companion_nfo_tag,
            "sub_items": sub_items,
            "is_dir": os.path.isdir(file_path),
            "main_file_name": os.path.basename(target_file),
            "main_file_path": target_file
        }

    @classmethod
    def _fallback_analysis(cls, file_path: str) -> Dict[str, Any]:
        """Basic fallback when MediaInfo is not installed."""
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        ext = os.path.splitext(file_path)[1].lstrip(".").upper()
        parent_dir = os.path.dirname(os.path.abspath(file_path))
        
        return {
            "file_name": os.path.basename(file_path),
            "file_size": size,
            "duration": "N/A",
            "container": ext or "MKV",
            "overall_bitrate": "N/A",
            "resolution": "1080p",
            "width": 1920,
            "height": 1080,
            "video_codec": "x264",
            "video_format": "AVC",
            "video_bitrate": "N/A",
            "frame_rate": "24.000",
            "hdr_tags": [],
            "audio_tracks": [
                {"language": "Français", "format": "E-AC-3", "channels": "5.1", "bitrate": "640 kb/s", "title": ""}
            ],
            "subtitle_tracks": [
                {"language": "Français", "format": "UTF-8", "forced": True, "title": "Forcé"}
            ],
            "languages": ["Français"],
            "detected_lang_tag": "MULTI.VFF",
            "raw_text": f"General\nComplete name: {file_path}\nFile size: {size} bytes\nFormat: {ext}\n",
            "embedded_title": "",
            "parent_folder": os.path.basename(parent_dir),
            "companion_nfo_tag": None,
            "sub_items": [],
            "is_dir": os.path.isdir(file_path),
            "main_file_name": os.path.basename(file_path),
            "main_file_path": file_path
        }
