// Torrent Generator Frontend Application

let currentPath = "/data";
let currentAnalysis = null;
let currentGeneratedData = null;

// DOM Ready
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initExplorer();
    initScanner();
    initGenerator();
    initSettings();
    initHistory();
    checkServicesStatus();
});

// Toast Notifications
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    if (type === "error") icon = "fa-triangle-exclamation";
    
    toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Navigation Tabs
function initTabs() {
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            switchTab(tabId);
        });
    });

    // Subtabs for NFO & BBCode & Preview
    document.querySelectorAll(".subtab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".subtab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".subtab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            const subtabId = btn.getAttribute("data-subtab");
            const targetContent = document.getElementById(subtabId);
            if (targetContent) targetContent.classList.add("active");

            if (subtabId === "sub-bbcode-preview") {
                updateBbcodePreview();
            }
        });
    });

    // Refresh live preview button
    const refreshPreviewBtn = document.getElementById("btn-refresh-preview");
    if (refreshPreviewBtn) {
        refreshPreviewBtn.addEventListener("click", updateBbcodePreview);
    }

    // Copy editor content
    document.getElementById("btn-copy-active-editor").addEventListener("click", () => {
        const activeSubtab = document.querySelector(".subtab-content.active textarea");
        if (activeSubtab) {
            navigator.clipboard.writeText(activeSubtab.value);
            showToast("Texte copié dans le presse-papiers !", "success");
        } else if (document.getElementById("sub-bbcode-preview").classList.contains("active")) {
            navigator.clipboard.writeText(document.getElementById("editor-bbcode").value);
            showToast("BBCode copié dans le presse-papiers !", "success");
        }
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

    const targetNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    if (targetNav) targetNav.classList.add("active");

    const targetPane = document.getElementById(`pane-${tabId}`);
    if (targetPane) targetPane.classList.add("active");

    // Dynamic titles
    const titles = {
        explorer: ["Explorateur de Médias", "Parcourez vos disques du serveur et sélectionnez un média à uploader"],
        scanner: ["Analyse Globale & Doublons C411", "Scannez un dossier complet de votre serveur pour vérifier les doublons et préparer vos uploads"],
        generator: ["Générateur & Vérification", "Vérifiez les règles C411, générez NFO et Torrent puis uploadez"],
        history: ["Historique", "Consultez et téléchargez vos torrents précédemment générés"],
        settings: ["Paramètres", "Configurez vos accès C411, client torrent et les chemins de disques"]
    };
    if (titles[tabId]) {
        document.getElementById("page-title").textContent = titles[tabId][0];
        document.getElementById("page-subtitle").textContent = titles[tabId][1];
    }

    if (tabId === "history") loadHistory();
    if (tabId === "settings") loadSettings();
}

// File Explorer
function initExplorer() {
    loadDirectory(currentPath);

    document.getElementById("btn-refresh-explorer").addEventListener("click", () => {
        loadDirectory(currentPath);
    });

    document.getElementById("btn-go-path").addEventListener("click", () => {
        const p = document.getElementById("quick-path-input").value.trim();
        if (p) loadDirectory(p);
    });
}

async function loadDirectory(path) {
    const listBody = document.getElementById("explorer-list");
    listBody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-muted"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Chargement...</td></tr>`;

    try {
        const res = await fetch(`/api/browse?path=${encodeURIComponent(path)}`);
        if (!res.ok) throw new Error("Erreur lors de la lecture du dossier.");
        const data = await res.json();
        
        currentPath = data.current_path;
        document.getElementById("quick-path-input").value = currentPath;
        renderBreadcrumbs(currentPath);

        listBody.innerHTML = "";

        // If parent path available
        if (data.parent_path) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><a href="#" class="font-bold text-primary flex items-center gap-2" onclick="loadDirectory('${data.parent_path}'); return false;"><i class="fa-solid fa-folder-tree"></i> .. (Dossier parent)</a></td>
                <td>--</td>
                <td>--</td>
                <td style="text-align: right;"><button class="btn btn-outline btn-xs" onclick="loadDirectory('${data.parent_path}');">Ouvrir</button></td>
            `;
            listBody.appendChild(tr);
        }

        if (data.items.length === 0) {
            listBody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-muted">Ce dossier est vide.</td></tr>`;
            return;
        }

        data.items.forEach(item => {
            const tr = document.createElement("tr");
            const icon = item.is_dir ? "fa-folder text-warning" : getFileIcon(item.name);
            
            tr.innerHTML = `
                <td>
                    <div class="flex items-center gap-2">
                        <i class="fa-solid ${icon}"></i>
                        <span class="font-medium">${escapeHtml(item.name)}</span>
                    </div>
                </td>
                <td>${item.size}</td>
                <td>${item.modified}</td>
                <td style="text-align: right;">
                    <div class="flex justify-end gap-2">
                        ${item.is_dir ? `<button class="btn btn-outline btn-xs" onclick="loadDirectory('${item.path}');"><i class="fa-solid fa-folder-open"></i> Ouvrir</button>` : ''}
                        <button class="btn btn-primary btn-xs" onclick="selectAndAnalyze('${item.path}');">
                            <i class="fa-solid fa-wand-magic-sparkles mr-1"></i> Analyser
                        </button>
                    </div>
                </td>
            `;
            listBody.appendChild(tr);
        });

    } catch (e) {
        listBody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-danger"><i class="fa-solid fa-triangle-exclamation mr-2"></i> ${e.message}</td></tr>`;
    }
}

function renderBreadcrumbs(path) {
    const container = document.getElementById("explorer-breadcrumbs");
    const parts = path.split("/").filter(p => p.length > 0);
    
    let html = `<span class="breadcrumb-item cursor-pointer text-primary" onclick="loadDirectory('/data')"><i class="fa-solid fa-database"></i> /data</span>`;
    let accum = "";

    parts.forEach((p, idx) => {
        accum += "/" + p;
        if (accum !== "/data") {
            const currentAccum = accum;
            html += ` <i class="fa-solid fa-chevron-right text-xs text-muted"></i> <span class="breadcrumb-item cursor-pointer text-primary" onclick="loadDirectory('${currentAccum}')">${escapeHtml(p)}</span>`;
        }
    });

    container.innerHTML = html;
}

function getFileIcon(filename) {
    const ext = filename.split(".").pop().toLowerCase();
    if (["mkv", "mp4", "avi", "mov", "ts", "m2ts"].includes(ext)) return "fa-film text-primary";
    if (["mp3", "flac", "wav", "aac"].includes(ext)) return "fa-music text-success";
    if (["epub", "pdf", "cbz", "cbr"].includes(ext)) return "fa-book text-info";
    if (["iso", "img", "bin"].includes(ext)) return "fa-compact-disc text-warning";
    if (["exe", "dmg", "zip", "rar"].includes(ext)) return "fa-file-zipper text-muted";
    return "fa-file text-muted";
}

