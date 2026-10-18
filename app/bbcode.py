from typing import Dict, Any, Optional

class BBCodeGenerator:
    @classmethod
    def generate(
        cls,
        release_title: str,
        media_info: Dict[str, Any],
        synopsis: Optional[str] = None,
        poster_url: Optional[str] = None,
        source: str = "WEB",
        vod_platform: str = "",
        tag: str = "NOTAG",
        nfo_text: Optional[str] = None
    ) -> str:
        """
        Generates clean BBCode presentation strictly compliant with C411 rules.
        """
        total_size_mb = media_info.get("file_size", 0) / (1024 * 1024)
        total_size_str = f"{total_size_mb / 1024:.2f} Go" if total_size_mb >= 1024 else f"{total_size_mb:.2f} Mo"

        bb = []
        bb.append("[center]")
        
        # Poster / Image
        if poster_url:
            bb.append(f"[img]{poster_url}[/img]")
            bb.append("")

        # Title
        bb.append(f"[size=5][b][color=#3498db]{release_title}[/color][/b][/size]")
        bb.append("[hr]")

        # Synopsis
        if synopsis:
            bb.append("[size=4][b][color=#e74c3c]SYNOPSIS[/color][/b][/size]")
            bb.append(f"[quote]{synopsis}[/quote]")
            bb.append("")

        # Release Info
        bb.append("[size=4][b][color=#2ecc71]INFORMATIONS SUR LA RELEASE[/color][/b][/size]")
        bb.append(f"[b]Format conteneur :[/b] {media_info.get('container', 'MKV')}")
        bb.append(f"[b]Durée :[/b] {media_info.get('duration', 'N/A')}")
        bb.append(f"[b]Taille totale :[/b] {total_size_str}")
        bb.append(f"[b]Source :[/b] {source}")
        if vod_platform:
            bb.append(f"[b]Plateforme VOD :[/b] {vod_platform}")
        bb.append(f"[b]Signature / Tag :[/b] {tag}")
        bb.append("")

        # Technical Info
        bb.append("[size=4][b][color=#f39c12]DÉTAILS TECHNIQUES[/color][/b][/size]")
        
        # Video
        video_details = f"{media_info.get('video_codec', 'x264')} | {media_info.get('resolution', '')} ({media_info.get('width', 0)}x{media_info.get('height', 0)})"
        if media_info.get("video_bitrate"):
            video_details += f" @ {media_info.get('video_bitrate')}"
        hdr_tags = media_info.get("hdr_tags", [])
        if hdr_tags:
            video_details += f" | HDR: {', '.join(hdr_tags)}"
        bb.append(f"[b]Vidéo :[/b] {video_details}")

        # Audio
        audio_tracks = media_info.get("audio_tracks", [])
        if audio_tracks:
            for idx, a in enumerate(audio_tracks, start=1):
                track_line = f"Piste #{idx} - {a.get('language', 'N/A')} : {a.get('format', '')} {a.get('channels', '')} ch"
                if a.get('bitrate'):
                    track_line += f" @ {a.get('bitrate')}"
                if a.get('title'):
                    track_line += f" ({a.get('title')})"
                bb.append(f"[b]Audio #{idx} :[/b] {track_line}")
        else:
            bb.append("[b]Audio :[/b] Non spécifié")

        # Subtitles
        subtitle_tracks = media_info.get("subtitle_tracks", [])
        if subtitle_tracks:
            for idx, s in enumerate(subtitle_tracks, start=1):
                sub_type = "Forcé" if s.get('forced') else "Complet"
                sub_line = f"{s.get('language', 'N/A')} ({s.get('format', 'UTF-8')}) - Type : {sub_type}"
                if s.get('title'):
                    sub_line += f" [{s.get('title')}]"
                bb.append(f"[b]Sous-titre #{idx} :[/b] {sub_line}")
        else:
            bb.append("[b]Sous-titres :[/b] Aucun")

        bb.append("")

        # NFO Spoiler
        if nfo_text:
            bb.append("[size=4][b][color=#9b59b6]NFO TECHNIQUE[/color][/b][/size]")
            bb.append(f"[spoiler=Afficher le NFO][font=monospace]{nfo_text}[/font][/spoiler]")
            bb.append("")

        bb.append("[hr]")
        bb.append("[i]Release partagée avec Torrent Generator C411[/i]")
        bb.append("[/center]")

        return "\n".join(bb)
