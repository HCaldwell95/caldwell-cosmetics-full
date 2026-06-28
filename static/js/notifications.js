document.addEventListener('DOMContentLoaded', function () {

    const notifList  = document.getElementById('notifList');
    const markAllBtn = document.getElementById('markAllReadBtn');
    let notifications = [];

    function esc(s) {
        return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function showToast(msg) {
        const t = document.getElementById('dashToast');
        if (!t) return;
        t.textContent = msg;
        t.classList.add('dash-toast--show');
        setTimeout(() => t.classList.remove('dash-toast--show'), 3000);
    }

    function updateSidebarBadge() {
        const badge = document.getElementById('notifBadge');
        if (!badge) return;
        const count = notifications.filter(n => !n.is_read).length;
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'inline-flex';
        } else {
            badge.style.display = 'none';
        }
    }

    function renderList() {
        if (!notifications.length) {
            notifList.innerHTML = '<p class="notif-empty">No notifications yet. They\'ll appear here when clients complete consent forms.</p>';
            return;
        }

        notifList.innerHTML = notifications.map(n => `
            <div class="notif-item${n.is_read ? '' : ' notif-item--unread'}" data-id="${n.id}">
                <span class="notif-dot" aria-hidden="true"></span>
                <div class="notif-item__body">
                    <p class="notif-item__message">${esc(n.message)}</p>
                    <p class="notif-item__meta">${esc(n.created_at)}</p>
                </div>
                <a href="${esc(n.form_url)}" target="_blank" rel="noopener" class="notif-item__action btn btn--ghost btn--sm">${esc(n.action_label)}</a>
            </div>
        `).join('');

        notifList.querySelectorAll('.notif-item').forEach(function (el) {
            el.addEventListener('click', function (e) {
                if (e.target.closest('.notif-item__action')) return;
                markRead(parseInt(el.dataset.id, 10));
            });
        });
    }

    function markRead(id) {
        const url = NOTIF_URLS.markRead.replace('{id}', id);
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.ok) {
                const n = notifications.find(function (x) { return x.id === id; });
                if (n) n.is_read = true;
                renderList();
                updateSidebarBadge();
            }
        })
        .catch(function () {});
    }

    markAllBtn.addEventListener('click', function () {
        fetch(NOTIF_URLS.markAll, {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.ok) {
                notifications.forEach(function (n) { n.is_read = true; });
                renderList();
                updateSidebarBadge();
                showToast('All notifications marked as read.');
            }
        })
        .catch(function () {});
    });

    fetch(NOTIF_URLS.data)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            notifications = data.notifications;
            renderList();
            updateSidebarBadge();
        })
        .catch(function () {
            notifList.innerHTML = '<p class="notif-empty">Failed to load notifications.</p>';
        });
});
