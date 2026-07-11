document.addEventListener('DOMContentLoaded', function () {

    const tableBody      = document.getElementById('closedDatesTableBody');
    const archiveList    = document.getElementById('closedDatesArchiveList');
    const toggleArchiveBtn = document.getElementById('toggleArchiveBtn');
    const newDateInput   = document.getElementById('newClosedDate');
    const newReasonInput = document.getElementById('newClosedReason');
    const addBtn         = document.getElementById('addClosedDateBtn');
    const errorEl        = document.getElementById('closedDateError');

    let archiveLoaded = false;

    function formatDisplayDate(isoDate) {
        return new Date(isoDate + 'T00:00:00').toLocaleDateString('en-GB', {
            weekday: 'short', day: 'numeric', month: 'long', year: 'numeric',
        });
    }

    function renderRows(target, closedDates, emptyMessage) {
        if (!closedDates.length) {
            target.innerHTML = `<li class="dash-closed-date-row__empty">${esc(emptyMessage)}</li>`;
            return;
        }

        target.innerHTML = closedDates.map(c => `
            <li class="dash-closed-date-row" data-id="${c.id}">
                <span class="dash-closed-date-row__info">
                    <span class="dash-closed-date-row__date">${esc(formatDisplayDate(c.date))}</span>
                    ${c.reason ? `<span class="dash-closed-date-row__reason"> — ${esc(c.reason)}</span>` : ''}
                </span>
                <button class="btn btn--ghost btn--sm dash-closed-date-delete" data-id="${c.id}">Remove</button>
            </li>`).join('');

        target.querySelectorAll('.dash-closed-date-delete').forEach(btn => {
            btn.addEventListener('click', () => deleteClosedDate(parseInt(btn.dataset.id)));
        });
    }

    function loadClosedDates() {
        fetch(DASHBOARD_URLS.closedDatesData)
            .then(r => r.json())
            .then(data => renderRows(tableBody, data.closed_dates, 'No closed dates added yet.'));
    }

    function loadArchive() {
        archiveList.innerHTML = '<li class="dash-closed-date-row__empty">Loading…</li>';
        fetch(DASHBOARD_URLS.closedDatesArchiveData)
            .then(r => r.json())
            .then(data => renderRows(archiveList, data.closed_dates, 'No past closed dates on record.'));
    }

    function deleteClosedDate(id) {
        if (!confirm('Remove this closed date? Clients will be able to book on this day again.')) return;

        fetch(DASHBOARD_URLS.closedDateDelete.replace('{id}', id), {
            method: 'POST',
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                showToast('Closed date removed.');
                loadClosedDates();
                if (archiveLoaded) loadArchive();
            }
        });
    }

    toggleArchiveBtn.addEventListener('click', () => {
        const isHidden = archiveList.style.display === 'none';
        archiveList.style.display = isHidden ? 'block' : 'none';
        toggleArchiveBtn.textContent = isHidden ? 'Hide Past Closed Dates' : 'View Past Closed Dates';

        if (isHidden && !archiveLoaded) {
            archiveLoaded = true;
            loadArchive();
        }
    });

    addBtn.addEventListener('click', () => {
        errorEl.textContent = '';
        const date   = newDateInput.value;
        const reason = newReasonInput.value.trim();

        if (!date) {
            errorEl.textContent = 'Please select a date.';
            return;
        }

        fetch(DASHBOARD_URLS.closedDateCreate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify({ date, reason }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                newDateInput.value   = '';
                newReasonInput.value = '';
                showToast('Closed date added.');
                loadClosedDates();
            } else {
                errorEl.textContent = Object.values(data.errors || {})[0] || 'Something went wrong.';
            }
        });
    });

    loadClosedDates();
});