// Media Analysis & Generator
async function selectAndAnalyze(filePath, forcedMode = null) {
    showToast("Analyse du média en cours...", "info");
    switchTab("generator");

    document.getElementById("generator-empty").style.display = "none";
    document.getElementById("generator-content").style.display = "block";

    // Show loading placeholders
    document.getElementById("gen-source-filename").textContent = "Analyse en cours...";
    document.getElementById("gen-source-path").textContent = filePath;

    try {
        const res = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                path: filePath,
                release_mode: forcedMode || "auto"
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Erreur lors de l'analyse du média.");
        }
        const data = await res.json();
        currentAnalysis = data;
        currentAnalysis.source_path = filePath;

        // Reset generated buttons
        document.getElementById("btn-upload-c411").disabled = true;
        document.getElementById("btn-send-qbittorrent").disabled = true;
        document.getElementById("download-actions").style.display = "none";

        // Populate Overview Card
        const media = data.media_info || {};
        document.getElementById("gen-source-filename").textContent = media.file_name || filePath.split("/").pop();
        document.getElementById("gen-source-path").textContent = `Chemin: ${filePath}`;
        
        const sizeMb = (media.file_size || 0) / (1024 * 1024);
        document.getElementById("gen-stat-size").textContent = sizeMb >= 1024 ? `${(sizeMb / 1024).toFixed(2)} Go` : `${sizeMb.toFixed(2)} Mo`;
        document.getElementById("gen-stat-res").textContent = media.resolution || "N/A";
        document.getElementById("gen-stat-video").textContent = media.video_codec || "N/A";
        
        const firstAudio = media.audio_tracks && media.audio_tracks.length > 0 ? media.audio_tracks[0] : null;
        document.getElementById("gen-stat-audio").textContent = firstAudio ? `${firstAudio.language} (${firstAudio.format})` : "N/A";

        // Populate Namer & Anti-Detag
        const namer = data.namer || {};
        document.getElementById("input-release-title").value = namer.title || "";
        document.getElementById("input-year").value = namer.year || "";
        document.getElementById("input-lang-tag").value = namer.language || "";
        document.getElementById("select-source").value = namer.source || "WEB";
        document.getElementById("input-team-tag").value = namer.final_tag || "NOTAG";
        checkCoherenceWarning();

        const badgeTag = document.getElementById("badge-tag-status");
        if (namer.detected_tag) {
            badgeTag.textContent = `TAG D'ORIGINE : -${namer.detected_tag}`;
            badgeTag.className = "badge badge-success";
        } else {
            badgeTag.textContent = "AUCUN TAG : -NOTAG";
            badgeTag.className = "badge badge-warning";
        }
        if (namer.detag_warning) {
            document.getElementById("text-detag-explanation").textContent = namer.detag_warning;
        }

        // Populate Piece Size
        if (data.suggested_piece_size) {
            document.getElementById("select-piece-size").value = data.suggested_piece_size;
            document.getElementById("badge-piece-calc").textContent = `Recommandé C411 : ${data.suggested_piece_size / (1024 * 1024)} Mo`;
        }

        // Populate Category
        if (data.suggested_category_id) {
            document.getElementById("select-category").value = data.suggested_category_id;
        }

        // TMDB query prefill (clean movie / series title without parentheses or year)
        let baseNameGuess = (namer && namer.clean_title) ? namer.clean_title : "";
        if (!baseNameGuess) {
            baseNameGuess = (media.file_name || filePath.split("/").pop() || "")
                .replace(/[\(\[\{]\s*(?:19\d\d|20\d\d)\s*[\)\]\}].*$/, "")
                .replace(/\b(?:19\d\d|20\d\d)\b.*$/, "")
                .replace(/[\._\-]+/g, " ")
                .replace(/[^\w\s]/g, " ")
                .replace(/\s+/g, " ")
                .trim();
        }
        document.getElementById("tmdb-search-input").value = baseNameGuess;

        // Sub-items handling (Episodes in folder or Manga tomes)
        const subItemsCard = document.getElementById("sub-items-card");
        const subItemsList = document.getElementById("sub-items-list");
        if (media.sub_items && media.sub_items.length > 1) {
            document.getElementById("sub-items-count").textContent = media.sub_items.length;
            subItemsList.innerHTML = "";
            media.sub_items.forEach(si => {
                const tr = document.createElement("tr");
                const isItemBook = si.name.match(/\.(epub|pdf|cbz|cbr)$/i);
                const actionLabel = isItemBook ? "Tome seul" : "Épisode seul";
                const modeToUse = isItemBook ? "manga_tome" : "episode";
                tr.innerHTML = `
                    <td class="font-mono text-xs"><i class="fa-solid ${isItemBook ? 'fa-book text-info' : 'fa-file-video text-primary'} mr-1"></i> ${escapeHtml(si.name)}</td>
                    <td class="text-xs">${si.size}</td>
                    <td style="text-align: right;">
                        <button class="btn btn-outline btn-xs" onclick="selectAndAnalyze('${escapeJsString(si.path)}', '${modeToUse}');">
                            <i class="fa-solid fa-play mr-1"></i> ${actionLabel}
                        </button>
                    </td>
                `;
                subItemsList.appendChild(tr);
            });
            subItemsCard.style.display = "block";
        } else {
            subItemsCard.style.display = "none";
        }

        // Set mode from server or forced parameter
        const effectiveMode = (typeof forcedMode !== "undefined" && forcedMode) ? forcedMode : (data.suggested_release_mode || "single");
        document.getElementById("select-release-mode").value = effectiveMode;
        updateModeBadge(effectiveMode);

        // Populate Editors
        document.getElementById("editor-nfo").value = data.nfo || "";
        document.getElementById("editor-bbcode").value = data.bbcode || "";
        updateBbcodePreview();

        showToast("Média analysé avec succès selon les standards C411 !", "success");

        // Auto duplicate check with smart quality & tag comparison
        if (namer.title) {
            checkDuplicatesC411(namer.title);
        }

    } catch (e) {
        showToast(`Échec de l'analyse : ${e.message}`, "error");
    }
}

function updateModeBadge(mode) {
    const badge = document.getElementById("badge-pack-mode");
    const labels = {
        single: "FILM / UNIQUE",
        season_pack: "PACK SAISON",
        episode: "ÉPISODE SEUL",
        integrale: "INTÉGRALE",
        manga_tome: "TOME MANGA",
        manga_pack: "PACK MANGA"
    };
    if (badge) badge.textContent = labels[mode] || (mode ? mode.toUpperCase() : "MÉDIA");
}

