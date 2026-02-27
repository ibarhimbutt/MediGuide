/**
 * MediGuide AI — Event handlers: feature switch, language, forms, file upload, report.
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.state || !MG.api) return;
    var state = MG.state;

    MG.switchFeature = function (feature) {
        state.currentFeature = feature;
        document.querySelectorAll(".feature-tab").forEach(function (tab) {
            tab.classList.toggle("active", tab.dataset.feature === feature);
        });
        document.querySelectorAll(".input-panel").forEach(function (panel) {
            panel.classList.add("hidden");
        });
        var panel = document.getElementById("input-" + feature);
        if (panel) panel.classList.remove("hidden");
        var welcome = document.getElementById("welcome-message");
        if (welcome) welcome.style.display = "none";
        if (feature !== "symptom-checker") state.symptomHistory = [];
    };

    MG.renderHistory = function (items) {
        var container = document.getElementById("recent-chats");
        if (!container) return;
        container.innerHTML = "";
        if (!items || !items.length) {
            var empty = document.createElement("p");
            empty.className = "text-[12px] text-gray-400";
            empty.textContent = "Your recent MediGuide conversations will appear here.";
            container.appendChild(empty);
            state.historyItems = [];
            return;
        }
        state.historyItems = items;
        items.forEach(function (item, index) {
            var btn = document.createElement("button");
            btn.className =
                "w-full text-left px-3 py-2 rounded-xl truncate hover:bg-gray-50 " +
                (index === 0 ? "bg-gray-50 text-gray-800 font-medium" : "text-gray-500");
            btn.textContent = item.title || "Conversation";
            btn.dataset.index = String(index);
            btn.addEventListener("click", function () {
                MG.openHistoryItem(parseInt(this.dataset.index, 10));
            });
            container.appendChild(btn);
        });
    };

    MG.setLanguage = function (lang) {
        state.currentLanguage = lang;
        var sel = document.getElementById("sidebar-language");
        if (sel) sel.value = lang;
        if (MG.persistSession) MG.persistSession();
    };

    MG.insertExample = function (text) {
        if (state.currentFeature === "symptom-checker") {
            var el = document.getElementById("symptom-input");
            if (el) { el.value = text; el.focus(); }
        } else if (state.currentFeature === "medication-info") {
            var el2 = document.getElementById("medication-input");
            if (el2) { el2.value = text; el2.focus(); }
        }
    };

    MG.handleSymptomSubmit = function (event) {
        event.preventDefault();
        var input = document.getElementById("symptom-input");
        var btn = document.getElementById("symptom-btn");
        var message = (input && input.value ? input.value.trim() : "") || "";
        if (!message) return;
        state.symptomHistory.push({ role: "user", content: message });
        MG.addMessage(message, "user", undefined, undefined, { feature: "symptom-checker" });
        if (input) input.value = "";
        if (btn) btn.disabled = true;
        MG.addLoadingMessage();
        MG.api.chat({ message: message }).then(function (data) {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            if (input) input.focus();
            if (data.error) {
                MG.addMessage("Error: " + data.error, "assistant");
                return;
            }
            MG.addMessage(data.reply, "assistant", undefined, data.meta, { feature: "symptom-checker" });
            state.symptomHistory.push({ role: "assistant", content: data.reply });
            if (MG.persistSession) MG.persistSession();
        }).catch(function () {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            if (input) input.focus();
            MG.addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
        });
    };

    MG.handleReportSubmit = function (event) {
        event.preventDefault();
        if (!state.selectedPdfFile) return;
        var btn = document.getElementById("report-btn");
        MG.addMessage("Uploaded report: " + state.selectedPdfFile.name, "user");
        if (btn) btn.disabled = true;
        MG.addLoadingMessage();
        var formData = new FormData();
        formData.append("file", state.selectedPdfFile);
        MG.api.analyzeReport(formData).then(function (data) {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            MG.resetFileInput("pdf");
            if (data.error) {
                MG.addMessage("Error: " + data.error, "assistant");
                return;
            }
            MG.addMessage(data.reply, "assistant", undefined, data.meta, { feature: "report-explainer" });
        }).catch(function () {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            MG.resetFileInput("pdf");
            MG.addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
        });
    };

    MG.handleMedicationSubmit = function (event) {
        event.preventDefault();
        var input = document.getElementById("medication-input");
        var btn = document.getElementById("medication-btn");
        var medication = (input && input.value ? input.value.trim() : "") || "";
        if (!medication) return;
        MG.addMessage("Medication safety check for:\n" + medication, "user");
        if (input) input.value = "";
        if (btn) btn.disabled = true;
        MG.addLoadingMessage();
        MG.api.medicationInfo(medication).then(function (data) {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            if (input) input.focus();
            if (data.error) {
                MG.addMessage("Error: " + data.error, "assistant");
                return;
            }
            MG.addMessage(data.reply, "assistant", undefined, data.meta, { feature: "medication-info" });
        }).catch(function () {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            if (input) input.focus();
            MG.addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
        });
    };

    MG.handleImageSubmit = function (event) {
        event.preventDefault();
        if (!state.selectedImageFile) return;
        var btn = document.getElementById("image-btn");
        MG.addMessage("Uploaded image: " + state.selectedImageFile.name, "user");
        if (btn) btn.disabled = true;
        MG.addLoadingMessage();
        var formData = new FormData();
        formData.append("file", state.selectedImageFile);
        MG.api.analyzeImage(formData).then(function (data) {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            MG.resetFileInput("image");
            if (data.error) {
                MG.addMessage("Error: " + data.error, "assistant");
                return;
            }
            MG.addMessage(data.reply, "assistant", undefined, data.meta, { feature: "image-analysis" });
        }).catch(function () {
            MG.removeLoadingMessage();
            if (btn) btn.disabled = false;
            MG.resetFileInput("image");
            MG.addMessage("Failed to connect to the server. Please make sure the backend is running.", "assistant");
        });
    };

    MG.handleFileSelect = function (input, type) {
        var file = input && input.files && input.files[0];
        if (!file) return;
        if (type === "pdf") {
            state.selectedPdfFile = file;
            var fn = document.getElementById("pdf-filename");
            if (fn) fn.textContent = file.name;
            var zone = document.getElementById("pdf-drop-zone");
            if (zone) { zone.classList.add("border-primary-400", "bg-primary-50"); }
            var reportBtn = document.getElementById("report-btn");
            if (reportBtn) reportBtn.disabled = false;
        } else if (type === "image") {
            state.selectedImageFile = file;
            var fn2 = document.getElementById("image-filename");
            if (fn2) fn2.textContent = file.name;
            var zone2 = document.getElementById("image-drop-zone");
            if (zone2) zone2.classList.add("border-primary-400", "bg-primary-50");
            var imgBtn = document.getElementById("image-btn");
            if (imgBtn) imgBtn.disabled = false;
            var preview = document.getElementById("image-preview");
            var container = document.getElementById("image-preview-container");
            if (preview && container) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    preview.src = e.target.result;
                    container.classList.remove("hidden");
                };
                reader.readAsDataURL(file);
            }
        }
    };

    MG.resetFileInput = function (type) {
        if (type === "pdf") {
            state.selectedPdfFile = null;
            var input = document.getElementById("pdf-input");
            if (input) input.value = "";
            var fn = document.getElementById("pdf-filename");
            if (fn) fn.textContent = "Drop your medical report PDF here or click to browse";
            var zone = document.getElementById("pdf-drop-zone");
            if (zone) zone.classList.remove("border-primary-400", "bg-primary-50");
            var btn = document.getElementById("report-btn");
            if (btn) btn.disabled = true;
        } else if (type === "image") {
            state.selectedImageFile = null;
            var input2 = document.getElementById("image-input");
            if (input2) input2.value = "";
            var fn2 = document.getElementById("image-filename");
            if (fn2) fn2.textContent = "Drop a medical image here or click to browse";
            var zone2 = document.getElementById("image-drop-zone");
            if (zone2) zone2.classList.remove("border-primary-400", "bg-primary-50");
            var btn2 = document.getElementById("image-btn");
            if (btn2) btn2.disabled = true;
            var container = document.getElementById("image-preview-container");
            if (container) container.classList.add("hidden");
        }
    };

    MG.setupDragDrop = function (zoneId, inputId, type) {
        var zone = document.getElementById(zoneId);
        if (!zone) return;
        ["dragenter", "dragover"].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                zone.classList.add("border-primary-400", "bg-primary-50");
            });
        });
        ["dragleave", "drop"].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                if (evt === "dragleave") zone.classList.remove("border-primary-400", "bg-primary-50");
            });
        });
        zone.addEventListener("drop", function (e) {
            var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
            if (file) {
                var input = document.getElementById(inputId);
                if (input) {
                    var dt = new DataTransfer();
                    dt.items.add(file);
                    input.files = dt.files;
                    MG.handleFileSelect(input, type);
                }
            }
        });
    };

    MG.reportAnswer = function (feature, replyText, safetyEncoded) {
        try {
            var safety = {};
            if (safetyEncoded) {
                try {
                    safety = JSON.parse(decodeURIComponent(safetyEncoded));
                } catch (e) {}
            }
            MG.api.reportAnswer({ feature: feature, reply: replyText, safety: safety });
        } catch (e) {}
    };

    MG.startNewChat = function () {
        var chatArea = document.getElementById("chat-area");
        var welcome = document.getElementById("welcome-message");
        if (!chatArea) return;

        state.messageLog = [];
        state.symptomHistory = [];
        state.selectedPdfFile = null;
        state.selectedImageFile = null;

        var children = Array.from(chatArea.children);
        children.forEach(function (node) {
            if (node !== welcome) chatArea.removeChild(node);
        });

        MG.switchFeature("symptom-checker");
        if (welcome) welcome.style.display = "";
        if (MG.persistSession) MG.persistSession();
    };

    MG.openHistoryItem = function (index) {
        var items = state.historyItems || [];
        if (index < 0 || index >= items.length) return;
        var item = items[index];
        var messages = item.messages || [];
        var chatArea = document.getElementById("chat-area");
        var welcome = document.getElementById("welcome-message");
        if (chatArea) chatArea.innerHTML = "";
        if (welcome) welcome.style.display = "none";

        state.symptomHistory = [];
        state.messageLog = [];

        messages.forEach(function (m) {
            MG.addMessage(m.content, m.role, undefined, m.meta || null, {
                feature: item.feature || "symptom-checker",
            });
            if (item.feature === "symptom-checker") {
                state.symptomHistory.push({ role: m.role, content: m.content });
            }
        });

        MG.switchFeature(item.feature === "medication-safety" ? "medication-info" : "symptom-checker");
        if (MG.persistSession) MG.persistSession();
    };

    // --- Help modal ---
    MG.openHelpModal = function () {
        var modal = document.getElementById("help-modal");
        if (modal) {
            modal.classList.remove("hidden");
            modal.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";
        }
    };

    MG.closeHelpModal = function () {
        var modal = document.getElementById("help-modal");
        if (modal) {
            modal.classList.add("hidden");
            modal.setAttribute("aria-hidden", "true");
            document.body.style.overflow = "";
        }
    };

    // --- Share chat link ---
    MG.shareChatLink = function () {
        var url = window.location.href;
        var toast = document.getElementById("share-toast");
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(url).then(
                function () {
                    if (toast) {
                        toast.classList.remove("opacity-0", "pointer-events-none");
                        toast.classList.add("opacity-100");
                        window.setTimeout(function () {
                            toast.classList.add("opacity-0", "pointer-events-none");
                            toast.classList.remove("opacity-100");
                        }, 2000);
                    }
                },
                function () { /* fallback: try select + execCommand */ fallbackCopy(url, toast); }
            );
        } else {
            fallbackCopy(url, toast);
        }
    };

    function fallbackCopy(url, toast) {
        try {
            var ta = document.createElement("textarea");
            ta.value = url;
            ta.setAttribute("readonly", "");
            ta.style.position = "fixed";
            ta.style.opacity = "0";
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
            if (toast) {
                toast.classList.remove("opacity-0", "pointer-events-none");
                toast.classList.add("opacity-100");
                window.setTimeout(function () {
                    toast.classList.add("opacity-0", "pointer-events-none");
                    toast.classList.remove("opacity-100");
                }, 2000);
            }
        } catch (e) {}
    }
})();
