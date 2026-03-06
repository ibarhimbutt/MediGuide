/**
 * MediGuide AI — Detect user location for area-based doctor recommendations.
 * Uses IP-based geolocation (no permission) with optional precise browser geolocation.
 */
(function () {
    "use strict";
    var MG = window.MediGuide;
    if (!MG || !MG.state) return;
    var state = MG.state;

    function formatLocation(data) {
        if (!data) return null;
        var city = data.city || data.city_name;
        var region = data.regionName || data.region || data.state;
        var country = data.country || data.country_name;
        if (!city && !region && !country) return null;
        var parts = [];
        if (city) parts.push(city);
        if (region && region !== city) parts.push(region);
        if (country) parts.push(country);
        return parts.length ? parts.join(", ") : null;
    }

    MG.detectLocation = function (cb) {
        if (state.userLocation && typeof cb === "function") {
            cb(state.userLocation);
            return;
        }
        var done = function (locationString, locData) {
            if (locationString) {
                state.userLocation = locationString;
                state.userCity = (locData && locData.city) || null;
                state.userState = (locData && (locData.region || locData.state)) || null;
                state.userCountry = (locData && (locData.country || locData.country_name)) || null;
                try {
                    localStorage.setItem("mediguideLocation", locationString);
                    if (locData) localStorage.setItem("mediguideLocationData", JSON.stringify({ city: state.userCity, state: state.userState, country: state.userCountry }));
                } catch (e) {}
            }
            if (typeof cb === "function") cb(locationString);
        };
        fetch("/api/location")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var loc = data.location || formatLocation(data);
                if (loc) return done(loc, data);
                throw new Error("No location");
            })
            .catch(function () {
                return fetch("https://ipapi.co/json/")
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        var loc = formatLocation(data);
                        if (loc) return done(loc, data);
                        throw new Error("No location");
                    });
            })
            .catch(function () {
                try {
                    var saved = localStorage.getItem("mediguideLocation");
                    if (saved) state.userLocation = saved;
                } catch (e) {}
                done(state.userLocation || null);
            });
    };

    MG.refreshLocation = function (cb) {
        state.userLocation = null;
        MG.detectLocation(cb);
    };

    function init() {
        try {
            var saved = localStorage.getItem("mediguideLocation");
            if (saved) state.userLocation = saved;
            var savedData = localStorage.getItem("mediguideLocationData");
            if (savedData) {
                try {
                    var d = JSON.parse(savedData);
                    state.userCity = d.city || null;
                    state.userState = d.state || null;
                    state.userCountry = d.country || null;
                } catch (e) {}
            }
        } catch (e) {}
        MG.detectLocation(function (loc) {
            var wrap = document.getElementById("user-location-display");
            var text = document.getElementById("user-location-text");
            if (wrap && text && loc) {
                text.textContent = loc;
                wrap.classList.remove("hidden");
                wrap.classList.add("flex");
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