function checkCoherenceWarning() {
    if (!currentAnalysis || !currentAnalysis.media_info) return;
    const titleInput = document.getElementById("input-release-title");
    const title = (titleInput ? titleInput.value : "").trim();
    const audioTracks = currentAnalysis.media_info.audio_tracks || [];
    const audioCount = audioTracks.length;
    const alertBox = document.getElementById("alert-coherence-warning");
    const textExpl = document.getElementById("text-coherence-explanation");
    const btnFix = document.getElementById("btn-fix-coherence");

    if (!alertBox) return;

    const hasMultiInTitle = /\bMULTI\b/i.test(title);

    if (hasMultiInTitle && audioCount < 2) {
        alertBox.style.display = "block";
        const trackLang = audioTracks[0] ? (audioTracks[0].language || "Français") : "Français";
        if (textExpl) {
            textExpl.innerHTML = `<strong>⚠️ Attention Règle C411 (Incohérence NFO) :</strong> Le titre contient <code>MULTI</code> mais le média ne déclare qu'une seule piste audio (${trackLang}). Le bot C411 bloque l'envoi dans ce cas. Le tag doit être <code>VFF</code> ou <code>TRUEFRENCH</code>.`;
        }
        if (btnFix) {
            btnFix.onclick = () => {
                let currentVal = titleInput.value;
                let fixed = currentVal.replace(/\.MULTI\./gi, ".").replace(/\.MULTI\b/gi, "").replace(/\bMULTI\./gi, "");
                titleInput.value = fixed;
                let langInput = document.getElementById("input-lang-tag");
                if (langInput) {
                    langInput.value = langInput.value.replace(/^MULTI\./i, "").replace(/^MULTI$/i, "VFF");
                }
                checkCoherenceWarning();
                if (typeof checkDuplicatesC411 === "function") checkDuplicatesC411(fixed);
                showToast("Titre corrigé selon les normes C411 (tag MULTI retiré) !", "success");
            };
        }
    } else {
        alertBox.style.display = "none";
    }
}

function recalculateTitle() {
    if (!currentAnalysis) return;
    const mode = document.getElementById("select-release-mode").value;
    const year = document.getElementById("input-year").value.trim();
    let lang = document.getElementById("input-lang-tag").value.trim();
    const source = document.getElementById("select-source").value;
    const tag = document.getElementById("input-team-tag").value.trim() || "NOTAG";

    // C411 Strict Rule: If < 2 audio tracks, MULTI is strictly forbidden
    const audioTracks = (currentAnalysis.media_info && currentAnalysis.media_info.audio_tracks) ? currentAnalysis.media_info.audio_tracks : [];
    if (audioTracks.length < 2 && lang) {
        if (/^MULTI\./i.test(lang)) {
            lang = lang.replace(/^MULTI\./i, "");
            document.getElementById("input-lang-tag").value = lang;
        } else if (/^MULTI$/i.test(lang)) {
            lang = "VFF";
            document.getElementById("input-lang-tag").value = lang;
        }
    }

    let raw = currentAnalysis.media_info.file_name;
    // Strip file extension
    raw = raw.replace(/\.[a-zA-Z0-9]+$/, "");

    // Clean title base: isolate movie/series title before year
    let titlePart = raw;
    if (year && raw.includes(year)) {
        titlePart = raw.split(new RegExp(`[\\(\\[\\{]?\\s*${year}\\b`, 'i'))[0];
    }
    titlePart = titlePart
        .replace(/[\(\[\{].*?[\)\]\}]/g, "")
        .replace(/\b(S\d{1,2}E\d{1,4}|S\d{1,2}|E\d{1,4}|Ep\d{1,4}|Episode[\s\.]*\d+|T\d{1,3}|Tome[\s\.]*\d+|INTEGRALE)\b/gi, "")
        .replace(/\b(2160p|1080p|720p|576p|480p|BluRay|BDRip|BRRip|WEB-DL|WEBDL|WEBRip|WEB|HDTV|DVDRip|REMUX|x264|x265|HEVC|AVC|AAC|AC3|EAC3|DTS|MULTI|VFF|VF2|VFQ|VFI|VOSTFR|TRUEFRENCH|FRENCH)\b.*$/gi, "")
        .replace(/[\s_\-]+/g, ".")
        .replace(/[^\w\.]/g, "")
        .replace(/\.+/g, ".")
        .trim(".");

    if (!titlePart) titlePart = "Release";

    const parts = [titlePart];

    // Detect existing tokens from raw filename
    const seMatch = raw.match(/\b(S\d{1,2}E\d{1,4})\b/i);
    const sMatch = raw.match(/\b(S\d{1,2})\b/i);
    const eMatch = raw.match(/\b(?:Episode|Ep|E)[\s\.]*(\d{1,4})\b/i);
    const tMatch = raw.match(/\b(?:Tome|Volume|Vol|T)[\s\.]*(\d{1,3})\b/i);
    const tRangeMatch = raw.match(/\b(T\d{1,3}[\-\.]T\d{1,3})\b/i);

    if (mode === "episode") {
        if (year) parts.push(year);
        if (seMatch) {
            parts.push(seMatch[1].toUpperCase());
        } else if (sMatch && eMatch) {
            parts.push(`${sMatch[1].toUpperCase()}E${parseInt(eMatch[1], 10).toString().padStart(2, '0')}`);
        } else if (eMatch) {
            parts.push(`E${parseInt(eMatch[1], 10).toString().padStart(2, '0')}`);
        } else {
            parts.push("S01E01");
        }
    } else if (mode === "season_pack") {
        parts.push(sMatch ? sMatch[1].toUpperCase() : "S01");
    } else if (mode === "integrale") {
        if (year) parts.push(year);
        parts.push("INTEGRALE");
    } else if (mode === "manga_tome") {
        parts.push(tMatch ? `T${parseInt(tMatch[1], 10).toString().padStart(2, '0')}` : "T01");
    } else if (mode === "manga_pack") {
        parts.push(tRangeMatch ? tRangeMatch[1].toUpperCase() : "INTEGRALE");
    } else if (mode === "single") {
        if (year) parts.push(year);
    }

    const isBook = (mode === "manga_tome" || mode === "manga_pack");
    if (isBook) {
        if (lang) parts.push(lang);
    } else {
        if (lang) parts.push(lang);
        if (currentAnalysis.media_info.resolution && currentAnalysis.media_info.resolution !== "Autre") parts.push(currentAnalysis.media_info.resolution);
        if (source) parts.push(source);
        if (currentAnalysis.media_info.hdr_tags && currentAnalysis.media_info.hdr_tags.length > 0) parts.push(currentAnalysis.media_info.hdr_tags.join("."));
        if (currentAnalysis.namer && currentAnalysis.namer.audio_spec) parts.push(currentAnalysis.namer.audio_spec);
        if (currentAnalysis.media_info.video_codec) parts.push(currentAnalysis.media_info.video_codec);
    }

    const newTitle = parts.join(".") + `-${tag}`;
    document.getElementById("input-release-title").value = newTitle;
    
    // Check coherence warning immediately
    checkCoherenceWarning();

    // Automatically re-run duplicate check on title change
    checkDuplicatesC411(newTitle);
}

