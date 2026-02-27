/**
 * MediGuide AI — Session persistence (localStorage).
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.state) return;
    var state = MG.state;
    var key = MG.STORAGE_KEY || "mediguideSession";

    MG.persistSession = function () {
        try {
            var data = {
                userId: state.userId,
                currentLanguage: state.currentLanguage,
                symptomHistory: state.symptomHistory,
                messageLog: state.messageLog,
            };
            window.localStorage.setItem(key, JSON.stringify(data));
        } catch (e) {}
    };

    MG.restoreSession = function () {
        try {
            var raw = window.localStorage.getItem(key);
            if (!raw) return;
            var data = JSON.parse(raw);
            if (data.userId && !state.userId) state.userId = data.userId;
            if (data.currentLanguage) state.currentLanguage = data.currentLanguage;
            if (Array.isArray(data.symptomHistory)) state.symptomHistory = data.symptomHistory;
            if (Array.isArray(data.messageLog)) {
                state.messageLog = data.messageLog;
                state.messageLog.forEach(function (m) {
                    MG.addMessage(m.content, m.role, undefined, m.meta || null, {
                        feature: m.feature || "symptom-checker",
                        record: false,
                    });
                });
            }
        } catch (e) {
            state.messageLog = [];
        }
    };
})();
