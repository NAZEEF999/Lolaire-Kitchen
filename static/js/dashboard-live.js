/**
 * Lightweight polling for new orders — no Channels/Redis/Celery,
 * per the brief's "reliability and simplicity over infrastructure"
 * instruction. Polls dashboard:live_updates every POLL_INTERVAL_MS;
 * that endpoint already filters everything by the viewer's Staff
 * Access permissions server-side, so this script never has to make
 * its own permission decisions — it only renders what it's given.
 *
 * Preferences (mute, last-seen order id) are stored in localStorage,
 * scoped to this browser — there's no per-account preference model
 * in the project to persist them to server-side, and adding one just
 * for a boolean felt like exactly the kind of unnecessary new table
 * the brief said to avoid.
 */
(function () {
    "use strict";

    const POLL_INTERVAL_MS = 20000;
    const LAST_ORDER_KEY = "lolaire_last_order_id";
    const MUTED_KEY = "lolaire_notif_muted";
    const LIVE_UPDATES_URL = "/dashboard/live-updates/";
    const SOUND_URL = "/static/audio/new-order.wav";

    const bellBtn = document.getElementById("notif-bell-btn");
    const bellCount = document.getElementById("notif-bell-count");
    const bellPanel = document.getElementById("notif-bell-panel");
    const bellList = document.getElementById("notif-bell-list");
    const bellEmpty = document.getElementById("notif-bell-empty");
    const toastContainer = document.getElementById("notif-toast-container");
    const muteToggle = document.getElementById("notif-mute-toggle");
    const muteIconOn = document.getElementById("notif-mute-icon-on");
    const muteIconOff = document.getElementById("notif-mute-icon-off");
    const recoveryBadge = document.getElementById("pending-recovery-badge");

    if (!bellBtn) return; // Not authenticated / navbar not present on this page.

    let unseenCount = 0;
    let audioUnlocked = false;
    let audioEl = null;

    function isMuted() {
        return localStorage.getItem(MUTED_KEY) === "true";
    }

    function setMuted(muted) {
        localStorage.setItem(MUTED_KEY, muted ? "true" : "false");
        muteIconOn.classList.toggle("hidden", muted);
        muteIconOff.classList.toggle("hidden", !muted);
    }

    function unlockAudio() {
        if (audioUnlocked) return;
        audioUnlocked = true;
        try {
            audioEl = new Audio(SOUND_URL);
            audioEl.volume = 0.5;
            // Priming play/pause on the first real user gesture — browsers
            // allow this because it happens inside a genuine click/keydown
            // handler, and afterwards .play() from the poll callback (which
            // isn't itself a user gesture) is allowed to proceed.
            const primePromise = audioEl.play();
            if (primePromise && primePromise.then) {
                primePromise.then(() => audioEl.pause()).catch(() => {});
            }
        } catch (e) {
            // Autoplay/audio blocked entirely — degrade gracefully, no sound, no crash.
        }
    }
    document.addEventListener("click", unlockAudio, { once: true });
    document.addEventListener("keydown", unlockAudio, { once: true });

    function playChime() {
        if (isMuted() || !audioUnlocked || !audioEl) return;
        try {
            audioEl.currentTime = 0;
            const p = audioEl.play();
            if (p && p.catch) p.catch(() => {});
        } catch (e) {
            // Ignore — a missed chime is not worth surfacing an error over.
        }
    }

    function orderSummaryText(order) {
        // total_amount is only present in the payload when the viewer
        // has payments:view (see dashboard.views.live_updates) — must
        // not assume it's always there.
        const items = order.item_count + " item" + (order.item_count === 1 ? "" : "s");
        if (order.total_amount === undefined || order.total_amount === null) return items;
        return items + " · \u20A6" + Number(order.total_amount).toLocaleString();
    }

    function showToast(order) {
        const toast = document.createElement("div");
        toast.className = "notif-toast bg-white border border-hairline shadow-lg rounded-lg p-4 cursor-pointer";
        toast.innerHTML =
            '<div class="flex items-start gap-3">' +
            '<span class="status-dot status-dot-warning mt-1.5"></span>' +
            '<div class="min-w-0">' +
            '<p class="text-sm font-semibold">New Order #' + escapeHtml(order.order_number) + "</p>" +
            '<p class="text-xs text-inksoft mt-0.5">' + orderSummaryText(order) + "</p>" +
            '<p class="text-[0.7rem] text-inksoft mt-1">Just now</p>' +
            "</div></div>";
        toast.addEventListener("click", function () {
            window.location.href = order.url;
        });
        toastContainer.appendChild(toast);
        setTimeout(function () {
            toast.style.transition = "opacity 0.3s ease";
            toast.style.opacity = "0";
            setTimeout(function () { toast.remove(); }, 300);
        }, 8000);
    }

    function addToBell(order) {
        bellEmpty.classList.add("hidden");
        const row = document.createElement("a");
        row.href = order.url;
        row.className = "block px-4 py-3 border-b border-hairline hover:bg-appbg text-sm";
        row.innerHTML =
            '<div class="flex items-center gap-2">' +
            '<span class="status-dot status-dot-warning"></span>' +
            '<span class="font-medium">New Order #' + escapeHtml(order.order_number) + "</span></div>" +
            '<p class="text-xs text-inksoft mt-0.5 pl-4">' + orderSummaryText(order) + "</p>";
        bellList.prepend(row);
        unseenCount += 1;
        bellCount.textContent = String(unseenCount);
        bellCount.classList.remove("hidden");
        bellCount.classList.add("flex");
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    bellBtn.addEventListener("click", function () {
        bellPanel.classList.toggle("hidden");
        if (!bellPanel.classList.contains("hidden")) {
            unseenCount = 0;
            bellCount.classList.add("hidden");
            bellCount.classList.remove("flex");
        }
    });
    document.addEventListener("click", function (e) {
        if (bellPanel && !bellPanel.classList.contains("hidden") && !bellPanel.contains(e.target) && !bellBtn.contains(e.target)) {
            bellPanel.classList.add("hidden");
        }
    });

    if (muteToggle) {
        setMuted(isMuted());
        muteToggle.addEventListener("click", function () {
            setMuted(!isMuted());
        });
    }

    // Quick Actions and profile menu — same open/close-on-outside-click
    // pattern as the notification bell above, just two more toggleable panels.
    function wireDropdown(btnId, panelId) {
        var btn = document.getElementById(btnId);
        var panel = document.getElementById(panelId);
        if (!btn || !panel) return;
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            panel.classList.toggle("hidden");
        });
        document.addEventListener("click", function (e) {
            if (!panel.classList.contains("hidden") && !panel.contains(e.target) && !btn.contains(e.target)) {
                panel.classList.add("hidden");
            }
        });
    }
    wireDropdown("quick-actions-btn", "quick-actions-panel");
    wireDropdown("profile-menu-btn", "profile-menu-panel");

    function poll() {
        const lastSeenRaw = localStorage.getItem(LAST_ORDER_KEY);
        const firstEverLoad = lastSeenRaw === null;
        const since = firstEverLoad ? 0 : parseInt(lastSeenRaw, 10);

        fetch(LIVE_UPDATES_URL + "?since=" + since, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (res) { return res.ok ? res.json() : null; })
            .then(function (data) {
                if (!data) return;

                if (firstEverLoad) {
                    // Baseline only — never notify about orders that already
                    // existed before this browser started watching.
                    localStorage.setItem(LAST_ORDER_KEY, String(data.latest_order_id || 0));
                } else if (data.new_orders && data.new_orders.length) {
                    data.new_orders.forEach(function (order) {
                        showToast(order);
                        addToBell(order);
                    });
                    playChime();
                    localStorage.setItem(LAST_ORDER_KEY, String(data.latest_order_id || since));
                } else if (data.latest_order_id) {
                    localStorage.setItem(LAST_ORDER_KEY, String(data.latest_order_id));
                }

                if (recoveryBadge && data.pending_recovery_count !== null && data.pending_recovery_count !== undefined) {
                    recoveryBadge.textContent = String(data.pending_recovery_count);
                    recoveryBadge.classList.toggle("hidden", data.pending_recovery_count === 0);
                }
            })
            .catch(function () {
                // Network hiccup — try again on the next interval, no need to surface this to the user.
            });
    }

    poll();
    setInterval(poll, POLL_INTERVAL_MS);
})();
