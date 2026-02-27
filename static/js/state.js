/**
 * MediGuide AI — Application state (single source of truth).
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG) return;

    MG.state = {
        currentFeature: "symptom-checker",
        currentLanguage: "en",
        userId: null,
        symptomHistory: [],
        messageLog: [],
        selectedPdfFile: null,
        selectedImageFile: null,
    };

    MG.initUserId = function () {
        try {
            var stored = window.localStorage.getItem(MG.USER_ID_KEY);
            if (stored) {
                MG.state.userId = stored;
                return;
            }
            if (window.crypto && window.crypto.randomUUID) {
                MG.state.userId = window.crypto.randomUUID();
            } else {
                MG.state.userId = "user-" + Date.now();
            }
            window.localStorage.setItem(MG.USER_ID_KEY, MG.state.userId);
        } catch (e) {
            MG.state.userId = "user-" + Date.now();
        }
    };
})();
