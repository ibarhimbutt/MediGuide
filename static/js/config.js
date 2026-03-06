/**
 * MediGuide AI — Client-side constants and config.
 */
(function () {
    "use strict";
    window.MediGuide = window.MediGuide || {};
    window.MediGuide.STORAGE_KEY = "mediguideSession";
    window.MediGuide.USER_ID_KEY = "mediguideUserId";
    window.MediGuide.FEATURE_ICONS = {
        "symptom-checker": "fa-stethoscope",
        "report-explainer": "fa-file-medical",
        "medication-info": "fa-pills",
        "image-analysis": "fa-x-ray",
        "health-timeline": "fa-clock-rotate-left",
    };
    window.MediGuide.LANGUAGE_LABELS = {
        en: "English",
        ur: "Urdu",
        ar: "Arabic",
        hi: "Hindi",
    };
})();
