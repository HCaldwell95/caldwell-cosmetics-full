document.addEventListener('DOMContentLoaded', function () {

    const tableBody      = document.getElementById('closedDatesTableBody');
    const newDateInput   = document.getElementById('newClosedDate');
    const newReasonInput = document.getElementById('newClosedReason');
    const addBtn         = document.getElementById('addClosedDateBtn');
    const errorEl        = document.getElementById('closedDateError');

    function formatDisplayDate(isoDate) {
        return new Date(isoDate + 'T00:00:00').toLocaleDateString('en-GB', {
            weekday: 'short', day: 'numeric', month: 'long', year: 'numeric',
        });
    }

    function renderRows(closedDates) {
        if (!closedDates.length) {
            tableBody.innerHTML = '<tr><td colspan="3" class="dash-client-table__empty">No closed dates added yet.</td></tr>';
            return;
        }

        tableBody.innerHTML = closedDates.map(c => `
            <tr data-id="${c.id}">
                <td>${esc(formatDisplayDate(c.date))}</td>
                <td>${esc(c.reason) || '—'}</td>
                <td>
                    <button class="dash-client-view-btn dash-closed-date-delete" data-id="${c.id}">Remove</button>
                </td>
            </tr>`).join('');

        tableBody.querySelectorAll('.dash-closed-date-delete').forEach(btn => {
            btn.addEventListener('click', () => deleteClosedDate(parseInt(btn.dataset.id)));
        });
    }

    function loadClosedDates() {
        fetch(DASHBOARD_URLS.closedDatesData)
            .then(r => r.json())
            .then(data => renderRows(data.closed_dates));
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
            }
        });
    }

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
