// ---------------------------------------------------------------------------
// MediGuide AI — Frontend Application
// ---------------------------------------------------------------------------

let currentFeature = "symptom-checker";
let currentLanguage = "en"; // en, ur, ar, hi
let selectedPdfFile = null;
let selectedImageFile = null;

// Conversation history for symptom checker (AI triage agent)
// Stored as an array of { role: "user" | "assistant", content: string }
let symptomHistory = [];

// ---------------------------------------------------------------------------
// Feature switching
// ---------------------------------------------------------------------------

function switchFeature(feature) {
    currentFeature = feature;

    document.querySelectorAll(".feature-tab").forEach((tab) => {
        tab.classList.toggle("active", tab.dataset.feature === feature);
    });

    document.querySelectorAll(".input-panel").forEach((panel) => {
        panel.classList.add("hidden");
    });
    const activePanel = document.getElementById(`input-${feature}`);
    if (activePanel) activePanel.classList.remove("hidden");

    const welcome = document.getElementById("welcome-message");
    if (welcome) welcome.style.display = "none";

    // Reset symptom conversation when switching away from the symptom checker
    if (feature !== "symptom-checker") {
        symptomHistory = [];
    }
}

function setLanguage(lang) {
    currentLanguage = lang;

    document.querySelectorAll("[data-language-option]").forEach((el) => {
        el.classList.remove("language-active");
    });

    const active = document.querySelector(`[data-language-option="${lang}"]`);
    if (active) {
        active.classList.add("language-active");
    }
}

function insertExample(text) {
    if (currentFeature === "symptom-checker") {
        document.getElementById("symptom-input").value = text;
        document.getElementById("symptom-input").focus();
    } else if (currentFeature === "medication-info") {
        document.getElementById("medication-input").value = text;
        document.getElementById("medication-input").focus();
    }
}

// ---------------------------------------------------------------------------
// Chat message rendering
// ---------------------------------------------------------------------------

function addMessage(content, role, icon, meta) {
    const chatArea = document.getElementById("chat-area");
    const welcome = document.getElementById("welcome-message");
    if (welcome) welcome.style.display = "none";

    const wrapper = document.createElement("div");
    wrapper.className = `flex gap-3 ${role === "user" ? "justify-end" : "justify-start"} message-enter`;

    const iconMap = {
        "symptom-checker": "fa-stethoscope",
        "report-explainer": "fa-file-medical",
        "medication-info": "fa-pills",
        "image-analysis": "fa-x-ray",
    };

    if (role === "user") {
        wrapper.innerHTML = `
            <div class="max-w-2xl">
                <div class="bg-primary-600 text-white px-4 py-3 rounded-2xl rounded-tr-md text-sm leading-relaxed">
                    ${escapeHtml(content)}
                </div>
            </div>
            <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center shrink-0 mt-1">
                <i class="fas fa-user text-primary-600 text-xs"></i>
            </div>`;
    } else {
        const aiIcon = icon || iconMap[currentFeature] || "fa-heartbeat";
        wrapper.innerHTML = `
            <div class="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center shrink-0 mt-1">
                <i class="fas ${aiIcon} text-white text-xs"></i>
            </div>
            <div class="max-w-2xl">
                <div class="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-md text-sm leading-relaxed text-gray-700 shadow-sm ai-response">
                    ${formatMarkdown(content)}
                    ${renderAiMeta(meta)}
                </div>
            </div>`;
    }

    chatArea.appendChild(wrapper);
    chatArea.scrollTop = chatArea.scrollHeight;
    return wrapper;
}

