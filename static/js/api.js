/**
 * MediGuide AI — API client (fetch wrappers).
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.state) return;
    var state = MG.state;

    MG.api = {
        chat: function (payload) {
            return fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: payload.message,
                    history: payload.history || state.symptomHistory,
                    language: state.currentLanguage,
                    userId: state.userId,
                }),
            }).then(function (r) { return r.json(); });
        },
        analyzeReport: function (formData) {
            formData.append("language", state.currentLanguage);
            formData.append("userId", state.userId || "");
            return fetch("/analyze-report", { method: "POST", body: formData }).then(function (r) { return r.json(); });
        },
        medicationInfo: function (medication) {
            return fetch("/medication-info", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    medication: medication,
                    language: state.currentLanguage,
                    userId: state.userId,
                }),
            }).then(function (r) { return r.json(); });
        },
        analyzeImage: function (formData) {
            formData.append("language", state.currentLanguage);
            formData.append("userId", state.userId || "");
            return fetch("/analyze-image", { method: "POST", body: formData }).then(function (r) { return r.json(); });
        },
        reportAnswer: function (payload) {
            return fetch("/report-answer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    userId: state.userId,
                    feature: payload.feature,
                    reply: payload.reply,
                    language: state.currentLanguage,
                    safety: payload.safety || {},
                }),
            }).then(function (r) { return r.json(); });
        },
        history: function () {
            if (!state.userId) return Promise.resolve({ items: [] });
            return fetch("/history?userId=" + encodeURIComponent(state.userId))
                .then(function (r) { return r.json(); })
                .catch(function () { return { items: [] }; });
        },
    };
})();
