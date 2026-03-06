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
                    literacyMode: state.literacyMode,
                    location: state.userLocation,
                    city: state.userCity,
                    state: state.userState,
                    country: state.userCountry,
                }),
            }).then(function (r) { return r.json(); });
        },
        analyzeReport: function (formData) {
            formData.append("language", state.currentLanguage);
            formData.append("userId", state.userId || "");
            formData.append("literacyMode", state.literacyMode || "standard");
            if (state.userLocation) formData.append("location", state.userLocation);
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
                    literacyMode: state.literacyMode,
                    location: state.userLocation,
                }),
            }).then(function (r) { return r.json(); });
        },
        analyzeImage: function (formData) {
            formData.append("language", state.currentLanguage);
            formData.append("userId", state.userId || "");
            formData.append("literacyMode", state.literacyMode || "standard");
            if (state.userLocation) formData.append("location", state.userLocation);
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
        doctors: function (city, state, taxonomy) {
            var params = "city=" + encodeURIComponent(city || "") + "&state=" + encodeURIComponent(state || "") + "&taxonomy=" + encodeURIComponent(taxonomy || "Internal Medicine");
            return fetch("/api/doctors?" + params).then(function (r) { return r.json(); });
        },
        history: function () {
            if (!state.userId) return Promise.resolve({ items: [] });
            return fetch("/history?userId=" + encodeURIComponent(state.userId))
                .then(function (r) { return r.json(); })
                .catch(function () { return { items: [] }; });
        },
        timeline: function (range) {
            if (!state.userId) return Promise.resolve({ items: [], summary: "" });
            var q = "userId=" + encodeURIComponent(state.userId);
            if (range) q += "&range=" + encodeURIComponent(range);
            return fetch("/timeline?" + q).then(function (r) { return r.json(); });
        },
        downloadHealthReport: function (payload) {
            return fetch("/download-health-report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }).then(function (r) {
                if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || "Failed"); });
                return r.blob();
            });
        },
        generateErPdf: function (params) {
            var payload = {
                patient_id: state.userId,
                patient_name: state.userDisplayName || "Patient",
                symptoms: params.symptoms || "",
                symptom_timeline: params.symptomTimeline || "As reported in this session.",
                urgency: params.urgency || "HIGH",
                doctor_questions: params.doctorQuestions || [],
            };
            return fetch("/generate-er-pdf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            }).then(function (r) {
                if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || "Failed"); });
                return r.blob();
            });
        },
    };
})();
