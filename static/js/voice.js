/**
 * MediGuide AI — Voice-to-symptom input using Web Speech API.
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.state) return;
    var state = MG.state;

    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    var recognition = null;
    var isListening = false;

    var LANG_MAP = {
        "en": "en-US",
        "en-US": "en-US",
        "en-GB": "en-GB",
        "ur": "ur-PK",
        "ur-PK": "ur-PK",
        "ar": "ar-SA",
        "ar-SA": "ar-SA",
        "hi": "hi-IN",
        "hi-IN": "hi-IN",
    };
    var LANG_LABELS = {
        "en-US": "English",
        "en-GB": "English (UK)",
        "ur-PK": "Urdu",
        "ar-SA": "Arabic",
        "hi-IN": "Hindi",
    };

    function getRecognitionLang() {
        var uiLang = state.currentLanguage || "en";
        return LANG_MAP[uiLang] || LANG_MAP["en"] || "en-US";
    }

    function getLangLabel(lang) {
        return LANG_LABELS[lang] || lang || "English";
    }

    function isSupported() {
        return !!SpeechRecognition;
    }

    MG.toggleVoiceInput = function () {
        if (!isSupported()) {
            var btn = document.getElementById("voice-input-btn");
            if (btn) btn.setAttribute("title", "Voice input requires Chrome or Edge");
            return;
        }
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    };

    function startListening() {
        if (!SpeechRecognition || !isSupported()) return;
        var input = document.getElementById("symptom-input");
        var btn = document.getElementById("voice-input-btn");
        var icon = document.getElementById("voice-icon");
        var dot = document.getElementById("voice-listening-dot");
        var status = document.getElementById("voice-status");
        var langLabel = document.getElementById("voice-lang-label");
        if (!input || !btn) return;

        try {
            if (!recognition) {
                recognition = new SpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.onresult = function (e) {
                    var transcript = "";
                    for (var i = e.resultIndex; i < e.results.length; i++) {
                        if (e.results[i].isFinal) {
                            transcript += e.results[i][0].transcript;
                        }
                    }
                    if (transcript) {
                        var current = input.value.trim();
                        input.value = current ? current + " " + transcript : transcript;
                    }
                };
                recognition.onend = function () {
                    if (isListening) {
                        try { recognition.start(); } catch (err) {}
                    } else {
                        setListeningUI(false);
                        if (MG.voiceAutoSubmitEnabled && MG.voiceAutoSubmitEnabled()) {
                            var inp = document.getElementById("symptom-input");
                            if (inp && inp.value.trim()) {
                                var form = document.getElementById("symptom-form");
                                if (form && typeof handleSymptomSubmit === "function") {
                                    handleSymptomSubmit({ preventDefault: function () {} });
                                }
                            }
                        }
                    }
                };
                recognition.onerror = function (e) {
                    if (e.error === "not-allowed" || e.error === "permission-denied") {
                        stopListening();
                        showVoiceError("Microphone access was denied. Please enable microphone permissions in your browser settings.");
                    } else if (e.error === "no-speech") {
                        // Ignore - user may have paused
                    } else {
                        stopListening();
                        showVoiceError("Voice input error. Please try again.");
                    }
                };
            }

            var lang = getRecognitionLang();
            recognition.lang = lang;
            if (langLabel) langLabel.textContent = getLangLabel(lang);
            recognition.start();
            isListening = true;
            setListeningUI(true);
        } catch (err) {
            showVoiceError("Could not start voice input. Please check microphone permissions.");
        }
    }

    function stopListening() {
        isListening = false;
        if (recognition) {
            try { recognition.stop(); } catch (e) {}
        }
        setListeningUI(false);
    }

    function setListeningUI(listening) {
        var btn = document.getElementById("voice-input-btn");
        var icon = document.getElementById("voice-icon");
        var dot = document.getElementById("voice-listening-dot");
        var status = document.getElementById("voice-status");
        if (btn) btn.classList.toggle("ring-2", listening);
        if (btn) btn.classList.toggle("ring-red-400", listening);
        if (icon) icon.classList.toggle("hidden", listening);
        if (dot) dot.classList.toggle("hidden", !listening);
        if (status) status.classList.toggle("hidden", !listening);
    }

    function showVoiceError(msg) {
        var toast = document.getElementById("voice-error-toast");
        if (toast) {
            toast.textContent = msg;
            toast.classList.remove("hidden", "opacity-0");
            toast.classList.add("opacity-100");
            setTimeout(function () {
                toast.classList.add("opacity-0");
                setTimeout(function () { toast.classList.add("hidden"); }, 300);
            }, 4000);
        } else {
            alert(msg);
        }
    }

    MG.initVoiceInput = function () {
        var btn = document.getElementById("voice-input-btn");
        var cb = document.getElementById("voice-auto-submit");
        if (!btn) return;
        if (!isSupported()) {
            btn.setAttribute("title", "Voice input requires Chrome or Edge");
        }
        var autoSubmit = false;
        try {
            autoSubmit = localStorage.getItem("mediguideVoiceAutoSubmit") === "1";
        } catch (e) {}
        state.voiceAutoSubmit = autoSubmit;
        if (cb) {
            cb.checked = autoSubmit;
            cb.addEventListener("change", function () {
                state.voiceAutoSubmit = this.checked;
                try { localStorage.setItem("mediguideVoiceAutoSubmit", this.checked ? "1" : "0"); } catch (e) {}
            });
        }
    };

    MG.voiceAutoSubmitEnabled = function () {
        return !!state.voiceAutoSubmit;
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", MG.initVoiceInput);
    } else {
        MG.initVoiceInput();
    }
})();
