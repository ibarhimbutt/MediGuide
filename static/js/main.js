/**
 * MediGuide AI — Bootstrap: init state, restore session, bind UI to window for HTML.
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.switchFeature || !MG.api) return;
    var SIDEBAR_STORAGE_KEY = "mediguideSidebarCollapsed";

    function getSidebarWrapper() {
        return document.getElementById("sidebar-wrapper");
    }

    function getSidebarToggleIcon() {
        return document.getElementById("sidebar-toggle-icon");
    }

    function toggleSidebar() {
        var wrapper = getSidebarWrapper();
        if (!wrapper) return;
        var icon = getSidebarToggleIcon();
        var collapsed = wrapper.classList.toggle("sidebar-collapsed");
        try {
            window.localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
        } catch (e) {}
        if (icon) {
            icon.className = collapsed ? "fas fa-chevron-right text-sm" : "fas fa-bars text-sm";
        }
    }

    function applySavedSidebarState() {
        var wrapper = getSidebarWrapper();
        if (!wrapper) return;
        var icon = getSidebarToggleIcon();
        try {
            var saved = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
            if (saved === "1") {
                wrapper.classList.add("sidebar-collapsed");
                if (icon) icon.className = "fas fa-chevron-right text-sm";
            } else {
                wrapper.classList.remove("sidebar-collapsed");
                if (icon) icon.className = "fas fa-bars text-sm";
            }
        } catch (e) {}
    }

    function init() {
        MG.initUserId();
        if (MG.initVoiceInput) MG.initVoiceInput();
        var body = document.body;
        if (body && body.dataset && body.dataset.userName) {
            MG.state.userDisplayName = body.dataset.userName;
        }
        MG.setupDragDrop("pdf-drop-zone", "pdf-input", "pdf");
        MG.setupDragDrop("image-drop-zone", "image-input", "image");
        MG.restoreSession();
        MG.setLanguage(MG.state.currentLanguage);

        if (!MG.state.messageLog || MG.state.messageLog.length === 0) {
            MG.addMessage(
                "Hello! I'm MediGuide AI — your personal health assistant. " +
                "I'm here to help with **symptoms**, **medications**, **health concerns**, and **medical triage** only. " +
                "How can I help you today?",
                "assistant",
                null,
                { feature: "symptom-checker", model: "MediGuide AI" },
                { record: false }
            );
        }
        applySavedSidebarState();

        var toggleBtn = document.getElementById("sidebar-toggle");
        if (toggleBtn) toggleBtn.addEventListener("click", toggleSidebar);

        // Help modal
        var helpBtn = document.getElementById("help-btn");
        if (helpBtn && MG.openHelpModal) helpBtn.addEventListener("click", MG.openHelpModal);
        var helpModalClose = document.getElementById("help-modal-close");
        if (helpModalClose && MG.closeHelpModal) helpModalClose.addEventListener("click", MG.closeHelpModal);
        var helpModalBackdrop = document.getElementById("help-modal-backdrop");
        if (helpModalBackdrop && MG.closeHelpModal) helpModalBackdrop.addEventListener("click", MG.closeHelpModal);

        var findDoctorsBtn = document.getElementById("find-doctors-btn");
        var doctorsModal = document.getElementById("doctors-modal");
        var doctorsModalClose = document.getElementById("doctors-modal-close");
        var doctorsModalBackdrop = document.getElementById("doctors-modal-backdrop");
        var doctorsSearchBtn = document.getElementById("doctors-search-btn");
        if (findDoctorsBtn && doctorsModal) {
            findDoctorsBtn.addEventListener("click", function () {
                doctorsModal.classList.remove("hidden");
                doctorsModal.setAttribute("aria-hidden", "false");
                document.body.style.overflow = "hidden";
            });
        }
        if (doctorsModalClose) doctorsModalClose.addEventListener("click", function () {
            doctorsModal.classList.add("hidden");
            doctorsModal.setAttribute("aria-hidden", "true");
            document.body.style.overflow = "";
        });
        if (doctorsModalBackdrop) doctorsModalBackdrop.addEventListener("click", function () {
            doctorsModalClose.click();
        });
        if (doctorsSearchBtn && MG.api && MG.api.doctors) {
            doctorsSearchBtn.addEventListener("click", function () {
                var city = MG.state.userCity;
                var stateVal = MG.state.userState;
                var specialty = (document.getElementById("doctors-specialty") || {}).value || "Internal Medicine";
                var resultsEl = document.getElementById("doctors-results");
                var hintEl = document.getElementById("doctors-modal-hint");
                if (!city || !stateVal) {
                    if (hintEl) hintEl.textContent = "Location not detected. Please ensure your location is available (US city and state required).";
                    if (resultsEl) resultsEl.innerHTML = "";
                    return;
                }
                if (hintEl) hintEl.textContent = "Searching " + specialty + " in " + city + ", " + stateVal + "...";
                if (resultsEl) resultsEl.innerHTML = '<div class="text-gray-500"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';
                MG.api.doctors(city, stateVal, specialty).then(function (data) {
                    if (hintEl) hintEl.textContent = "Search US healthcare providers by specialty. Requires your location (city, state).";
                    if (!data.providers || !data.providers.length) {
                        resultsEl.innerHTML = '<p class="text-gray-500">No providers found. Try a different specialty or location.</p>';
                        return;
                    }
                    var html = '<p class="font-medium text-gray-700 mb-2">' + data.providers.length + ' provider(s) found</p>';
                    data.providers.forEach(function (d) {
                        html += '<div class="p-3 rounded-lg bg-gray-50 border border-gray-100"><span class="font-medium">' + (d.name || "Provider") + (d.credential ? ' <span class="text-gray-500">' + d.credential + '</span>' : '') + '</span>' +
                            (d.address ? '<p class="text-xs text-gray-500 mt-1">' + d.address + '</p>' : '') + '</div>';
                    });
                    html += '<p class="mt-2 text-[10px] text-gray-400">Source: NPPES (US National Provider Identifier Registry)</p>';
                    resultsEl.innerHTML = html;
                }).catch(function () {
                    if (hintEl) hintEl.textContent = "Search US healthcare providers by specialty. Requires your location (city, state).";
                    resultsEl.innerHTML = '<p class="text-red-500">Failed to load providers. Please try again.</p>';
                });
            });
        }
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                var modal = document.getElementById("help-modal");
                if (modal && !modal.classList.contains("hidden") && MG.closeHelpModal) MG.closeHelpModal();
            }
        });

        // Share chat link
        var shareBtn = document.getElementById("chat-share-btn");
        if (shareBtn && MG.shareChatLink) shareBtn.addEventListener("click", MG.shareChatLink);

        // Literacy mode toggle
        var literacyBtns = document.querySelectorAll(".literacy-btn");
        literacyBtns.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var mode = this.dataset.mode || "standard";
                MG.state.literacyMode = mode;
                literacyBtns.forEach(function (b) {
                    b.classList.remove("literacy-active", "ring-1", "ring-teal-500");
                    b.classList.add("bg-gray-100", "text-gray-700");
                    if (b.dataset.mode === "simple") { b.classList.remove("bg-blue-100", "text-blue-700"); b.classList.add("bg-blue-50", "text-blue-600"); }
                    if (b.dataset.mode === "medical") { b.classList.remove("bg-emerald-100", "text-emerald-700"); b.classList.add("bg-emerald-50", "text-emerald-600"); }
                });
                this.classList.remove("bg-gray-100", "bg-blue-50", "bg-emerald-50");
                this.classList.add("literacy-active", "ring-1", "ring-teal-500");
                if (mode === "simple") { this.classList.add("bg-blue-100", "text-blue-700"); }
                else if (mode === "medical") { this.classList.add("bg-emerald-100", "text-emerald-700"); }
                else { this.classList.add("bg-gray-200", "text-gray-800"); }
                try { localStorage.setItem("mediguideLiteracyMode", mode); } catch (e) {}
                if (MG.api && MG.api.savePreference) {
                    MG.api.savePreference("literacyMode", mode);
                } else if (state.userId) {
                    fetch("/save-preference", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ userId: state.userId, key: "literacyMode", value: mode }),
                    });
                }
                var toast = document.getElementById("literacy-toast");
                var labels = { simple: "Simple Mode", standard: "Standard Mode", medical: "Medical Mode" };
                if (toast) {
                    toast.textContent = "Switched to " + (labels[mode] || mode) + " — responses will now use " + (mode === "simple" ? "easy language" : mode === "medical" ? "clinical terminology" : "balanced language");
                    toast.classList.remove("opacity-0", "pointer-events-none");
                    toast.classList.add("opacity-100");
                    setTimeout(function () {
                        toast.classList.add("opacity-0", "pointer-events-none");
                        toast.classList.remove("opacity-100");
                    }, 2500);
                }
            });
        });
        try {
            var saved = localStorage.getItem("mediguideLiteracyMode");
            if (saved && ["simple", "standard", "medical"].indexOf(saved) >= 0) {
                MG.state.literacyMode = saved;
                literacyBtns.forEach(function (b) {
                    b.classList.remove("literacy-active", "ring-1", "ring-teal-500");
                    if (b.dataset.mode === saved) {
                        b.classList.add("literacy-active", "ring-1", "ring-teal-500");
                        if (saved === "simple") { b.classList.remove("bg-gray-100"); b.classList.add("bg-blue-100", "text-blue-700"); }
                        else if (saved === "medical") { b.classList.remove("bg-gray-100"); b.classList.add("bg-emerald-100", "text-emerald-700"); }
                        else { b.classList.add("bg-gray-200", "text-gray-800"); }
                    } else {
                        if (b.dataset.mode === "simple") { b.classList.add("bg-blue-50", "text-blue-600"); }
                        else if (b.dataset.mode === "medical") { b.classList.add("bg-emerald-50", "text-emerald-600"); }
                        else { b.classList.add("bg-gray-100", "text-gray-700"); }
                    }
                });
            }
        } catch (e) {}

        // User menu dropdown
        var userMenuBtn = document.getElementById("user-menu-btn");
        var userMenuDropdown = document.getElementById("user-menu-dropdown");
        if (userMenuBtn && userMenuDropdown) {
            userMenuBtn.addEventListener("click", function (e) {
                e.stopPropagation();
                var open = userMenuDropdown.classList.toggle("hidden");
                userMenuBtn.setAttribute("aria-expanded", open ? "false" : "true");
            });
            document.addEventListener("click", function () {
                userMenuDropdown.classList.add("hidden");
                userMenuBtn.setAttribute("aria-expanded", "false");
            });
        }

        // Load recent history for sidebar
        MG.api.history().then(function (data) {
            if (MG.renderHistory) MG.renderHistory(data.items || []);
        });

        // Expose handlers for inline onclick (no HTML change)
        window.switchFeature = MG.switchFeature;
        window.startNewChat = MG.startNewChat;
        window.setLanguage = MG.setLanguage;
        window.insertExample = MG.insertExample;
        window.handleSymptomSubmit = function (e) { MG.handleSymptomSubmit(e); };
        window.handleReportSubmit = function (e) { MG.handleReportSubmit(e); };
        window.handleMedicationSubmit = function (e) { MG.handleMedicationSubmit(e); };
        window.handleImageSubmit = function (e) { MG.handleImageSubmit(e); };
        window.handleFileSelect = function (input, type) { MG.handleFileSelect(input, type); };
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