function initGenerator() {
    // Recalculate title on button click
    document.getElementById("btn-recalc-title").addEventListener("click", () => {
        recalculateTitle();
        showToast("Titre réactualisé !", "info");
    });

    // Real-time C411 title and language coherence checks
    document.getElementById("input-release-title").addEventListener("input", checkCoherenceWarning);
    document.getElementById("input-lang-tag").addEventListener("input", checkCoherenceWarning);

    // Dynamic Mode Selector change (automatically updates title and category)
    document.getElementById("select-release-mode").addEventListener("change", (e) => {
        const mode = e.target.value;
        updateModeBadge(mode);

        const filePath = currentAnalysis ? (currentAnalysis.source_path || "").toLowerCase() : "";
        const isAnime = filePath.includes("manga") && !filePath.includes("ebook") && !filePath.includes("scan");

        if (mode === "season_pack" || mode === "episode" || mode === "integrale") {
            document.getElementById("select-category").value = isAnime ? "5070" : "5000";
        } else if (mode === "manga_tome" || mode === "manga_pack") {
            document.getElementById("select-category").value = "7030";
        } else if (mode === "single") {
            document.getElementById("select-category").value = isAnime ? "2060" : "2000";
        }

        recalculateTitle();
    });

    // Dynamic Category change (adapts mode and updates release title)
    document.getElementById("select-category").addEventListener("change", (e) => {
        const catId = e.target.value;
        if (catId.startsWith("7")) {
            // Ebooks / Manga
            const currentMode = document.getElementById("select-release-mode").value;
            if (currentMode !== "manga_tome" && currentMode !== "manga_pack") {
                document.getElementById("select-release-mode").value = "manga_tome";
                updateModeBadge("manga_tome");
            }
        } else if (catId.startsWith("5")) {
            // Séries TV / Animes
            const currentMode = document.getElementById("select-release-mode").value;
            if (currentMode === "single" || currentMode.startsWith("manga")) {
                document.getElementById("select-release-mode").value = "season_pack";
                updateModeBadge("season_pack");
            }
        } else if (catId.startsWith("2")) {
            // Films
            document.getElementById("select-release-mode").value = "single";
            updateModeBadge("single");
        }
        recalculateTitle();
    });

    // Check duplicate on C411 button
    document.getElementById("btn-check-c411").addEventListener("click", () => {
        const title = document.getElementById("input-release-title").value;
        if (title) checkDuplicatesC411(title);
    });

    // TMDB Search
    document.getElementById("btn-search-tmdb").addEventListener("click", searchTmdb);

    // 1. Generate Torrent & NFO
    document.getElementById("btn-generate-torrent").addEventListener("click", async () => {
        if (!currentAnalysis) return;
        const releaseName = document.getElementById("input-release-title").value.trim();
        if (!releaseName) {
            showToast("Veuillez renseigner un nom de release.", "error");
            return;
        }

        const audioTracks = (currentAnalysis && currentAnalysis.media_info && currentAnalysis.media_info.audio_tracks) ? currentAnalysis.media_info.audio_tracks : [];
        if (/\bMULTI\b/i.test(releaseName) && audioTracks.length < 2) {
            checkCoherenceWarning();
            showToast("Incohérence C411 : Le titre contient MULTI mais le média ne contient qu'une seule piste audio. C411 rejettera l'envoi !", "error");
            return;
        }

        const payload = {
            source_path: currentAnalysis.source_path,
            release_name: releaseName,
            release_mode: document.getElementById("select-release-mode").value,
            rename_on_disk: document.getElementById("chk-rename-on-disk") ? document.getElementById("chk-rename-on-disk").checked : false,
            category_id: parseInt(document.getElementById("select-category").value),
            piece_size: parseInt(document.getElementById("select-piece-size").value),
            nfo_content: document.getElementById("editor-nfo").value,
            bbcode_content: document.getElementById("editor-bbcode").value,
            source_type: document.getElementById("select-source").value,
            tag: document.getElementById("input-team-tag").value.trim() || "NOTAG",
            tmdb_id: document.getElementById("tmdb-id-val").value ? parseInt(document.getElementById("tmdb-id-val").value) : null,
            imdb_id: document.getElementById("imdb-id-val").value || null,
            poster_url: document.getElementById("poster-url-val").value || null
        };

        const btnGen = document.getElementById("btn-generate-torrent");
        btnGen.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Génération du torrent (hachage SHA-1)...`;
        btnGen.disabled = true;

        try {
            const res = await fetch("/api/generate-torrent", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Erreur lors de la génération.");
            }

            const data = await res.json();
            currentGeneratedData = data;
            currentGeneratedData.effective_source_path = data.effective_source_path || currentAnalysis.source_path;
            currentGeneratedData.release_name = releaseName;
            currentGeneratedData.category_id = payload.category_id;
            currentGeneratedData.bbcode = payload.bbcode_content;
            currentGeneratedData.nfo = payload.nfo_content;

            showToast(data.message, "success");

            // Enable next steps
            document.getElementById("btn-upload-c411").disabled = false;
            document.getElementById("btn-send-qbittorrent").disabled = false;

            // Setup download links
            document.getElementById("btn-dl-torrent").href = `/api/download?path=${encodeURIComponent(data.torrent_path)}`;
            document.getElementById("btn-dl-nfo").href = `/api/download?path=${encodeURIComponent(data.nfo_path)}`;
            document.getElementById("download-actions").style.display = "flex";

        } catch (e) {
            showToast(e.message, "error");
        } finally {
            btnGen.innerHTML = `<i class="fa-solid fa-file-circle-plus mr-2"></i> 1. Créer le Torrent & NFO`;
            btnGen.disabled = false;
        }
    });

    // 2. Upload to C411
    document.getElementById("btn-upload-c411").addEventListener("click", async () => {
        if (!currentGeneratedData) return;

        const audioTracks = (currentAnalysis && currentAnalysis.media_info && currentAnalysis.media_info.audio_tracks) ? currentAnalysis.media_info.audio_tracks : [];
        if (/\bMULTI\b/i.test(currentGeneratedData.release_name) && audioTracks.length < 2) {
            checkCoherenceWarning();
            showToast("Incohérence C411 : Le titre contient MULTI mais le média ne contient qu'une seule piste audio. C411 rejettera l'upload !", "error");
            return;
        }

        const btnUpload = document.getElementById("btn-upload-c411");
        btnUpload.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Upload vers C411...`;
        btnUpload.disabled = true;

        const payload = {
            torrent_path: currentGeneratedData.torrent_path,
            nfo_path: currentGeneratedData.nfo_path,
            name: currentGeneratedData.release_name,
            category_id: currentGeneratedData.category_id,
            description: currentGeneratedData.bbcode,
            mediainfo_text: currentGeneratedData.nfo,
            tmdb_id: document.getElementById("tmdb-id-val").value ? parseInt(document.getElementById("tmdb-id-val").value) : null,
            imdb_id: document.getElementById("imdb-id-val").value || null,
            anonymous: false
        };

        try {
            const res = await fetch("/api/upload-c411", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const result = await res.json();
            if (result.success) {
                showToast(result.message, "success");
            } else {
                showToast(result.message, "error");
                if (result.web_upload_url) {
                    if (audioTracks.length < 2) {
                        showToast("💡 Sur la page C411 : Sélectionnez Langue = 'Français' (ne cochez pas Multi car 1 seule piste audio)", "info");
                    }
                    window.open(result.web_upload_url, "_blank");
                }
            }
        } catch (e) {
            showToast(`Erreur d'upload : ${e.message}`, "error");
        } finally {
            btnUpload.innerHTML = `<i class="fa-solid fa-cloud-arrow-up mr-2"></i> 2. Uploader sur C411`;
            btnUpload.disabled = false;
        }
    });

    // 3. Send to qBittorrent
    document.getElementById("btn-send-qbittorrent").addEventListener("click", async () => {
        if (!currentGeneratedData) return;

        const btnQb = document.getElementById("btn-send-qbittorrent");
        btnQb.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Injection qBittorrent...`;
        btnQb.disabled = true;

        const payload = {
            torrent_path: currentGeneratedData.torrent_path,
            source_path: currentGeneratedData.effective_source_path || currentAnalysis.source_path,
            info_hash: currentGeneratedData.info_hash
        };

        try {
            const res = await fetch("/api/add-qbittorrent", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const result = await res.json();
            if (result.success) {
                showToast(result.message, "success");
            } else {
                showToast(result.message, "error");
            }
        } catch (e) {
            showToast(`Erreur qBittorrent : ${e.message}`, "error");
        } finally {
            btnQb.innerHTML = `<i class="fa-solid fa-seedling mr-2"></i> 3. Envoyer à qBittorrent`;
            btnQb.disabled = false;
        }
    });
}

// C411 Deep Duplicate Check (Quality, Source & Tag)
async function checkDuplicatesC411(releaseTitle) {
    const resBox = document.getElementById("duplicate-results");
    resBox.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Analyse approfondie des doublons sur C411 (qualité, source, team)...`;

    const resolution = currentAnalysis ? currentAnalysis.media_info.resolution : "";
    const source = document.getElementById("select-source").value;
    const tag = document.getElementById("input-team-tag").value.trim();
    const categoryId = document.getElementById("select-category").value;

    try {
        const res = await fetch("/api/check-duplicates", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: releaseTitle,
                resolution: resolution,
                source: source,
                tag: tag,
                category_id: categoryId
            })
        });
        const data = await res.json();

        let badgeClass = "badge-success";
        let icon = "fa-circle-check";
        if (data.level === "danger") {
            badgeClass = "badge-danger";
            icon = "fa-circle-xmark";
        } else if (data.level === "warning") {
            badgeClass = "badge-warning";
            icon = "fa-triangle-exclamation";
        }

        let html = `
            <div class="mb-2 flex items-center justify-between">
                <span class="badge ${badgeClass}"><i class="fa-solid ${icon} mr-1"></i> ${data.badge}</span>
                <span class="text-xs text-muted">${data.total_found} torrent(s) trouvés</span>
            </div>
            <p class="text-xs mb-2 font-medium">${escapeHtml(data.status_text)}</p>
        `;

        // 1. Same team duplicate (Red prominent box)
        if (data.same_tag_duplicates && data.same_tag_duplicates.length > 0) {
            html += `
                <div class="p-2 mb-2 rounded border border-danger" style="background-color: rgba(220, 53, 69, 0.18);">
                    <div class="font-bold text-xs text-danger mb-1 flex items-center">
                        <i class="fa-solid fa-ban mr-1"></i> DOUBLON DE VOTRE TEAM DÉTECTÉ (-${escapeHtml(data.matched_tag || tag)}) :
                    </div>
                    <ul class="text-xs mb-1" style="max-height: 120px; overflow-y: auto;">
            `;
            data.same_tag_duplicates.forEach(item => {
                html += `
                    <li class="py-1 flex justify-between items-center text-danger border-b border-dark">
                        <span class="truncate mr-2 font-mono font-bold" style="max-width: 260px;" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
                        <span class="badge badge-danger"><strong>${item.seeders}S</strong> / ${item.size}</span>
                    </li>
                `;
            });
            html += `
                    </ul>
                    <div class="text-xs text-danger mt-1">⚠️ <strong>Refus certain</strong> : cette version existe déjà avec votre signature de team.</div>
                </div>
            `;
        }

        // 2. Same quality/format by another team
        if (data.same_quality_duplicates && data.same_quality_duplicates.length > 0) {
            html += `
                <div class="text-warning font-bold text-xs mb-1"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Même résolution / format (autres teams) :</div>
                <ul class="text-xs mb-2" style="max-height: 90px; overflow-y: auto;">
            `;
            data.same_quality_duplicates.forEach(item => {
                html += `
                    <li class="py-1 border-b border-dark flex justify-between items-center text-warning">
                        <span class="truncate mr-2" style="max-width: 250px;" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
                        <span><strong>${item.seeders}S</strong> / ${item.size}</span>
                    </li>
                `;
            });
            html += `</ul>`;
        }

        // 3. Other qualities/versions
        if (data.other_versions && data.other_versions.length > 0) {
            html += `
                <div class="text-muted text-xs mb-1"><i class="fa-solid fa-folder-open mr-1"></i> Autres versions sur C411 (qualités différentes autorisées) :</div>
                <ul class="text-xs" style="max-height: 80px; overflow-y: auto;">
            `;
            data.other_versions.slice(0, 4).forEach(item => {
                html += `
                    <li class="py-1 border-b border-dark flex justify-between items-center text-muted">
                        <span class="truncate mr-2" style="max-width: 250px;" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
                        <span>${item.seeders}S / ${item.size}</span>
                    </li>
                `;
            });
            html += `</ul>`;
        }

        resBox.innerHTML = html;

    } catch (e) {
        resBox.innerHTML = `<span class="text-muted"><i class="fa-solid fa-circle-exclamation mr-1"></i> Vérification non disponible (Vérifiez la clé API C411 dans Paramètres).</span>`;
    }
}