function addLoadingMessage() {
    const chatArea = document.getElementById("chat-area");
    const wrapper = document.createElement("div");
    wrapper.className = "flex gap-3 justify-start message-enter";
    wrapper.id = "loading-message";
    wrapper.innerHTML = `
        <div class="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center shrink-0 mt-1">
            <i class="fas fa-heartbeat text-white text-xs"></i>
        </div>
        <div class="bg-white border border-gray-200 px-5 py-4 rounded-2xl rounded-tl-md shadow-sm">
            <div class="flex items-center gap-2">
                <div class="loading-dots flex gap-1">
                    <span class="w-2 h-2 bg-primary-400 rounded-full"></span>
                    <span class="w-2 h-2 bg-primary-400 rounded-full"></span>
                    <span class="w-2 h-2 bg-primary-400 rounded-full"></span>
                </div>
                <span class="text-sm text-gray-400 ml-1">Analyzing...</span>
            </div>
        </div>`;
    chatArea.appendChild(wrapper);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function removeLoadingMessage() {
    const el = document.getElementById("loading-message");
    if (el) el.remove();
}

// ---------------------------------------------------------------------------
// Form handlers
// ---------------------------------------------------------------------------

async function handleSymptomSubmit(event) {
    event.preventDefault();
    const input = document.getElementById("symptom-input");
    const btn = document.getElementById("symptom-btn");
    const message = input.value.trim();
    if (!message) return;

    // Push to local history first so UI always reflects the full conversation
    symptomHistory.push({ role: "user", content: message });
    addMessage(message, "user");
    input.value = "";
    btn.disabled = true;
    addLoadingMessage();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message,
                history: symptomHistory,
                language: currentLanguage,
            }),
        });
        const data = await res.json();
        removeLoadingMessage();
        if (data.error) {
            addMessage(`Error: ${data.error}`, "assistant");
        } else {
            addMessage(data.reply, "assistant", undefined, data.meta);
            symptomHistory.push({ role: "assistant", content: data.reply });
        }
    } catch (err) {
        removeLoadingMessage();
        addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
    } finally {
        btn.disabled = false;
        input.focus();
    }
}

async function handleReportSubmit(event) {
    event.preventDefault();
    if (!selectedPdfFile) return;

    const btn = document.getElementById("report-btn");
    addMessage(`Uploaded report: ${selectedPdfFile.name}`, "user");
    btn.disabled = true;
    addLoadingMessage();

    const formData = new FormData();
    formData.append("file", selectedPdfFile);
    formData.append("language", currentLanguage);

    try {
        const res = await fetch("/analyze-report", { method: "POST", body: formData });
        const data = await res.json();
        removeLoadingMessage();
        if (data.error) {
            addMessage(`Error: ${data.error}`, "assistant");
        } else {
            addMessage(data.reply, "assistant", undefined, data.meta);
        }
    } catch (err) {
        removeLoadingMessage();
        addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
    } finally {
        btn.disabled = false;
        resetFileInput("pdf");
    }
}

async function handleMedicationSubmit(event) {
    event.preventDefault();
    const input = document.getElementById("medication-input");
    const btn = document.getElementById("medication-btn");
    const medication = input.value.trim();
    if (!medication) return;

    addMessage(`Medication safety check for:\n${medication}`, "user");
    input.value = "";
    btn.disabled = true;
    addLoadingMessage();

    try {
        const res = await fetch("/medication-info", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ medication, language: currentLanguage }),
        });
        const data = await res.json();
        removeLoadingMessage();
        if (data.error) {
            addMessage(`Error: ${data.error}`, "assistant");
        } else {
            addMessage(data.reply, "assistant", undefined, data.meta);
        }
    } catch (err) {
        removeLoadingMessage();
        addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
    } finally {
        btn.disabled = false;
        input.focus();
    }
}

async function handleImageSubmit(event) {
    event.preventDefault();
    if (!selectedImageFile) return;

    const btn = document.getElementById("image-btn");
    addMessage(`Uploaded image: ${selectedImageFile.name}`, "user");
    btn.disabled = true;
    addLoadingMessage();

    const formData = new FormData();
    formData.append("file", selectedImageFile);
    formData.append("language", currentLanguage);

    try {
        const res = await fetch("/analyze-image", { method: "POST", body: formData });
        const data = await res.json();
        removeLoadingMessage();
        if (data.error) {
            addMessage(`Error: ${data.error}`, "assistant");
        } else {
            addMessage(data.reply, "assistant", undefined, data.meta);
        }
    } catch (err) {
        removeLoadingMessage();
        addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
    } finally {
        btn.disabled = false;
        resetFileInput("image");
    }
}

// ---------------------------------------------------------------------------
// File handling
// ---------------------------------------------------------------------------

