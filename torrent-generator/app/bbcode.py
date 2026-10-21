import os
import re
from typing import Dict, Any, Optional, List

FLAG_MAPPING = {
    "français": "fr", "francais": "fr", "french": "fr", "fr": "fr", "fra": "fr", "fre": "fr",
    "vff": "fr", "vfq": "fr", "vf": "fr", "truefrench": "fr", "vf2": "fr",
    "anglais": "gb", "english": "gb", "en": "gb", "eng": "gb", "vo": "gb",
    "japonais": "jp", "japanese": "jp", "ja": "jp", "jpn": "jp",
    "allemand": "de", "german": "de", "de": "de", "deu": "de", "ger": "de",
    "espagnol": "es", "spanish": "es", "es": "es", "spa": "es",
    "italien": "it", "italian": "it", "it": "it", "ita": "it",
    "portugais": "pt", "portuguese": "pt", "pt": "pt", "por": "pt",
    "russe": "ru", "russian": "ru", "ru": "ru", "rus": "ru",
    "coréen": "kr", "coreen": "kr", "korean": "kr", "ko": "kr", "kor": "kr",
    "chinois": "cn", "chinese": "cn", "zh": "cn", "chi": "cn", "zho": "cn",
    "néerlandais": "nl", "neerlandais": "nl", "dutch": "nl", "nl": "nl", "nld": "nl",
    "polonais": "pl", "polish": "pl", "pl": "pl", "pol": "pl",
    "turc": "tr", "turkish": "tr", "tr": "tr", "tur": "tr",
    "arabe": "sa", "arabic": "sa", "ar": "sa", "ara": "sa",
    "suédois": "se", "suedois": "se", "swedish": "se", "sv": "se", "swe": "se",
    "danois": "dk", "danish": "dk", "da": "dk", "dan": "dk",
    "finnois": "fi", "finnish": "fi", "fi": "fi", "fin": "fi",
    "norvégien": "no", "norvegien": "no", "norwegian": "no", "no": "no", "nor": "no",
}

def get_flag_code(lang: str) -> str:
    lang_lower = (lang or "").lower().strip()
    for key, code in FLAG_MAPPING.items():
        if key in lang_lower:
            return code
    return "un"