// TMDB Search & Selection (Supports Title, direct TMDB URL, or IMDb ID)
async function searchTmdb() {
    const q = document.getElementById("tmdb-search-input").value.trim();
    if (!q) return;

    const badge = document.getElementById("tmdb-status-badge");
    const container = document.getElementById("tmdb-results-container");
    const list = document.getElementById("tmdb-cards-list");

    const isDirect = q.match(/themoviedb\.org\/(movie|tv)\/\d+/i) || q.match(/^tt\d{7,8}$/i) || q.match(/^\d+$/);
    if (isDirect) {
        if (badge) badge.textContent = "Résolution directe...";
        list.innerHTML = `<div class="text-muted"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Récupération directe de la fiche TMDB / IMDb...</div>`;
    } else {
        if (badge) badge.textContent = "Recherche titre...";
        list.innerHTML = `<div class="text-muted"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Recherche TMDB en cours...</div>`;
    }
    container.style.display = "block";

    try {
        const res = await fetch("/api/tmdb-search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: q })
        });
        const data = await res.json();

        if (!data.results || data.results.length === 0) {
            list.innerHTML = `<div class="text-muted">Aucun résultat trouvé sur TMDB pour "${escapeHtml(q)}".</div>`;
            if (badge) badge.textContent = "Aucun résultat";
            return;
        }

        if (data.direct_match && data.results && data.results.length === 1) {
            applyTmdbMetadata(data.results[0]);
            showToast(`Fiche TMDB trouvée et appliquée : "${data.results[0].title}" !`, "success");
            return;
        }

        if (badge) badge.textContent = `${data.results.length} résultat(s)`;
        list.innerHTML = "";
        data.results.forEach(item => {
            const card = document.createElement("div");
            card.className = "tmdb-card";
            card.innerHTML = `
                <img src="${item.poster_url || 'https://via.placeholder.com/60x90?text=No+Cover'}" alt="Poster">
                <div class="tmdb-card-info">
                    <h5>${escapeHtml(item.title)} (${item.year || 'N/A'})</h5>
                    <p>${escapeHtml(item.synopsis || 'Pas de synopsis disponible.')}</p>
                </div>
            `;
            card.addEventListener("click", () => applyTmdbMetadata(item));
            list.appendChild(card);
        });

    } catch (e) {
        list.innerHTML = `<div class="text-danger">Erreur : ${e.message}</div>`;
        if (badge) badge.textContent = "Erreur TMDB";
    }
}

