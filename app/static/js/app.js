// Torrent Generator Frontend Application

let currentPath = "/data";
let currentAnalysis = null;
let currentGeneratedData = null;

// DOM Ready
document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initExplorer();
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

    // Subtabs for NFO & BBCode
    document.querySelectorAll(".subtab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".subtab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".subtab-content").forEach(c => c.classList.remove("active"));
            
            btn.classList.add("active");
            const subtabId = btn.getAttribute("data-subtab");
            document.getElementById(subtabId).classList.add("active");
        });
    });

    // Copy editor content
    document.getElementById("btn-copy-active-editor").addEventListener("click", () => {
        const activeSubtab = document.querySelector(".subtab-content.active textarea");
        if (activeSubtab) {
            navigator.clipboard.writeText(activeSubtab.value);
            showToast("Texte copié dans le presse-papiers !", "success");
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
        explorer: ["Explorateur de Médias", "Parcourez vos disques NAS et sélectionnez un média à uploader"],
        generator: ["Générateur & Vérification", "Vérifiez les règles C411, générez NFO et Torrent puis uploadez"],
        history: ["Historique", "Consultez et téléchargez vos torrents précédemment générés"],
        settings: ["Paramètres", "Configurez vos accès C411, qBittorrent et les chemins de disques"]
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
async function selectAndAnalyze(filePath) {
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
            body: JSON.stringify({ path: filePath })
        });

        if (!res.ok) throw new Error("Erreur lors de l'analyse du média.");
        const data = await res.json();
        currentAnalysis = data;
        currentAnalysis.source_path = filePath;

        // Reset generated buttons
        document.getElementById("btn-upload-c411").disabled = true;
        document.getElementById("btn-send-qbittorrent").disabled = true;
        document.getElementById("download-actions").style.display = "none";

        // Populate Overview Card
        const media = data.media_info;
        document.getElementById("gen-source-filename").textContent = media.file_name;
        document.getElementById("gen-source-path").textContent = `Chemin: ${filePath}`;
        
        const sizeMb = media.file_size / (1024 * 1024);
        document.getElementById("gen-stat-size").textContent = sizeMb >= 1024 ? `${(sizeMb / 1024).toFixed(2)} Go` : `${sizeMb.toFixed(2)} Mo`;
        document.getElementById("gen-stat-res").textContent = media.resolution || "N/A";
        document.getElementById("gen-stat-video").textContent = media.video_codec || "N/A";
        
        const firstAudio = media.audio_tracks && media.audio_tracks.length > 0 ? media.audio_tracks[0] : null;
        document.getElementById("gen-stat-audio").textContent = firstAudio ? `${firstAudio.language} (${firstAudio.format})` : "N/A";

        // Populate Namer & Anti-Detag
        const namer = data.namer;
        document.getElementById("input-release-title").value = namer.title;
        document.getElementById("input-year").value = namer.year || "";
        document.getElementById("input-lang-tag").value = namer.language || "";
        document.getElementById("select-source").value = namer.source || "WEB";
        document.getElementById("input-team-tag").value = namer.final_tag || "NOTAG";

        const badgeTag = document.getElementById("badge-tag-status");
        if (namer.detected_tag) {
            badgeTag.textContent = `TAG D'ORIGINE : -${namer.detected_tag}`;
            badgeTag.className = "badge badge-success";
        } else {
            badgeTag.textContent = "AUCUN TAG : -NOTAG";
            badgeTag.className = "badge badge-warning";
        }
        document.getElementById("text-detag-explanation").textContent = namer.detag_warning;

        // Populate Piece Size
        document.getElementById("select-piece-size").value = data.suggested_piece_size;
        document.getElementById("badge-piece-calc").textContent = `Recommandé C411 : ${data.suggested_piece_size / (1024 * 1024)} Mo`;

        // Populate Category
        document.getElementById("select-category").value = data.suggested_category_id;

        // TMDB query prefill
        const cleanNameGuess = media.file_name.replace(/\b(19\d\d|20\d\d)\b.*$/, "").replace(/[\._\-]/g, " ").trim();
        document.getElementById("tmdb-search-input").value = cleanNameGuess;

        // Populate Editors
        document.getElementById("editor-nfo").value = data.nfo;
        document.getElementById("editor-bbcode").value = data.bbcode;

        showToast("Média analysé avec succès selon les standards C411 !", "success");

        // Auto duplicate check prompt
        checkDuplicatesC411(namer.title);

    } catch (e) {
        showToast(`Échec de l'analyse : ${e.message}`, "error");
    }
}

