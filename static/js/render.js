/**
 * MediGuide AI — DOM rendering: messages, meta, loading, utilities.
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.state) return;
    var state = MG.state;
    var icons = MG.FEATURE_ICONS || {};
    var langLabels = MG.LANGUAGE_LABELS || {};

    function escapeHtml(text) {
        var div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function formatMarkdown(text) {
        var html = escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        html = html.replace(/^### (.+)$/gm, '<h4 class="font-semibold text-gray-900 mt-3 mb-1">$1</h4>');
        html = html.replace(/^## (.+)$/gm, '<h3 class="font-bold text-gray-900 mt-4 mb-1 text-base">$1</h3>');
        html = html.replace(/^[-•] (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
        html = html.replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal">$1. $2</li>');
        html = html.replace(/((?:<li[^>]*>.*?<\/li>\n?)+)/g, '<ul class="my-2 space-y-1">$1</ul>');
        html = html.replace(/\n\n/g, "</p><p class='mt-2'>");
        html = html.replace(/\n/g, "<br>");
        return "<p>" + html + "</p>";
    }

    function renderAiMeta(meta) {
        if (!meta) return "";
        var model = meta.model || "Azure OpenAI";
        var lang = meta.language || state.currentLanguage || "en";
        var pretty = langLabels[lang] || lang;
        return (
            '<div class="mt-3 pt-2 border-t border-gray-100 flex flex-wrap items-center gap-3 text-[11px] text-gray-400">' +
            '<span class="inline-flex items-center gap-1"><i class="fas fa-microchip"></i><span>' + model + "</span></span>" +
            '<span class="inline-flex items-center gap-1"><i class="fas fa-language"></i><span>' + pretty + "</span></span>" +
            '<span class="inline-flex items-center gap-1"><i class="fas fa-shield-heart"></i><span>AI guidance only — not medical advice</span></span>' +
            "</div>"
        );
    }

    function renderSafetyMeta(safety) {
        if (!safety || typeof safety.maxSeverity === "undefined") return "";
        var level = safety.maxSeverity || 0;
        var label = "Safe";
        var colour = "text-emerald-600";
        if (level >= 6) { label = "High risk content (filtered)"; colour = "text-red-600"; }
        else if (level >= 4) { label = "Medium risk content"; colour = "text-amber-600"; }
        else if (level >= 2) { label = "Low risk content"; colour = "text-yellow-600"; }
        return '<div class="mt-1 text-[11px] ' + colour + '"><i class="fas fa-shield-alt"></i><span>' + label + "</span></div>";
    }

    function renderReportButton(meta, replyText) {
        if (!meta) return "";
        var feature = (meta.feature || state.currentFeature).replace(/'/g, "");
        var safety = meta.safety || {};
        var escaped = encodeURIComponent(replyText || "");
        var safetyEnc = encodeURIComponent(JSON.stringify(safety));
        return (
            '<div class="mt-2 text-[11px] text-gray-400 flex items-center justify-between">' +
            '<button type="button" class="inline-flex items-center gap-1 hover:text-red-600" ' +
            'onclick="MediGuide.reportAnswer(\'' + feature + "', decodeURIComponent('" + escaped + "'), '" + safetyEnc + "')\">" +
            '<i class="fas fa-flag"></i><span>Report this answer</span></button></div>'
        );
    }

    MG.addMessage = function (content, role, icon, meta, options) {
        options = options || {};
        var feature = options.feature !== undefined ? options.feature : state.currentFeature;
        var record = options.record !== false;

        var chatArea = document.getElementById("chat-area");
        var welcome = document.getElementById("welcome-message");
        if (welcome) welcome.style.display = "none";

        var wrapper = document.createElement("div");
        wrapper.className = "flex gap-3 " + (role === "user" ? "justify-end" : "justify-start") + " message-enter";

        if (role === "user") {
            wrapper.innerHTML =
                '<div class="max-w-2xl"><div class="bg-gradient-to-r from-mg-start to-mg-end text-white px-4 py-3 rounded-2xl rounded-tr-md text-sm leading-relaxed shadow-sm">' +
                escapeHtml(content) +
                '</div></div><div class="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center shrink-0 mt-1">' +
                '<i class="fas fa-user text-gray-600 text-xs"></i></div>';
        } else {
            var aiIcon = icon || icons[feature] || "fa-heartbeat";
            var safety = meta && meta.safety ? meta.safety : null;
            wrapper.innerHTML =
                '<div class="w-16 h-16 rounded-full flex items-center justify-center shrink-0 mt-1 overflow-hidden">' +
                '<img src="/static/images/robot.png" alt="MediGuide AI" class="w-full h-full object-cover">' +
                "</div>" +
                '<div class="max-w-4xl"><div class="bg-white text-sm leading-relaxed text-gray-700 ai-response">' +
                formatMarkdown(content) + renderAiMeta(meta) + renderSafetyMeta(safety) + renderReportButton(meta, content) +
                "</div></div>";
        }

        chatArea.appendChild(wrapper);
        chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: "smooth" });

        if (record) {
            state.messageLog.push({ role: role, content: content, meta: meta || null, feature: feature });
            if (MG.persistSession) MG.persistSession();
        }
        return wrapper;
    };

    MG.addLoadingMessage = function () {
        var chatArea = document.getElementById("chat-area");
        var wrapper = document.createElement("div");
        wrapper.className = "flex gap-3 justify-start message-enter";
        wrapper.id = "loading-message";
        wrapper.innerHTML =
            '<div class="w-16 h-16 rounded-full flex items-center justify-center shrink-0 mt-1 overflow-hidden">' +
            '<img src="/static/images/robot.png" alt="MediGuide AI" class="w-full h-full object-cover"></div>' +
            '<div class="bg-white border border-gray-200 px-5 py-4 rounded-2xl rounded-tl-md shadow-sm flex items-center gap-3">' +
            '<div class="loading-dots flex gap-1">' +
            '<span class="w-2 h-2 bg-teal-400 rounded-full"></span><span class="w-2 h-2 bg-teal-400 rounded-full"></span>' +
            '<span class="w-2 h-2 bg-teal-400 rounded-full"></span></div>' +
            '<span class="text-sm text-gray-500">MediGuide is typing...</span></div>';
        chatArea.appendChild(wrapper);
        chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: "smooth" });
    };

    MG.removeLoadingMessage = function () {
        var el = document.getElementById("loading-message");
        if (el) el.remove();
    };
})();