async function applyTmdbMetadata(item) {
    let fullItem = item;
    // If rich fields like directors/genres_str are missing, fetch full details from API
    if (!item.directors && item.id) {
        try {
            const mType = item.media_type || "movie";
            const res = await fetch("/api/tmdb-details", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ tmdb_id: item.id, media_type: mType })
            });
            if (res.ok) {
                fullItem = await res.json();
            }
        } catch (e) {
            console.error("Error fetching full tmdb details:", e);
        }
    }

    document.getElementById("tmdb-id-val").value = fullItem.id || "";
    document.getElementById("imdb-id-val").value = fullItem.imdb_id || "";
    document.getElementById("poster-url-val").value = fullItem.poster_url || "";
    document.getElementById("tmdb-results-container").style.display = "none";

    const badge = document.getElementById("tmdb-status-badge");
    if (badge) badge.textContent = `Fiche : ${fullItem.title} (${fullItem.year || 'N/A'})`;

    if (fullItem.year && !document.getElementById("input-year").value) {
        document.getElementById("input-year").value = fullItem.year;
        recalculateTitle();
    }

    // Regenerate C411 presentation description
    if (currentAnalysis) {
        const releaseTitle = document.getElementById("input-release-title").value;
        const source = document.getElementById("select-source").value;
        const tag = document.getElementById("input-team-tag").value.trim() || "NOTAG";
        const fileCount = currentAnalysis.media_info.sub_items && currentAnalysis.media_info.sub_items.length > 0 
            ? currentAnalysis.media_info.sub_items.length 
            : 1;

        try {
            const genRes = await fetch("/api/generate-description", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    release_title: releaseTitle,
                    media_info: currentAnalysis.media_info,
                    source: source,
                    tag: tag,
                    tmdb_data: fullItem,
                    file_count: fileCount
                })
            });
            if (genRes.ok) {
                const genData = await genRes.json();
                document.getElementById("editor-bbcode").value = genData.description;
                updateBbcodePreview();
            }
        } catch (e) {
            console.error("Error generating C411 description:", e);
        }
    }

    showToast(`Métadonnées appliquées : "${fullItem.title}" (${fullItem.year || 'N/A'})`, "success");
}

// ==========================================
// Analyse Globale / Mass Directory Scanner
// ==========================================
let scannerResults = [];
let currentScannerFilter = "all";

function initScanner() {
    // Quick path chips
    document.querySelectorAll(".btn-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const folder = chip.getAttribute("data-folder");
            const mode = chip.getAttribute("data-mode");
            if (folder) document.getElementById("scanner-folder-input").value = folder;
            if (mode) document.getElementById("scanner-mode-select").value = mode;
        });
    });

    // Start Scan Button
    const btnScan = document.getElementById("btn-start-mass-scan");
    if (btnScan) {
        btnScan.addEventListener("click", runMassScan);
    }

    // Filter Buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const filter = btn.getAttribute("data-filter");
            applyScannerFilter(filter);
        });
    });

    // KPI Cards as Filter Shortcuts
    document.querySelectorAll(".filter-kpi-card").forEach(card => {
        card.addEventListener("click", () => {
            const filter = card.getAttribute("data-filter");
            applyScannerFilter(filter);
        });
    });
}

async function runMassScan() {
    const folderInput = document.getElementById("scanner-folder-input").value.trim();
    const modeSelect = document.getElementById("scanner-mode-select").value;
    const btnScan = document.getElementById("btn-start-mass-scan");

    if (!folderInput) {
        showToast("Veuillez indiquer un chemin de dossier.", "error");
        return;
    }

    btnScan.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Analyse en cours...`;
    btnScan.disabled = true;

    try {
        const limitVal = parseInt(document.getElementById("scanner-limit-select")?.value || "500", 10);
        const res = await fetch("/api/mass-scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                folder_path: folderInput,
                mode: modeSelect,
                limit: limitVal,
                check_c411: true
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Erreur lors du scan du dossier.");
        }

        const data = await res.json();
        scannerResults = data.results || data.items || [];

        // Update KPIs
        const total = scannerResults.length;
        const uploadable = scannerResults.filter(i => i.status_code === "green").length;
        const warning = scannerResults.filter(i => i.status_code === "yellow").length;
        const danger = scannerResults.filter(i => i.status_code === "red").length;

        document.getElementById("kpi-total").textContent = total;
        document.getElementById("kpi-uploadable").textContent = uploadable;
        document.getElementById("kpi-warning").textContent = warning;
        document.getElementById("kpi-danger").textContent = danger;

        document.getElementById("scanner-kpis").style.display = "grid";
        document.getElementById("scanner-results-card").style.display = "block";
        document.getElementById("scanner-empty-state").style.display = "none";

        const now = new Date();
        document.getElementById("scanner-scan-time").textContent = `Dernier scan : ${now.toLocaleTimeString()}`;

        currentScannerFilter = "all";
        applyScannerFilter("all");

        showToast(`Scan terminé : ${total} élément(s) analysé(s) !`, "success");

    } catch (e) {
        showToast(`Échec du scan : ${e.message}`, "error");
    } finally {
        btnScan.innerHTML = `<i class="fa-solid fa-magnifying-glass-chart mr-2"></i> Lancer l'Analyse Globale`;
        btnScan.disabled = false;
    }
}

function applyScannerFilter(filter) {
    currentScannerFilter = filter;

    document.querySelectorAll(".filter-btn").forEach(b => {
        if (b.getAttribute("data-filter") === filter) {
            b.classList.add("active");
        } else {
            b.classList.remove("active");
        }
    });

    renderScannerTable();
}