function initGenerator() {
    // Recalculate title when fields change
    document.getElementById("btn-recalc-title").addEventListener("click", () => {
        if (!currentAnalysis) return;
        const year = document.getElementById("input-year").value.trim();
        const lang = document.getElementById("input-lang-tag").value.trim();
        const source = document.getElementById("select-source").value;
        const tag = document.getElementById("input-team-tag").value.trim();

        // Extract base title
        let raw = currentAnalysis.media_info.file_name;
        // Clean dots
        let titlePart = raw.replace(/\b(19\d\d|20\d\d)\b.*$/, "").replace(/[\s_\-]+/g, ".").replace(/[^\w\.]/g, "").trim(".");

        const parts = [titlePart];
        if (year) parts.push(year);
        if (lang) parts.push(lang);
        if (currentAnalysis.media_info.resolution && currentAnalysis.media_info.resolution !== "Autre") parts.push(currentAnalysis.media_info.resolution);
        if (source) parts.push(source);
        if (currentAnalysis.media_info.video_codec) parts.push(currentAnalysis.media_info.video_codec);

        const newTitle = parts.join(".") + `-${tag || 'NOTAG'}`;
        document.getElementById("input-release-title").value = newTitle;
        showToast("Titre réactualisé !", "info");
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

        const payload = {
            source_path: currentAnalysis.source_path,
            release_name: releaseName,
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
            source_path: currentAnalysis.source_path
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

// C411 Duplicate Search
async function checkDuplicatesC411(releaseTitle) {
    const resBox = document.getElementById("duplicate-results");
    resBox.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Recherche sur C411 en cours...`;

    // Extract core words for search query
    const words = releaseTitle.split(".")[0];
    const yearMatch = releaseTitle.match(/\b(19\d\d|20\d\d)\b/);
    const query = yearMatch ? `${words} ${yearMatch[0]}` : words;

    try {
        const res = await fetch("/api/search-c411", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query })
        });
        const data = await res.json();

        if (data.results && data.results.length > 0) {
            let html = `<div class="mb-2 text-warning"><i class="fa-solid fa-triangle-exclamation mr-1"></i> <strong>${data.results.length} release(s) similaire(s) trouvée(s) sur C411 :</strong></div><ul class="text-xs" style="max-height: 120px; overflow-y: auto;">`;
            data.results.slice(0, 5).forEach(item => {
                html += `
                    <li class="py-1 border-b border-dark flex justify-between items-center">
                        <span class="truncate mr-2" style="max-width: 250px;">${escapeHtml(item.title)}</span>
                        <span><strong class="text-success">${item.seeders}S</strong> / ${item.size}</span>
                    </li>
                `;
            });
            html += `</ul><div class="mt-2 text-muted">Vérifiez que votre version n'est pas un doublon strict avant de publier.</div>`;
            resBox.innerHTML = html;
        } else {
            resBox.innerHTML = `<div class="text-success"><i class="fa-solid fa-circle-check mr-1"></i> Aucun doublon direct trouvé sur C411 avec la recherche "${escapeHtml(query)}". Parfait pour un nouvel upload !</div>`;
        }
    } catch (e) {
        resBox.innerHTML = `<span class="text-muted">Recherche non disponible (Vérifiez la clé API C411 dans Paramètres).</span>`;
    }
}

// TMDB Search & Selection
async function searchTmdb() {
    const q = document.getElementById("tmdb-search-input").value.trim();
    if (!q) return;

    const container = document.getElementById("tmdb-results-container");
    const list = document.getElementById("tmdb-cards-list");
    list.innerHTML = `<div class="text-muted"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Recherche TMDB...</div>`;
    container.style.display = "block";

    try {
        const res = await fetch("/api/tmdb-search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: q })
        });
        const data = await res.json();

        if (!data.results || data.results.length === 0) {
            list.innerHTML = `<div class="text-muted">Aucun résultat trouvé sur TMDB.</div>`;
            return;
        }

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
    }
}

function applyTmdbMetadata(item) {
    document.getElementById("tmdb-id-val").value = item.id;
    document.getElementById("poster-url-val").value = item.poster_url || "";
    document.getElementById("tmdb-results-container").style.display = "none";

    // Regenerate BBCode description with Poster and French Synopsis
    if (currentAnalysis) {
        const releaseTitle = document.getElementById("input-release-title").value;
        const source = document.getElementById("select-source").value;
        const tag = document.getElementById("input-team-tag").value;
        const nfo = document.getElementById("editor-nfo").value;

        // Custom BBCode update
        let bb = `[center]\n`;
        if (item.poster_url) {
            bb += `[img]${item.poster_url}[/img]\n\n`;
        }
        bb += `[size=5][b][color=#3498db]${releaseTitle}[/color][/b][/size]\n[hr]\n`;
        if (item.synopsis) {
            bb += `[size=4][b][color=#e74c3c]SYNOPSIS[/color][/b][/size]\n[quote]${item.synopsis}[/quote]\n\n`;
        }
        bb += `[size=4][b][color=#2ecc71]INFORMATIONS SUR LA RELEASE[/color][/b][/size]\n`;
        bb += `[b]Format conteneur :[/b] ${currentAnalysis.media_info.container}\n`;
        bb += `[b]Durée :[/b] ${currentAnalysis.media_info.duration}\n`;
        bb += `[b]Source :[/b] ${source}\n`;
        bb += `[b]Signature / Tag :[/b] ${tag}\n\n`;

        bb += `[size=4][b][color=#f39c12]DÉTAILS TECHNIQUES[/color][/b][/size]\n`;
        bb += `[b]Vidéo :[/b] ${currentAnalysis.media_info.video_codec} (${currentAnalysis.media_info.resolution})\n`;
        if (currentAnalysis.media_info.audio_tracks) {
            currentAnalysis.media_info.audio_tracks.forEach((a, i) => {
                bb += `[b]Audio #${i+1} :[/b] ${a.language} | ${a.format} ${a.channels} ch\n`;
            });
        }
        bb += `\n[size=4][b][color=#9b59b6]NFO TECHNIQUE[/color][/b][/size]\n`;
        bb += `[spoiler=Afficher le NFO][font=monospace]${nfo}[/font][/spoiler]\n[hr]\n`;
        bb += `[i]Release partagée avec Torrent Generator C411[/i]\n[/center]`;

        document.getElementById("editor-bbcode").value = bb;
        showToast(`Métadonnées appliquées : "${item.title}" (${item.year})`, "success");
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
        document.getElementById("cfg-qb-map-to").value = cfg.qbittorrent_path_mapping_to || "/mnt/Plex/Plex/films";
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