class BBCodeGenerator:
    """
    Generates presentation descriptions in full compliance with C411 standards,
    using official C411 headers/banners and clean HTML layout matching community releases.
    """

    @classmethod
    def generate(
        cls,
        release_title: str,
        media_info: Dict[str, Any],
        source: str = "WEB",
        vod_platform: str = "",
        tag: str = "NOTAG",
        tmdb_data: Optional[Dict[str, Any]] = None,
        synopsis: Optional[str] = None,
        poster_url: Optional[str] = None,
        file_count: int = 1,
        nfo_text: Optional[str] = None
    ) -> str:
        # Calculate human readable size
        total_size_bytes = media_info.get("file_size", 0)
        total_size_mb = total_size_bytes / (1024 * 1024)
        total_size_str = f"{total_size_mb / 1024:.2f} GiB" if total_size_mb >= 1024 else f"{total_size_mb:.2f} MiB"

        # Determine metadata from tmdb_data or fallback
        t_data = tmdb_data or {}
        
        display_title = t_data.get("title")
        if not display_title:
            # Clean release title for display
            clean = release_title.replace(".", " ")
            clean = re.sub(r"\b(19\d\d|20\d\d)\b.*", "", clean).strip()
            display_title = clean or release_title

        year_str = t_data.get("year")
        if not year_str:
            ym = re.search(r"\b(19\d\d|20\d\d)\b", release_title)
            year_str = ym.group(1) if ym else ""

        poster = poster_url or t_data.get("poster_url") or ""
        synop = synopsis or t_data.get("synopsis") or "Aucun synopsis disponible."

        country = t_data.get("country") or "France"
        genres = t_data.get("genres_str") or (", ".join(t_data.get("genres", [])) if t_data.get("genres") else "Non renseigné")
        release_date = t_data.get("release_date_formatted") or t_data.get("release_date") or year_str or "Non renseigné"
        
        duration = t_data.get("duration") or media_info.get("duration", "N/A")
        directors = t_data.get("directors") or "Non renseigné"
        actors = t_data.get("cast") or "Non renseigné"
        vote_avg = str(t_data.get("vote_average", "N/A"))
        if vote_avg and vote_avg != "N/A" and not vote_avg.endswith("/10"):
            vote_avg_display = f"{vote_avg}/10"
        else:
            vote_avg_display = vote_avg

        imdb_url = t_data.get("imdb_url") or ""
        if imdb_url:
            imdb_link = f'<a href="{imdb_url}" rel="noopener noreferrer" class="text-emerald-500 hover:text-emerald-400 underline" target="_blank">Fiche du Film</a>'
        else:
            imdb_link = '<a href="" rel="noopener noreferrer" class="text-emerald-500 hover:text-emerald-400 underline" target="_blank">Fiche du Film</a>'

        # Video specifications
        res = media_info.get("resolution", "")
        if not res and media_info.get("height"):
            h = media_info.get("height", 0)
            res = "2160p" if h >= 2100 else ("1080p" if h >= 1000 else "720p")

        video_codec = media_info.get("video_codec", "H.264")
        if video_codec == "x264":
            video_codec = "H.264"
        elif video_codec == "x265":
            video_codec = "H.265 / HEVC"

        video_bitrate = media_info.get("video_bitrate", "") or media_info.get("overall_bitrate", "N/A")
        
        # Audio tracks rows
        audio_tracks = media_info.get("audio_tracks", [])
        audio_rows = []
        if audio_tracks:
            for idx, a in enumerate(audio_tracks, start=1):
                lang = a.get("language", "Français")
                flag = get_flag_code(lang)
                ch = a.get("channels", "2.0")
                fmt = a.get("format", "AC3")
                br = a.get("bitrate", "") or "N/A"
                if isinstance(br, (int, float)) or (isinstance(br, str) and br.isdigit()):
                    br = f"{int(br) // 1000} kb/s"

                flag_img = f'<img src="https://flagcdn.com/20x15/{flag}.png" alt="{flag}" width="20" height="15" style="display:inline" loading="lazy" referrerpolicy="no-referrer-when-downgrade">'
                audio_rows.append(
                    f'<tr>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{idx}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{flag_img} {lang}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{ch}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{fmt}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{br}</td>'
                    f'</tr>'
                )
        else:
            audio_rows.append(
                '<tr>'
                '<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">1</td>'
                '<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle"><img src="https://flagcdn.com/20x15/fr.png" alt="fr" width="20" height="15" style="display:inline"> Français</td>'
                '<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">2.0</td>'
                '<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">AC3</td>'
                '<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">N/A</td>'
                '</tr>'
            )
        audio_table_html = (
            '<table class="w-full border-collapse my-4">'
            '<tbody>'
            '<tr>'
            '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">#</th>'
            '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Langue</th>'
            '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Canaux</th>'
            '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Codec</th>'
            '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Bitrate</th>'
            '</tr>'
            + "".join(audio_rows)
            + '</tbody></table>'
        )

        # Subtitles
        subtitle_tracks = media_info.get("subtitle_tracks", [])
        if subtitle_tracks:
            sub_rows = []
            for idx, s in enumerate(subtitle_tracks, start=1):
                s_lang = s.get("language", "Français")
                s_flag = get_flag_code(s_lang)
                s_type = "Forcé" if s.get("forced") else "Complet"
                s_fmt = s.get("format", "UTF-8")
                flag_img = f'<img src="https://flagcdn.com/20x15/{s_flag}.png" alt="{s_flag}" width="20" height="15" style="display:inline" loading="lazy" referrerpolicy="no-referrer-when-downgrade">'
                sub_rows.append(
                    f'<tr>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{idx}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{flag_img} {s_lang}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{s_type}</td>'
                    f'<td class="border border-slate-300 dark:border-emerald-700 p-2 align-middle">{s_fmt}</td>'
                    f'</tr>'
                )
            subtitles_html = (
                '<table class="w-full border-collapse my-4">'
                '<tbody>'
                '<tr>'
                '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">#</th>'
                '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Langue</th>'
                '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Type</th>'
                '<th class="border border-slate-300 dark:border-emerald-700 p-2 bg-slate-100 dark:bg-emerald-900/50 font-semibold">Format</th>'
                '</tr>'
                + "".join(sub_rows)
                + '</tbody></table>'
            )
        else:
            subtitles_html = '<br>'

        # Source line
        source_display = source
        if vod_platform:
            source_display += f" ({vod_platform})"

        # Poster block
        poster_block = ""
        if poster:
            poster_block = f'<img src="{poster}" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer"><br>'

        year_header = f'<h2 id="year">({year_str})</h2>' if year_str else ''

        # Build full presentation HTML identical to C411 standard
        parts = [
            f'<h1>{display_title}</h1><p></p>{year_header}<p><br></p>',
            f'<div class="my-2">{poster_block}<img src="https://c411.org/images/banners/c411-informations.webp" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></div><br>',
            f'<strong>Pays :</strong> {country}<br>',
            f'<strong>Genres :</strong> {genres}<br>',
            f'<strong>Date de sortie :</strong> {release_date}<br>',
            f'<strong>Durée :</strong> {duration}<br>',
            f'<strong>Réalisateur(s) :</strong> {directors}<br>',
            f'<strong>Acteur(s) :</strong> {actors}<br>',
            f'<strong>Note TMDB :</strong> {vote_avg_display}<br>',
            f'<strong>IMDB :</strong> {imdb_link}<br><br>',
            f'<div class="my-2"><img src="https://c411.org/images/banners/c411-synopsis.webp" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></div><br>',
            f'{synop}<br>',
            f'<div class="my-2"><img src="https://c411.org/images/banners/c411-details-techniques.webp" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></div><br>',
            f'<strong>Source : </strong>{source_display}<br>',
            f'<strong>Résolution :</strong> {res}<br>',
            f'<strong>Codec Vidéo :</strong> {video_codec}<br>',
            f'<strong>Débit vidéo :</strong> {video_bitrate}<br>',
            f'<div class="my-2"><img src="https://c411.org/images/banners/c411-langues.webp" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></div><br>',
            f'{audio_table_html}<br>',
            f'<div class="my-2"><img src="https://c411.org/images/banners/c411-sous-titres.webp" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></div><br>',
            f'{subtitles_html}',
            f'<div class="my-2"><img src="https://c411.org/images/banners/c411-telechargement.webp" alt="" class="max-w-full rounded-lg inline align-middle" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></div><br>',
            f'<strong>Release :</strong> {release_title}<br>',
            f'<strong>Team :</strong> {tag}<br>',
            f'<strong>Nombre de fichier(s) :</strong> {file_count}<br>',
            f'<strong>Poids Total :</strong> {total_size_str}<br>',
            f'Bannières de prez par <a href="https://c411.org/user/djoontah" rel="noopener noreferrer" class="text-emerald-500 hover:text-emerald-400 underline" target="_blank">djoontah</a>'
        ]

        return "".join(parts)