function renderScannerTable() {
    const tbody = document.getElementById("scanner-table-body");
    tbody.innerHTML = "";

    let filtered = scannerResults;
    if (currentScannerFilter === "uploadable") {
        filtered = scannerResults.filter(i => i.status_code === "green");
    } else if (currentScannerFilter === "different_quality") {
        filtered = scannerResults.filter(i => i.status_code === "yellow");
    } else if (currentScannerFilter === "duplicate") {
        filtered = scannerResults.filter(i => i.status_code === "red");
    }

    document.getElementById("scanner-filtered-count").textContent = filtered.length;

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-muted">Aucun résultat pour ce filtre.</td></tr>`;
        return;
    }

    filtered.forEach(item => {
        const tr = document.createElement("tr");

        const isDir = item.is_dir;
        const icon = isDir ? "fa-folder text-warning" : getFileIcon(item.name);

        // Mode badge
        const modeLabels = {
            single: "Film",
            season_pack: "Saison Pack",
            episode: "Épisode",
            integrale: "Intégrale",
            manga_tome: "Tome Manga",
            manga_pack: "Pack Manga"
        };
        const modeLabel = modeLabels[item.suggested_mode] || item.suggested_mode || "Média";

        // Status badge
        let statusBadge = "";
        if (item.status_code === "green") {
            statusBadge = `
                <div class="flex items-center gap-1 mb-1">
                    <span class="badge badge-success"><i class="fa-solid fa-circle-check mr-1"></i> Prêt pour Upload</span>
                </div>
                <small class="text-muted block text-xs">Aucun doublon trouvé sur C411</small>
            `;
        } else if (item.status_code === "red") {
            let dupDetails = "";
            if (item.duplicates_info && item.duplicates_info.same_tag_duplicates && item.duplicates_info.same_tag_duplicates.length > 0) {
                const d = item.duplicates_info.same_tag_duplicates[0];
                dupDetails = `<small class="text-danger block text-xs truncate" style="max-width: 260px;" title="${escapeHtml(d.title)}">Existant: ${escapeHtml(d.title)} (${d.size})</small>`;
            }
            statusBadge = `
                <div class="flex items-center gap-1 mb-1">
                    <span class="badge badge-danger font-bold"><i class="fa-solid fa-ban mr-1"></i> Doublon Strict (-${escapeHtml(item.tag)})</span>
                </div>
                ${dupDetails}
            `;
        } else if (item.status_code === "yellow") {
            let dupDetails = "";
            if (item.duplicates_info && item.duplicates_info.same_quality_duplicates && item.duplicates_info.same_quality_duplicates.length > 0) {
                const d = item.duplicates_info.same_quality_duplicates[0];
                dupDetails = `<small class="text-warning block text-xs truncate" style="max-width: 260px;" title="${escapeHtml(d.title)}">Autre team: ${escapeHtml(d.title)}</small>`;
            }
            statusBadge = `
                <div class="flex items-center gap-1 mb-1">
                    <span class="badge badge-warning"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Autre Qualité / Team</span>
                </div>
                ${dupDetails}
            `;
        } else {
            statusBadge = `<span class="badge badge-secondary">Non vérifié</span>`;
        }

        const safePath = escapeJsString(item.path);
        const safeMode = item.suggested_mode || "single";

        tr.innerHTML = `
            <td>
                <div class="flex items-center gap-2">
                    <i class="fa-solid ${icon}"></i>
                    <div>
                        <strong class="font-mono text-xs block text-primary" title="${escapeHtml(item.clean_title || item.name)}">${escapeHtml(item.clean_title || item.name)}</strong>
                        <small class="text-muted block font-mono" style="font-size: 0.7rem;">${escapeHtml(item.name)}</small>
                    </div>
                </div>
            </td>
            <td class="font-mono text-xs font-semibold">${item.size}</td>
            <td><span class="badge badge-info">${modeLabel}</span></td>
            <td><span class="badge badge-primary font-mono">-${escapeHtml(item.tag)}</span></td>
            <td>${statusBadge}</td>
            <td style="text-align: right;">
                <button class="btn btn-primary btn-xs" onclick="loadFromScanner('${safePath}', '${safeMode}');">
                    <i class="fa-solid fa-bolt mr-1"></i> Traiter
                </button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

function loadFromScanner(path, mode) {
    switchTab("generator");
    selectAndAnalyze(path, mode);
    showToast("Média chargé dans le Générateur !", "info");
}

function escapeJsString(str) {
    if (!str) return "";
    return str.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

// ==========================================
// BBCode Live HTML Preview Generator
// ==========================================
function renderBbcodeToHtml(bbcode) {
    if (!bbcode) return "<div class='text-muted text-center py-6'>Aucune description à afficher.</div>";

    // If the content is already HTML (C411 standard HTML presentation)
    const hasHtmlTags = /<\s*(?:div|table|p|strong|h[1-6]|img|br|span|a|tbody|tr|td|th)\b/i.test(bbcode);
    if (hasHtmlTags) {
        return bbcode;
    }

    let html = escapeHtml(bbcode);

    // [center]...[/center]
    html = html.replace(/\[center\]([\s\S]*?)\[\/center\]/gi, '<div style="text-align: center;">$1</div>');

    // [b], [i], [u], [s]
    html = html.replace(/\[b\]([\s\S]*?)\[\/b\]/gi, '<strong>$1</strong>');
    html = html.replace(/\[i\]([\s\S]*?)\[\/i\]/gi, '<em>$1</em>');
    html = html.replace(/\[u\]([\s\S]*?)\[\/u\]/gi, '<u>$1</u>');
    html = html.replace(/\[s\]([\s\S]*?)\[\/s\]/gi, '<s>$1</s>');

    // [size=N]...[/size]
    html = html.replace(/\[size=([1-7])\]([\s\S]*?)\[\/size\]/gi, (match, size, content) => {
        const sizes = { "1": "0.75rem", "2": "0.85rem", "3": "1rem", "4": "1.2rem", "5": "1.45rem", "6": "1.8rem", "7": "2.2rem" };
        const s = sizes[size] || "1rem";
        return `<span style="font-size: ${s}; line-height: 1.3;">${content}</span>`;
    });

    // [color=HEX or NAME]...[/color]
    html = html.replace(/\[color=([#a-zA-Z0-9]+)\]([\s\S]*?)\[\/color\]/gi, '<span style="color: $1;">$2</span>');

    // [font=monospace]...[/font]
    html = html.replace(/\[font=monospace\]([\s\S]*?)\[\/font\]/gi, '<span style="font-family: var(--font-mono); font-size: 0.82rem;">$1</span>');

    // [img]URL[/img]
    html = html.replace(/\[img\](https?:\/\/[^\s<]+)\[\/img\]/gi, '<img src="$1" style="max-width: 100%; max-height: 380px; border-radius: 8px; margin: 0.75rem auto; display: block; box-shadow: 0 4px 15px rgba(0,0,0,0.5);" alt="Poster">');

    // [url=URL]text[/url] & [url]URL[/url]
    html = html.replace(/\[url=(https?:\/\/[^\s<]+)\]([\s\S]*?)\[\/url\]/gi, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">$2</a>');
    html = html.replace(/\[url\](https?:\/\/[^\s<]+)\[\/url\]/gi, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: underline;">$1</a>');

    // [quote]...[/quote]
    html = html.replace(/\[quote\]([\s\S]*?)\[\/quote\]/gi, '<blockquote class="bbcode-quote">$1</blockquote>');

    // [spoiler=TITLE]...[/spoiler] or [spoiler]...[/spoiler]
    html = html.replace(/\[spoiler=([^\]]+)\]([\s\S]*?)\[\/spoiler\]/gi, '<details class="bbcode-spoiler" open><summary><i class="fa-solid fa-chevron-right mr-1"></i> $1</summary><pre class="bbcode-pre">$2</pre></details>');
    html = html.replace(/\[spoiler\]([\s\S]*?)\[\/spoiler\]/gi, '<details class="bbcode-spoiler" open><summary><i class="fa-solid fa-chevron-right mr-1"></i> Détails techniques</summary><pre class="bbcode-pre">$1</pre></details>');

    // [hr]
    html = html.replace(/\[hr\]/gi, '<hr class="bbcode-hr">');

    // Split pre blocks to avoid double br
    const parts = html.split(/(<pre[\s\S]*?<\/pre>)/gi);
    html = parts.map(part => {
        if (part.startsWith("<pre")) return part;
        return part.replace(/\r?\n/g, "<br>");
    }).join("");

    return html;
}

function updateBbcodePreview() {
    const raw = document.getElementById("editor-bbcode").value;
    const previewBox = document.getElementById("bbcode-rendered-preview");
    if (previewBox) {
        previewBox.innerHTML = renderBbcodeToHtml(raw);
    }
}

// History
async function initHistory() {
    document.getElementById("btn-refresh-history").addEventListener("click", loadHistory);
}

async function loadHistory() {
    const list = document.getElementById("history-list");
    try {
        const res = await fetch("/api/history");
        const items = await res.json();

        if (items.length === 0) {
            list.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-muted">Aucun torrent généré pour le moment.</td></tr>`;
            return;
        }

        list.innerHTML = "";
        items.forEach(item => {
            const sizeMb = item.size_bytes / (1024 * 1024);
            const sizeStr = sizeMb >= 1024 ? `${(sizeMb / 1024).toFixed(2)} Go` : `${sizeMb.toFixed(2)} Mo`;

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><small class="text-muted">${item.created_at}</small></td>
                <td><strong class="font-mono text-sm">${escapeHtml(item.name)}</strong></td>
                <td>${sizeStr}</td>
                <td><span class="badge badge-info">${item.status_c411}</span></td>
                <td><span class="badge badge-secondary">${item.status_qbittorrent}</span></td>
                <td style="text-align: right;">
                    <a href="/api/download?path=${encodeURIComponent(item.torrent_path)}" class="btn btn-outline btn-xs mr-1"><i class="fa-solid fa-download"></i> .torrent</a>
                    <a href="/api/download?path=${encodeURIComponent(item.nfo_path)}" class="btn btn-outline btn-xs"><i class="fa-solid fa-file-lines"></i> .nfo</a>
                </td>
            `;
            list.appendChild(tr);
        });
    } catch (e) {
        list.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-danger">Erreur de chargement.</td></tr>`;
    }
}

// Settings
async function initSettings() {
    document.getElementById("btn-save-settings").addEventListener("click", saveSettings);
    document.getElementById("btn-test-c411").addEventListener("click", testC411);
    document.getElementById("btn-test-qb").addEventListener("click", testQBittorrent);
}

async function loadSettings() {
    try {
        const res = await fetch("/api/config");
        const cfg = await res.json();

        document.getElementById("cfg-c411-passkey").value = cfg.c411_passkey || "";
        document.getElementById("cfg-c411-apikey").value = cfg.c411_api_key || "";
        document.getElementById("cfg-c411-baseurl").value = cfg.c411_base_url || "https://c411.org";
        document.getElementById("cfg-c411-announce-primary").value = cfg.c411_announce_primary || "https://c411.org/announce/";
        document.getElementById("cfg-c411-announce-backup").value = cfg.c411_announce_backup || "https://tk.c411.tw/announce/";
        document.getElementById("cfg-c411-default-tag").value = cfg.c411_default_tag || "NOTAG";

        document.getElementById("cfg-qb-url").value = cfg.qbittorrent_url || "";
        document.getElementById("cfg-qb-user").value = cfg.qbittorrent_username || "admin";
        document.getElementById("cfg-qb-pass").value = cfg.qbittorrent_password || "";
        document.getElementById("cfg-qb-map-from").value = cfg.qbittorrent_path_mapping_from || "/data";
        document.getElementById("cfg-qb-map-to").value = cfg.qbittorrent_path_mapping_to || "";
        document.getElementById("cfg-qb-category").value = cfg.qbittorrent_category || "c411";
        document.getElementById("cfg-qb-tags").value = cfg.qbittorrent_tags || "c411,upload";

        document.getElementById("cfg-tmdb-key").value = cfg.tmdb_api_key || "";
    } catch (e) {
        showToast("Impossible de charger les paramètres.", "error");
    }
}

async function saveSettings() {
    const payload = {
        web_port: 30017,
        data_dir: "/data",
        output_dir: "/output",
        c411_passkey: document.getElementById("cfg-c411-passkey").value.trim(),
        c411_api_key: document.getElementById("cfg-c411-apikey").value.trim(),
        c411_base_url: document.getElementById("cfg-c411-baseurl").value.trim(),
        c411_announce_primary: document.getElementById("cfg-c411-announce-primary").value.trim(),
        c411_announce_backup: document.getElementById("cfg-c411-announce-backup").value.trim(),
        c411_default_tag: document.getElementById("cfg-c411-default-tag").value.trim() || "NOTAG",
        c411_anonymous: false,

        qbittorrent_enabled: true,
        qbittorrent_url: document.getElementById("cfg-qb-url").value.trim(),
        qbittorrent_username: document.getElementById("cfg-qb-user").value.trim(),
        qbittorrent_password: document.getElementById("cfg-qb-pass").value,
        qbittorrent_category: document.getElementById("cfg-qb-category").value.trim(),
        qbittorrent_tags: document.getElementById("cfg-qb-tags").value.trim(),
        qbittorrent_path_mapping_from: document.getElementById("cfg-qb-map-from").value.trim(),
        qbittorrent_path_mapping_to: document.getElementById("cfg-qb-map-to").value.trim(),
        qbittorrent_start_paused: false,

        tmdb_api_key: document.getElementById("cfg-tmdb-key").value.trim()
    };

    try {
        const res = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            showToast(data.message, "success");
            checkServicesStatus();
        } else {
            showToast("Erreur lors de la sauvegarde.", "error");
        }
    } catch (e) {
        showToast(`Erreur : ${e.message}`, "error");
    }
}