function handleFileSelect(input, type) {
    const file = input.files[0];
    if (!file) return;

    if (type === "pdf") {
        selectedPdfFile = file;
        document.getElementById("pdf-filename").textContent = file.name;
        document.getElementById("pdf-drop-zone").classList.add("border-primary-400", "bg-primary-50");
        document.getElementById("report-btn").disabled = false;
    } else if (type === "image") {
        selectedImageFile = file;
        document.getElementById("image-filename").textContent = file.name;
        document.getElementById("image-drop-zone").classList.add("border-primary-400", "bg-primary-50");
        document.getElementById("image-btn").disabled = false;

        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById("image-preview").src = e.target.result;
            document.getElementById("image-preview-container").classList.remove("hidden");
        };
        reader.readAsDataURL(file);
    }
}

function resetFileInput(type) {
    if (type === "pdf") {
        selectedPdfFile = null;
        document.getElementById("pdf-input").value = "";
        document.getElementById("pdf-filename").textContent = "Drop your medical report PDF here or click to browse";
        document.getElementById("pdf-drop-zone").classList.remove("border-primary-400", "bg-primary-50");
        document.getElementById("report-btn").disabled = true;
    } else if (type === "image") {
        selectedImageFile = null;
        document.getElementById("image-input").value = "";
        document.getElementById("image-filename").textContent = "Drop a medical image here or click to browse";
        document.getElementById("image-drop-zone").classList.remove("border-primary-400", "bg-primary-50");
        document.getElementById("image-btn").disabled = true;
        document.getElementById("image-preview-container").classList.add("hidden");
    }
}

// ---------------------------------------------------------------------------
// Drag and drop support
// ---------------------------------------------------------------------------

function setupDragDrop(zoneId, inputId, type) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;

    ["dragenter", "dragover"].forEach((evt) => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            zone.classList.add("border-primary-400", "bg-primary-50");
        });
    });

    ["dragleave", "drop"].forEach((evt) => {
        zone.addEventListener(evt, (e) => {
            e.preventDefault();
            if (evt === "dragleave") {
                zone.classList.remove("border-primary-400", "bg-primary-50");
            }
        });
    });

    zone.addEventListener("drop", (e) => {
        const file = e.dataTransfer.files[0];
        if (file) {
            const input = document.getElementById(inputId);
            const dt = new DataTransfer();
            dt.items.add(file);
            input.files = dt.files;
            handleFileSelect(input, type);
        }
    });
}

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    let html = escapeHtml(text);

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Headers (### → h4, ## → h3)
    html = html.replace(/^### (.+)$/gm, '<h4 class="font-semibold text-gray-900 mt-3 mb-1">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="font-bold text-gray-900 mt-4 mb-1 text-base">$1</h3>');

    // Bullet points
    html = html.replace(/^[-•] (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal">$1. $2</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li[^>]*>.*?<\/li>\n?)+)/g, '<ul class="my-2 space-y-1">$1</ul>');

    // Line breaks
    html = html.replace(/\n\n/g, "</p><p class='mt-2'>");
    html = html.replace(/\n/g, "<br>");

    return `<p>${html}</p>`;
}

function renderAiMeta(meta) {
    if (!meta) return "";
    const feature = meta.feature || "";
    const model = meta.model || "";
    const language = meta.language || currentLanguage || "en";

    const prettyLanguageMap = {
        en: "English",
        ur: "Urdu",
        ar: "Arabic",
        hi: "Hindi",
    };

    const prettyLanguage = prettyLanguageMap[language] || language;

    return `
        <div class="mt-3 pt-2 border-t border-gray-100 flex flex-wrap items-center gap-3 text-[11px] text-gray-400">
            <span class="inline-flex items-center gap-1">
                <i class="fas fa-microchip"></i>
                <span>${model || "Azure OpenAI"}</span>
            </span>
            <span class="inline-flex items-center gap-1">
                <i class="fas fa-language"></i>
                <span>${prettyLanguage}</span>
            </span>
            <span class="inline-flex items-center gap-1">
                <i class="fas fa-shield-heart"></i>
                <span>AI guidance only — not medical advice</span>
            </span>
        </div>
    `;
}

// ---------------------------------------------------------------------------
// Initialize
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    setupDragDrop("pdf-drop-zone", "pdf-input", "pdf");
    setupDragDrop("image-drop-zone", "image-input", "image");

    // Initialise language selector (default English)
    setLanguage(currentLanguage);
});
