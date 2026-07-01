document.addEventListener('DOMContentLoaded', function () {

    // ---------------------------------------------------------------
    // Elements
    // ---------------------------------------------------------------

    const clientSearchBar  = document.getElementById('clientSearchBar');
    const clientTableBody  = document.getElementById('clientTableBody');
    const addClientBtn     = document.getElementById('addClientBtn');
    const addClientOverlay = document.getElementById('addClientOverlay');
    const addClientClose   = document.getElementById('addClientClose');
    const addClientCancel  = document.getElementById('addClientCancel');
    const addClientSave    = document.getElementById('addClientSave');

    // ---------------------------------------------------------------
    // Client list — with sort + filter
    // ---------------------------------------------------------------

    const clientFilterPhone = document.getElementById('clientFilterPhone');
    const clientCount       = document.getElementById('clientCount');

    let allClients         = [];
    let clientSearchTimeout = null;
    let sortCol            = 'last_name';
    let sortDir            = 'asc';

    function esc(s) {
        return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function applyFilterAndSort() {
        const phoneFilter = clientFilterPhone ? clientFilterPhone.value : '';

        let rows = allClients.slice();

        // Filter
        if (phoneFilter === 'has_phone') {
            rows = rows.filter(c => c.phone);
        } else if (phoneFilter === 'no_phone') {
            rows = rows.filter(c => !c.phone);
        }

        // Sort
        rows.sort((a, b) => {
            let av = (a[sortCol] ?? '').toLowerCase();
            let bv = (b[sortCol] ?? '').toLowerCase();
            if (sortCol === 'last_name') {
                // Secondary sort by first name
                const cmp = av.localeCompare(bv);
                if (cmp !== 0) return sortDir === 'asc' ? cmp : -cmp;
                const af = (a.first_name ?? '').toLowerCase();
                const bf = (b.first_name ?? '').toLowerCase();
                return sortDir === 'asc' ? af.localeCompare(bf) : bf.localeCompare(af);
            }
            const cmp = av.localeCompare(bv);
            return sortDir === 'asc' ? cmp : -cmp;
        });

        renderRows(rows);
        updateSortIcons();
    }

    function renderRows(rows) {
        if (clientCount) {
            clientCount.textContent = rows.length === 1 ? '1 client' : `${rows.length} clients`;
        }

        if (!rows.length) {
            clientTableBody.innerHTML = '<tr><td colspan="5" class="dash-client-table__empty">No clients found.</td></tr>';
            return;
        }

        clientTableBody.innerHTML = rows.map(c => `
            <tr class="dash-client-row" data-id="${c.id}">
                <td class="dash-client-name">${esc(c.name)}</td>
                <td>${esc(c.email)}</td>
                <td>${esc(c.phone) || '—'}</td>
                <td>${esc(c.joined)}</td>
                <td>
                    <button class="dash-client-view-btn" data-id="${c.id}">
                        <span class="dash-client-view-btn__full">View Profile</span>
                        <span class="dash-client-view-btn__short">View</span>
                    </button>
                </td>
            </tr>`).join('');

        clientTableBody.querySelectorAll('.dash-client-view-btn').forEach(btn => {
            btn.addEventListener('click', () => openProfilePanel(parseInt(btn.dataset.id)));
        });
    }

    function updateSortIcons() {
        document.querySelectorAll('.dash-sort-icon').forEach(icon => {
            const col = icon.dataset.col;
            if (col === sortCol) {
                icon.textContent = sortDir === 'asc' ? ' ▲' : ' ▼';
                icon.classList.add('dash-sort-icon--active');
            } else {
                icon.textContent = '';
                icon.classList.remove('dash-sort-icon--active');
            }
        });
        document.querySelectorAll('.dash-th-sortable').forEach(th => {
            th.classList.toggle('dash-th-sortable--active', th.dataset.col === sortCol);
        });
    }

    // Sortable column headers
    document.querySelectorAll('.dash-th-sortable').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.col;
            if (col === sortCol) {
                sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                sortCol = col;
                sortDir = col === 'joined_iso' ? 'desc' : 'asc';
            }
            applyFilterAndSort();
        });
    });

    // Filter change
    if (clientFilterPhone) {
        clientFilterPhone.addEventListener('change', applyFilterAndSort);
    }

    function loadClients(q) {
        const url = q
            ? `${DASHBOARD_URLS.clientList}?q=${encodeURIComponent(q)}`
            : DASHBOARD_URLS.clientList;

        fetch(url)
            .then(r => r.json())
            .then(data => {
                allClients = data.clients || [];
                applyFilterAndSort();
            });
    }

    clientSearchBar.addEventListener('input', function () {
        clearTimeout(clientSearchTimeout);
        clientSearchTimeout = setTimeout(() => loadClients(this.value.trim()), 300);
    });

    loadClients('');

    // ---------------------------------------------------------------
    // Add client modal
    // ---------------------------------------------------------------

    function openAddClientModal() {
        ['newFirstName','newLastName','newEmail','newPhone',
         'newPassword','newPasswordConfirm','newDob',
         'newAddress1','newAddress2','newTownCity','newPostcode',
         'newMedicalNotes'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const skinEl = document.getElementById('newSkinType');
        if (skinEl) skinEl.value = '';
        document.getElementById('addClientError').textContent = '';
        addClientOverlay.style.display = 'flex';
        document.body.style.overflow   = 'hidden';
        setTimeout(() => document.getElementById('newFirstName').focus(), 50);
    }

    function closeAddClientModal() {
        addClientOverlay.style.display = 'none';
        document.body.style.overflow   = '';
    }

    addClientBtn.addEventListener('click', openAddClientModal);
    addClientClose.addEventListener('click', closeAddClientModal);
    addClientCancel.addEventListener('click', closeAddClientModal);
    addClientOverlay.addEventListener('click', function (e) {
        if (e.target === addClientOverlay) closeAddClientModal();
    });

    addClientSave.addEventListener('click', function () {
        const firstName = document.getElementById('newFirstName').value.trim();
        const lastName  = document.getElementById('newLastName').value.trim();
        const email     = document.getElementById('newEmail').value.trim();
        const phone     = document.getElementById('newPhone').value.trim();
        const password  = document.getElementById('newPassword').value;
        const confirm   = document.getElementById('newPasswordConfirm').value;
        const errEl     = document.getElementById('addClientError');
        errEl.textContent = '';

        if (!email)    { errEl.textContent = 'Email address is required.'; return; }
        if (!password) { errEl.textContent = 'Password is required.'; return; }
        if (password.length < 8) { errEl.textContent = 'Password must be at least 8 characters.'; return; }
        if (password !== confirm) { errEl.textContent = 'Passwords do not match.'; return; }

        addClientSave.disabled    = true;
        addClientSave.textContent = 'Creating…';

        fetch(DASHBOARD_URLS.clientCreate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify({
                first_name:    firstName,
                last_name:     lastName,
                email:         email,
                phone:         phone,
                password:      password,
                dob:           document.getElementById('newDob').value          || '',
                skin_type:     document.getElementById('newSkinType').value     || '',
                address_line_1: document.getElementById('newAddress1').value.trim()  || '',
                address_line_2: document.getElementById('newAddress2').value.trim()  || '',
                town_city:     document.getElementById('newTownCity').value.trim()   || '',
                postcode:      document.getElementById('newPostcode').value.trim()   || '',
                medical_notes: document.getElementById('newMedicalNotes').value.trim() || '',
            }),
        })
        .then(r => r.json())
        .then(data => {
            addClientSave.disabled    = false;
            addClientSave.textContent = 'Create Client';
            if (data.ok) {
                closeAddClientModal();
                showToast('Client "' + (data.name || data.email) + '" created successfully.');
                loadClients(clientSearchBar.value.trim());
                openProfilePanel(data.id);
            } else {
                errEl.textContent = data.error || 'Something went wrong.';
            }
        })
        .catch(function () {
            addClientSave.disabled    = false;
            addClientSave.textContent = 'Create Client';
            document.getElementById('addClientError').textContent = 'Network error — please try again.';
        });
    });
});