async function testC411() {
    showToast("Test de l'API C411...", "info");
    try {
        const res = await fetch("/api/test-c411", { method: "POST" });
        const data = await res.json();
        showToast(data.message, data.success ? "success" : "error");
        updateC411Indicator(data.success);
    } catch (e) {
        showToast("Impossible de contacter C411.", "error");
        updateC411Indicator(false);
    }
}

async function testQBittorrent() {
    showToast("Test de qBittorrent...", "info");
    try {
        const res = await fetch("/api/test-qbittorrent", { method: "POST" });
        const data = await res.json();
        showToast(data.message, data.success ? "success" : "error");
        updateQbIndicator(data.success);
    } catch (e) {
        showToast("Impossible de contacter qBittorrent.", "error");
        updateQbIndicator(false);
    }
}

async function checkServicesStatus() {
    try {
        const res = await fetch("/api/config");
        const cfg = await res.json();

        // Check C411
        if (cfg.c411_passkey) {
            document.getElementById("c411-status-text").textContent = "Passkey prête";
            updateC411Indicator(true);
        } else {
            document.getElementById("c411-status-text").textContent = "Passkey requise";
            updateC411Indicator(false);
        }

        // Test QB
        const qbRes = await fetch("/api/test-qbittorrent", { method: "POST" });
        const qbData = await qbRes.json();
        updateQbIndicator(qbData.success);
        document.getElementById("qb-status-text").textContent = qbData.success ? `En ligne (${qbData.version || 'v5'})` : "Déconnecté";
    } catch (e) {
        // silent
    }
}

function updateC411Indicator(isOnline) {
    const ind = document.getElementById("c411-indicator");
    ind.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
}

function updateQbIndicator(isOnline) {
    const ind = document.getElementById("qb-indicator");
    ind.className = `status-indicator ${isOnline ? 'online' : 'offline'}`;
}

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
