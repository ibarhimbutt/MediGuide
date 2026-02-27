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
        MG.setupDragDrop("pdf-drop-zone", "pdf-input", "pdf");
        MG.setupDragDrop("image-drop-zone", "image-input", "image");
        MG.restoreSession();
        MG.setLanguage(MG.state.currentLanguage);
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
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                var modal = document.getElementById("help-modal");
                if (modal && !modal.classList.contains("hidden") && MG.closeHelpModal) MG.closeHelpModal();
            }
        });

        // Share chat link
        var shareBtn = document.getElementById("chat-share-btn");
        if (shareBtn && MG.shareChatLink) shareBtn.addEventListener("click", MG.shareChatLink);

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
