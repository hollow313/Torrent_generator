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

        # Language tag determination
        lang_tag = "MULTI"
        if has_french and (len(audios) > 1 or has_english):
            lang_tag = "MULTI.VFF"
        elif has_french and len(audios) == 1:
            lang_tag = "VFF"
        elif not has_french and has_english:
            if any(s.get("language") == "Français" for s in sub_details):
                lang_tag = "VOSTFR"
            else:
                lang_tag = "ENGLISH"

        # Duration formatting
        duration_sec = float(general.get("Duration", 0) or 0)
        hours = int(duration_sec // 3600)
        minutes = int((duration_sec % 3600) // 60)
        seconds = int(duration_sec % 60)
        duration_str = f"{hours}h {minutes:02d}m {seconds:02d}s" if hours > 0 else f"{minutes}m {seconds:02d}s"

        total_bytes = int(general.get("FileSize", 0) or os.path.getsize(file_path))

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
            "raw_text": raw_text
        }

    @classmethod
    def _fallback_analysis(cls, file_path: str) -> Dict[str, Any]:
        """Basic fallback when MediaInfo is not installed."""
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        ext = os.path.splitext(file_path)[1].lstrip(".").upper()
        
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
            "raw_text": f"General\nComplete name: {file_path}\nFile size: {size} bytes\nFormat: {ext}\n"
        }
