import os
import re
from typing import Dict, Any, List

C411_ASCII_HEADER = r"""
  ██████╗ ██╗  ██╗ ██╗ ██╗
 ██╔════╝ ██║  ██║███║███║
 ██║      ███████║╚██║╚██║
 ██║      ╚════██║ ██║ ██║
 ╚██████╗      ██║ ██║ ██║
  ╚═════╝      ╚═╝ ╚═╝ ╚═╝
  ═══════════════════════════════════════════════════════════
                 COMMUNITY 411 - RELEASE NFO
  ═══════════════════════════════════════════════════════════
"""

def sanitize_mediainfo_text(raw_text: str, file_name: str) -> str:
    """Ensures no NAS / host directories leak into the NFO output."""
    if not raw_text:
        return ""
    base = os.path.basename(file_name) if file_name else ""
    lines = []
    for line in raw_text.splitlines():
        if re.match(r"^\s*(?:Complete\s*name|Nom\s*complet|CompleteName)\s*:", line, re.IGNORECASE):
            prefix = line.split(":", 1)[0]
            val = line.split(":", 1)[1].strip()
            name = base or os.path.basename(val)
            lines.append(f"{prefix}: {name}")
        elif re.match(r"^\s*(?:Folder\s*name|Nom\s*du\s*dossier|Directory)\s*:", line, re.IGNORECASE):
            continue
        else:
            lines.append(line)
    return "\n".join(lines)

class NfoGenerator:
    @classmethod
    def generate(
        cls,
        release_title: str,
        media_info: Dict[str, Any],
        source: str = "WEB",
        vod_platform: str = "",
        tag: str = "NOTAG"
    ) -> str:
        """
        Generates a standard, compliant C411 .nfo file.
        """
        total_size_mb = media_info.get("file_size", 0) / (1024 * 1024)
        total_size_str = f"{total_size_mb / 1024:.2f} Go" if total_size_mb >= 1024 else f"{total_size_mb:.2f} Mo"

        lines = []
        lines.append(C411_ASCII_HEADER.strip("\n"))
        lines.append("")
        lines.append("───────────────────────────────────────────────────────────")
        lines.append("                INFORMATIONS GÉNÉRALES")
        lines.append("───────────────────────────────────────────────────────────")
        lines.append(f"  Titre de la release : {release_title}")
        lines.append(f"  Format conteneur    : {media_info.get('container', 'MKV')}")
        lines.append(f"  Durée totale        : {media_info.get('duration', 'N/A')}")
        lines.append(f"  Taille totale       : {total_size_str}")
        lines.append(f"  Source              : {source}")
        if vod_platform:
            lines.append(f"  Plateforme VOD      : {vod_platform}")
        lines.append(f"  Signature Team/Tag  : {tag}")
        lines.append("")
        
        lines.append("───────────────────────────────────────────────────────────")
        lines.append("                INFORMATIONS VIDÉO")
        lines.append("───────────────────────────────────────────────────────────")
        lines.append(f"  Codec vidéo         : {media_info.get('video_codec', 'x264')} ({media_info.get('video_format', '')})")
        lines.append(f"  Débit vidéo         : {media_info.get('video_bitrate', 'N/A')}")
        lines.append(f"  Résolution          : {media_info.get('width', 0)}x{media_info.get('height', 0)} ({media_info.get('resolution', '')})")
        lines.append(f"  Images par seconde  : {media_info.get('frame_rate', '24.000')} FPS")
        hdr_tags = media_info.get("hdr_tags", [])
        if hdr_tags:
            lines.append(f"  Format HDR          : {', '.join(hdr_tags)}")
        lines.append("")

        lines.append("───────────────────────────────────────────────────────────")
        lines.append("                INFORMATIONS AUDIO")
        lines.append("───────────────────────────────────────────────────────────")
        audio_tracks = media_info.get("audio_tracks", [])
        if audio_tracks:
            for idx, a in enumerate(audio_tracks, start=1):
                track_line = f"  Piste #{idx}           : {a.get('language', 'N/A')} | {a.get('format', '')} | {a.get('channels', '')} ch"
                if a.get('bitrate'):
                    track_line += f" @ {a.get('bitrate')}"
                if a.get('title'):
                    track_line += f" ({a.get('title')})"
                lines.append(track_line)
        else:
            lines.append("  Aucune piste audio détectée")
        lines.append("")

        lines.append("───────────────────────────────────────────────────────────")
        lines.append("                INFORMATIONS SOUS-TITRES")
        lines.append("───────────────────────────────────────────────────────────")
        subtitle_tracks = media_info.get("subtitle_tracks", [])
        if subtitle_tracks:
            for idx, s in enumerate(subtitle_tracks, start=1):
                sub_type = "Forcé" if s.get('forced') else "Complet"
                sub_line = f"  Piste #{idx}           : {s.get('language', 'N/A')} | {s.get('format', 'UTF-8')} | Type: {sub_type}"
                if s.get('title'):
                    sub_line += f" ({s.get('title')})"
                lines.append(sub_line)
        else:
            lines.append("  Aucun sous-titre présent")
        lines.append("")

        # Raw MediaInfo (Sanitized: only filename, no container/NAS paths)
        raw_text = media_info.get("raw_text", "")
        if raw_text:
            sanitized_raw = sanitize_mediainfo_text(raw_text, media_info.get("file_name", ""))
            lines.append("═══════════════════════════════════════════════════════════")
            lines.append("                MEDIAINFO COMPLET")
            lines.append("═══════════════════════════════════════════════════════════")
            lines.append(sanitized_raw.strip())
            lines.append("")

        return "\n".join(lines)
