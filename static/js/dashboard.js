document.addEventListener('DOMContentLoaded', function () {

    // ---------------------------------------------------------------
    // State
    // ---------------------------------------------------------------

    let currentView    = 'month';
    let currentDate    = new Date();
    let allEvents      = [];
    let activeBooking  = null;
    let selectedUserId = null;
    let isEditMode     = false;
    let activePanelUserId = null;

    // ---------------------------------------------------------------
    // Elements — calendar
    // ---------------------------------------------------------------

    const calendar      = document.getElementById('dashCalendar');
    const periodLabel   = document.getElementById('calPeriodLabel');
    const prevBtn       = document.getElementById('calPrev');
    const nextBtn       = document.getElementById('calNext');
    const todayBtn      = document.getElementById('calToday');
    const viewBtns      = document.querySelectorAll('.dash-view-btn');
    const newBookingBtn = document.getElementById('newBookingBtn');

    // Elements — booking modal
    const modalOverlay     = document.getElementById('modalOverlay');
    const modalClose       = document.getElementById('modalClose');
    const modalView        = document.getElementById('modalView');
    const modalForm        = document.getElementById('modalForm');
    const modalTitle       = document.getElementById('modalTitle');
    const editBookingBtn   = document.getElementById('editBookingBtn');
    const cancelBookingBtn = document.getElementById('cancelBookingBtn');
    const viewProfileBtn   = document.getElementById('viewProfileBtn');
    const formSaveBtn      = document.getElementById('formSaveBtn');
    const formCancelBtn    = document.getElementById('formCancelBtn');
    const clientSearch     = document.getElementById('clientSearch');
    const clientResults    = document.getElementById('clientResults');
    const selectedClientLabel = document.getElementById('selectedClientLabel');
    const formTreatment    = document.getElementById('formTreatment');
    const formDate         = document.getElementById('formDate');
    const formTime         = document.getElementById('formTime');
    const formNotes        = document.getElementById('formNotes');
    const formStatus       = document.getElementById('formStatus');
    const statusGroup      = document.getElementById('statusGroup');
    const clientSearchGroup = document.getElementById('clientSearchGroup');

    // Elements — profile panel
    const profileOverlay   = document.getElementById('profileOverlay');
    const profilePanel     = document.getElementById('profilePanel');
    const profileClose     = document.getElementById('profileClose');
    const profilePanelBody = document.getElementById('profilePanelBody');
    const panelName        = document.getElementById('panelName');
    const panelEmail       = document.getElementById('panelEmail');
    const panelEditBtn     = document.getElementById('panelEditBtn');

    // Elements — client list
    const clientSearchBar  = document.getElementById('clientSearchBar');
    const clientTableBody  = document.getElementById('clientTableBody');

    // Elements — bundle modal
    const bundleModalOverlay = document.getElementById('bundleModalOverlay');
    const bundleModalClose   = document.getElementById('bundleModalClose');
    const bundleModalCancel  = document.getElementById('bundleModalCancel');
    const bundleModalSave    = document.getElementById('bundleModalSave');

    // Elements — credit modal
    const creditModalOverlay = document.getElementById('creditModalOverlay');
    const creditModalClose   = document.getElementById('creditModalClose');
    const creditModalCancel  = document.getElementById('creditModalCancel');
    const creditModalSave    = document.getElementById('creditModalSave');

    // ---------------------------------------------------------------
    // Calendar — fetch & render
    // ---------------------------------------------------------------

    function getDateRange() {
        const y = currentDate.getFullYear();
        const m = currentDate.getMonth();

        if (currentView === 'month') {
            return { start: new Date(y, m, 1), end: new Date(y, m + 1, 0) };
        }

        const day   = currentDate.getDay();
        const diff  = day === 0 ? -6 : 1 - day;
        const start = new Date(currentDate);
        start.setDate(currentDate.getDate() + diff);
        start.setHours(0, 0, 0, 0);
        const end = new Date(start);
        end.setDate(start.getDate() + 6);
        return { start, end };
    }

    function formatISO(d) {
        return d.getFullYear() + '-' +
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0');
    }

    function fetchEvents() {
        const { start, end } = getDateRange();
        const url = `${DASHBOARD_URLS.bookingsData}?start=${formatISO(start)}&end=${formatISO(end)}`;
        fetch(url)
            .then(r => r.json())
            .then(data => {
                allEvents = data.events;
                updateStats();
                currentView === 'month' ? renderMonth() : renderWeek();
            });
    }

    function updateStats() {
        const today      = formatISO(new Date());
        const now        = new Date();
        const weekStart  = new Date(now);
        const wd         = now.getDay();
        weekStart.setDate(now.getDate() - (wd === 0 ? 6 : wd - 1));
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);

        const confirmed = allEvents.filter(e => e.status === 'confirmed');
        const cancelled = allEvents.filter(e => e.status === 'cancelled');

        document.querySelector('#statToday .dash-stat__value').textContent =
            confirmed.filter(e => e.date === today).length;
        document.querySelector('#statWeek .dash-stat__value').textContent =
            confirmed.filter(e => {
                const d = new Date(e.date + 'T00:00:00');
                return d >= weekStart && d <= now;
            }).length;
        document.querySelector('#statMonth .dash-stat__value').textContent =
            confirmed.filter(e => new Date(e.date + 'T00:00:00') >= monthStart).length;
        document.querySelector('#statCancelled .dash-stat__value').textContent =
            cancelled.length;
    }

    // ---------------------------------------------------------------
    // Month view
    // ---------------------------------------------------------------

    function renderMonth() {
        const y = currentDate.getFullYear();
        const m = currentDate.getMonth();

        periodLabel.textContent = new Date(y, m).toLocaleDateString('en-GB', {
            month: 'long', year: 'numeric',
        });

        const firstDay    = new Date(y, m, 1).getDay();
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        const today       = formatISO(new Date());

        const byDate = {};
        allEvents.forEach(e => { (byDate[e.date] = byDate[e.date] || []).push(e); });

        let html = '<div class="dash-month-grid">';
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].forEach(d => {
            html += `<div class="dash-month-header">${d}</div>`;
        });

        const startOffset = firstDay === 0 ? 6 : firstDay - 1;
        for (let i = 0; i < startOffset; i++) {
            html += '<div class="dash-month-cell dash-month-cell--empty"></div>';
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = formatISO(new Date(y, m, day));
            const isToday = dateStr === today;
            const events  = byDate[dateStr] || [];
            const isOpen  = OPEN_DAYS.includes(new Date(y, m, day).getDay());

            html += `
                <div class="dash-month-cell${isToday ? ' dash-month-cell--today' : ''}${!isOpen ? ' dash-month-cell--closed' : ''}" data-date="${dateStr}">
                    <span class="dash-month-cell__day">${day}</span>
                    <div class="dash-month-cell__events">
                        ${events.slice(0, 3).map(e => eventPill(e)).join('')}
                        ${events.length > 3 ? `<button class="dash-month-more" data-date="${dateStr}">+${events.length - 3} more</button>` : ''}
                    </div>
                </div>`;
        }

        html += '</div>';
        calendar.innerHTML = html;

        calendar.querySelectorAll('.dash-event-pill').forEach(pill => {
            pill.addEventListener('click', e => {
                e.stopPropagation();
                const id = parseInt(pill.dataset.id);
                openViewModal(allEvents.find(ev => ev.id === id));
            });
        });

        // "more" button — switch to week view on that date
        calendar.querySelectorAll('.dash-month-more').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                currentDate = new Date(btn.dataset.date + 'T00:00:00');
                currentView = 'week';
                viewBtns.forEach(b => b.classList.remove('dash-view-btn--active'));
                document.querySelector('[data-view="week"]').classList.add('dash-view-btn--active');
                fetchEvents();
            });
        });
    }

    function eventPill(e) {
        const cls    = e.status === 'cancelled' ? 'dash-event-pill--cancelled' : '';
        const colour = e.status === 'cancelled' ? '' : `style="background:${e.category_colour || '#b8965a'}"`;
        return `
            <div class="dash-event-pill ${cls}" ${colour} data-id="${e.id}" title="${e.client} — ${e.treatment}">
                <span class="dash-event-pill__time">${e.start_time}</span>
                <span class="dash-event-pill__name">${e.client}</span>
            </div>`;
    }

    // ---------------------------------------------------------------
    // Week view
    // ---------------------------------------------------------------

    function renderWeek() {
        const { start } = getDateRange();
        const days = [];
        for (let i = 0; i < 7; i++) {
            const d = new Date(start);
            d.setDate(start.getDate() + i);
            days.push(d);
        }

        const startLabel = days[0].toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
        const endLabel   = days[6].toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
        periodLabel.textContent = `${startLabel} – ${endLabel}`;

        const today  = formatISO(new Date());
        const byDate = {};
        allEvents.forEach(e => { (byDate[e.date] = byDate[e.date] || []).push(e); });

        const HOUR_START = 9;
        const HOUR_END   = 15;
        const HOUR_COUNT = HOUR_END - HOUR_START;
        const PX_PER_MIN = 2;

        let html = '<div class="dash-week-grid">';
        html += '<div class="dash-week-time-header"></div>';

        days.forEach(d => {
            const dateStr = formatISO(d);
            const isToday = dateStr === today;
            const isOpen  = OPEN_DAYS.includes(d.getDay());
            html += `
                <div class="dash-week-col-header${isToday ? ' dash-week-col-header--today' : ''}">
                    <span class="dash-week-col-header__day">${d.toLocaleDateString('en-GB', { weekday: 'short' })}</span>
                    <span class="dash-week-col-header__date${isToday ? ' dash-week-col-header__date--today' : ''}">${d.getDate()}</span>
                    ${!isOpen ? '<span class="dash-week-closed">Closed</span>' : ''}
                </div>`;
        });

        html += '<div class="dash-week-body"><div class="dash-week-gutter">';
        for (let h = HOUR_START; h < HOUR_END; h++) {
            html += `<div class="dash-week-gutter__hour" style="height:${60 * PX_PER_MIN}px">${String(h).padStart(2,'0')}:00</div>`;
        }
        html += '</div>';

        days.forEach(d => {
            const dateStr = formatISO(d);
            const events  = (byDate[dateStr] || []).sort((a, b) => a.start_time.localeCompare(b.start_time));

            html += `<div class="dash-week-col" data-date="${dateStr}" style="height:${HOUR_COUNT * 60 * PX_PER_MIN}px">`;
            for (let h = 0; h < HOUR_COUNT; h++) {
                html += `<div class="dash-week-hour-line" style="top:${h * 60 * PX_PER_MIN}px"></div>`;
            }
            events.forEach(e => {
                const [eh, em] = e.start_time.split(':').map(Number);
                const topMins  = (eh - HOUR_START) * 60 + em;
                const height   = e.duration * PX_PER_MIN;
                const colour = e.status === 'cancelled' ? '' : `background:${e.category_colour || '#b8965a'};`;
                html += `
                    <div class="dash-week-event${e.status === 'cancelled' ? ' dash-week-event--cancelled' : ''}"
                         data-id="${e.id}" style="${colour}top:${topMins * PX_PER_MIN}px; height:${height}px;">
                        <span class="dash-week-event__time">${e.start_time}</span>
                        <span class="dash-week-event__name">${e.client}</span>
                        <span class="dash-week-event__treatment">${e.treatment}</span>
                    </div>`;
            });
            html += '</div>';
        });

        html += '</div></div>';
        calendar.innerHTML = html;

        calendar.querySelectorAll('.dash-week-event').forEach(el => {
            el.addEventListener('click', e => {
                e.stopPropagation();
                const id = parseInt(el.dataset.id);
                openViewModal(allEvents.find(ev => ev.id === id));
            });
        });
    }

    // ---------------------------------------------------------------
    // Navigation
    // ---------------------------------------------------------------

    prevBtn.addEventListener('click', () => {
        currentView === 'month'
            ? currentDate.setMonth(currentDate.getMonth() - 1)
            : currentDate.setDate(currentDate.getDate() - 7);
        fetchEvents();
    });

    nextBtn.addEventListener('click', () => {
        currentView === 'month'
            ? currentDate.setMonth(currentDate.getMonth() + 1)
            : currentDate.setDate(currentDate.getDate() + 7);
        fetchEvents();
    });

    todayBtn.addEventListener('click', () => { currentDate = new Date(); fetchEvents(); });

    viewBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            viewBtns.forEach(b => b.classList.remove('dash-view-btn--active'));
            btn.classList.add('dash-view-btn--active');
            currentView = btn.dataset.view;
            fetchEvents();
        });
    });

    // ---------------------------------------------------------------
    // Booking modal — view
    // ---------------------------------------------------------------

    function openViewModal(booking) {
        activeBooking = booking;
        isEditMode    = false;

        modalTitle.textContent  = 'Appointment Details';
        modalView.style.display = 'block';
        modalForm.style.display = 'none';

        document.getElementById('viewClient').textContent    = booking.client;
        document.getElementById('viewEmail').textContent     = booking.email;
        document.getElementById('viewPhone').textContent     = booking.phone || '—';
        document.getElementById('viewTreatment').textContent = booking.treatment;
        document.getElementById('viewDate').textContent      =
            new Date(booking.date + 'T00:00:00').toLocaleDateString('en-GB', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
            });
        document.getElementById('viewTime').textContent     = booking.start_time;
        document.getElementById('viewDuration').textContent = booking.duration + ' minutes';
        document.getElementById('viewPrice').textContent    = '£' + booking.price;
        document.getElementById('viewNotes').textContent    = booking.notes || '—';
        document.getElementById('viewStatus').textContent   =
            booking.status.charAt(0).toUpperCase() + booking.status.slice(1);

        cancelBookingBtn.style.display =
            booking.status === 'cancelled' ? 'none' : 'inline-flex';

        openModal(modalOverlay);
    }

    viewProfileBtn.addEventListener('click', () => {
        if (!activeBooking) return;
        closeModal(modalOverlay);
        openProfilePanel(activeBooking.client_id);
    });

    editBookingBtn.addEventListener('click', () => openEditModal(activeBooking));

    cancelBookingBtn.addEventListener('click', () => {
        if (!confirm(`Cancel ${activeBooking.client}'s ${activeBooking.treatment} on ${activeBooking.date}?`)) return;
        fetch(DASHBOARD_URLS.bookingCancel.replace('{id}', activeBooking.id), {
            method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN },
        })
        .then(r => r.json())
        .then(data => { if (data.ok) { closeModal(modalOverlay); fetchEvents(); } });
    });

    // ---------------------------------------------------------------
    // Booking modal — create
    // ---------------------------------------------------------------

    newBookingBtn.addEventListener('click', () => openCreateModal(null));

    function openCreateModal(prefilledDate) {
        activeBooking  = null;
        isEditMode     = false;
        selectedUserId = null;

        modalTitle.textContent          = 'New Booking';
        modalView.style.display         = 'none';
        modalForm.style.display         = 'block';
        clientSearchGroup.style.display = 'block';
        statusGroup.style.display       = 'none';

        resetForm();
        if (prefilledDate) formDate.value = prefilledDate;
        openModal(modalOverlay);
    }

    // ---------------------------------------------------------------
    // Booking modal — edit
    // ---------------------------------------------------------------

    function openEditModal(booking) {
        isEditMode = true;

        modalTitle.textContent          = 'Edit Booking';
        modalView.style.display         = 'none';
        modalForm.style.display         = 'block';
        clientSearchGroup.style.display = 'none';
        statusGroup.style.display       = 'block';

        resetForm();

        formDate.value   = booking.date;
        formNotes.value  = booking.notes;
        formStatus.value = booking.status;

        Array.from(formTreatment.options).forEach(opt => {
            if (opt.text.startsWith(booking.treatment)) formTreatment.value = opt.value;
        });

        populateTimeSlots(() => { formTime.value = booking.start_time; });
    }

    // ---------------------------------------------------------------
    // Modal open/close helpers
    // ---------------------------------------------------------------

    function openModal(overlay) {
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeModal(overlay) {
        overlay.style.display = 'none';
        document.body.style.overflow = '';
    }

    modalClose.addEventListener('click',  () => closeModal(modalOverlay));
    formCancelBtn.addEventListener('click', () => closeModal(modalOverlay));
    modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeModal(modalOverlay); });

    // ---------------------------------------------------------------
    // Client search (booking modal)
    // ---------------------------------------------------------------

    let searchTimeout = null;

    clientSearch.addEventListener('input', function () {
        clearTimeout(searchTimeout);
        const q = this.value.trim();

        if (q.length < 2) { clientResults.innerHTML = ''; clientResults.style.display = 'none'; return; }

        searchTimeout = setTimeout(() => {
            fetch(`${DASHBOARD_URLS.userSearch}?q=${encodeURIComponent(q)}`)
                .then(r => r.json())
                .then(data => {
                    if (!data.users.length) {
                        clientResults.innerHTML = '<div class="dash-search-result dash-search-result--empty">No clients found</div>';
                        clientResults.style.display = 'block';
                        return;
                    }
                    clientResults.innerHTML = data.users.map(u => `
                        <div class="dash-search-result" data-id="${u.id}" data-name="${u.name}" data-email="${u.email}">
                            <span class="dash-search-result__name">${u.name}</span>
                            <span class="dash-search-result__email">${u.email}</span>
                        </div>`).join('');
                    clientResults.style.display = 'block';

                    clientResults.querySelectorAll('.dash-search-result[data-id]').forEach(row => {
                        row.addEventListener('click', () => {
                            selectedUserId = parseInt(row.dataset.id);
                            clientSearch.value = row.dataset.name;
                            selectedClientLabel.textContent = `${row.dataset.name} (${row.dataset.email})`;
                            clientResults.innerHTML = '';
                            clientResults.style.display = 'none';
                        });
                    });
                });
        }, 250);
    });

    document.addEventListener('click', e => {
        if (!clientSearch.contains(e.target) && !clientResults.contains(e.target)) {
            clientResults.style.display = 'none';
        }
    });

    // ---------------------------------------------------------------
    // Time slots
    // ---------------------------------------------------------------

    formTreatment.addEventListener('change', () => populateTimeSlots());

    function populateTimeSlots(callback) {
        const opt = formTreatment.options[formTreatment.selectedIndex];
        formTime.innerHTML = '<option value="">— Select —</option>';
        if (!opt || !opt.value) return;

        const duration = parseInt(opt.dataset.duration);
        generateTimes(duration).forEach(t => {
            const o = document.createElement('option');
            o.value = t; o.textContent = t;
            formTime.appendChild(o);
        });
        if (callback) callback();
    }

    // ---------------------------------------------------------------
    // Save booking
    // ---------------------------------------------------------------

    formSaveBtn.addEventListener('click', () => {
        clearErrors();
        const payload = {
            treatment_id: formTreatment.value,
            date:         formDate.value,
            start_time:   formTime.value,
            notes:        formNotes.value,
        };

        const url = isEditMode
            ? DASHBOARD_URLS.bookingEdit.replace('{id}', activeBooking.id)
            : DASHBOARD_URLS.bookingCreate;

        if (isEditMode) payload.status = formStatus.value;
        else payload.user_id = selectedUserId;

        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify(payload),
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) { closeModal(modalOverlay); fetchEvents(); }
            else showErrors(data.errors || {});
        });
    });

    function resetForm() {
        clientSearch.value              = '';
        selectedClientLabel.textContent = '';
        clientResults.innerHTML         = '';
        clientResults.style.display     = 'none';
        formTreatment.value             = '';
        formDate.value                  = '';
        formTime.innerHTML              = '<option value="">— Select treatment first —</option>';
        formNotes.value                 = '';
        formStatus.value                = 'confirmed';
        clearErrors();
    }

    function clearErrors() {
        document.querySelectorAll('.dash-field-error').forEach(el => el.textContent = '');
    }

    function showErrors(errors) {
        const map = { user: 'errorUser', treatment: 'errorTreatment', date: 'errorDate', start_time: 'errorStartTime', __all__: 'errorAll' };
        Object.entries(errors).forEach(([key, msg]) => {
            const el = document.getElementById(map[key]);
            if (el) el.textContent = msg;
        });
    }

    // ---------------------------------------------------------------
    // Client list
    // ---------------------------------------------------------------

    let clientSearchTimeout = null;

    function loadClients(q) {
        const url = q
            ? `${DASHBOARD_URLS.clientList}?q=${encodeURIComponent(q)}`
            : DASHBOARD_URLS.clientList;

        fetch(url)
            .then(r => r.json())
            .then(data => {
                if (!data.clients.length) {
                    clientTableBody.innerHTML = `<tr><td colspan="5" class="dash-client-table__empty">No clients found.</td></tr>`;
                    return;
                }

                clientTableBody.innerHTML = data.clients.map(c => `
                    <tr class="dash-client-row" data-id="${c.id}">
                        <td class="dash-client-name">${c.name}</td>
                        <td>${c.email}</td>
                        <td>${c.phone || '—'}</td>
                        <td>${c.joined}</td>
                        <td>
                            <button class="dash-client-view-btn btn btn--ghost btn--sm" data-id="${c.id}">
                                View Profile
                            </button>
                        </td>
                    </tr>`).join('');

                clientTableBody.querySelectorAll('.dash-client-view-btn').forEach(btn => {
                    btn.addEventListener('click', () => openProfilePanel(parseInt(btn.dataset.id)));
                });
            });
    }

    clientSearchBar.addEventListener('input', function () {
        clearTimeout(clientSearchTimeout);
        clientSearchTimeout = setTimeout(() => loadClients(this.value.trim()), 300);
    });

    loadClients('');

    // ---------------------------------------------------------------
    // Profile panel
    // ---------------------------------------------------------------

    function openProfilePanel(userId) {
        activePanelUserId = userId;
        profilePanel.classList.add('dash-profile-panel--open');
        profileOverlay.style.display = 'block';
        document.body.style.overflow = 'hidden';
        profilePanelBody.innerHTML   = '<div class="dash-profile-loading">Loading…</div>';
        panelName.textContent  = '—';
        panelEmail.textContent = '—';

        fetch(DASHBOARD_URLS.clientProfile.replace('{id}', userId))
            .then(r => r.json())
            .then(data => renderProfilePanel(data));
    }

    function closeProfilePanel() {
        profilePanel.classList.remove('dash-profile-panel--open');
        profileOverlay.style.display = 'none';
        document.body.style.overflow = '';
        activePanelUserId = null;
    }

    profileClose.addEventListener('click', closeProfilePanel);
    profileOverlay.addEventListener('click', closeProfilePanel);

    function renderProfilePanel(data) {
        const u       = data.user;
        const forms   = data.forms;
        const bundles = data.bundles;
        const credit  = data.credit;

        panelName.textContent  = u.name;
        panelEmail.textContent = u.email;

        // Store for edit
        profilePanel.dataset.userId = u.id;

        // Form status pills — clickable links
        function pill(label, complete, href, tooltip) {
            const cls = complete ? 'dash-form-pill--complete' : 'dash-form-pill--incomplete';
            const tip = tooltip || '';
            if (href) {
                return `<a href="${href}" class="dash-form-pill ${cls}" title="${tip}" target="_blank">${label}</a>`;
            }
            return `<span class="dash-form-pill ${cls}" title="${tip}">${label}</span>`;
        }

        const consultPill = pill(
            'Consultation',
            forms.consultation.completed,
            DASHBOARD_URLS.formConsultation.replace('{id}', u.id),
            forms.consultation.date ? `Completed ${forms.consultation.date}` : 'Not completed'
        );
        const photoPill = pill(
            'Photography',
            forms.photography.completed,
            DASHBOARD_URLS.formPhotography.replace('{id}', u.id),
            forms.photography.date ? `Completed ${forms.photography.date}` : 'Not completed'
        );
        const botoxClientPill = pill(
            'Botox (Client)',
            forms.botox.client_signed,
            DASHBOARD_URLS.formBotoxClient.replace('{id}', u.id),
            forms.botox.date ? `Signed ${forms.botox.date}` : 'Not signed'
        );
        const botoxOpPill = pill(
            'Botox (Operator)',
            forms.botox.fully_complete,
            forms.botox.id ? DASHBOARD_URLS.botoxOperator.replace('{id}', forms.botox.id) : null,
            forms.botox.fully_complete ? 'Fully complete' : (forms.botox.client_signed ? 'Awaiting operator sign-off' : 'Client has not signed yet')
        );
        const prpClientPill = pill(
            'PRP (Client)',
            forms.prp.client_signed,
            DASHBOARD_URLS.formPrpClient.replace('{id}', u.id),
            forms.prp.date ? `Signed ${forms.prp.date}` : 'Not signed'
        );
        const prpOpPill = pill(
            'PRP (Operator)',
            forms.prp.fully_complete,
            forms.prp.id ? DASHBOARD_URLS.prpOperator.replace('{id}', forms.prp.id) : null,
            forms.prp.fully_complete ? 'Fully complete' : (forms.prp.client_signed ? 'Awaiting operator sign-off' : 'Client has not signed yet')
        );
        const laserPill = pill(
            forms.laser_reconsent.count > 0
                ? `Laser Re-Consent (${forms.laser_reconsent.count})`
                : 'Laser Re-Consent',
            forms.laser_reconsent.count > 0,
            DASHBOARD_URLS.formLaserReconsent.replace('{id}', u.id),
            forms.laser_reconsent.last_date ? `Last: ${forms.laser_reconsent.last_date}` : 'None completed'
        );

        // Bundle pips
        function bundlePips(b) {
            let html = '';
            for (let i = 0; i < b.total_sessions; i++) {
                html += `<span class="pip${i < b.sessions_used ? ' pip--used' : ''}"></span>`;
            }
            return html;
        }

        const bundlesHtml = bundles.length
            ? bundles.filter(b => b.status === 'active').map(b => `
                <div class="dash-bundle-row">
                    <div class="dash-bundle-row__info">
                        <span class="dash-bundle-row__name">${b.treatment_name}</span>
                        <div class="dash-bundle-row__pips">${bundlePips(b)}</div>
                        <span class="dash-bundle-row__count">${b.sessions_remaining} of ${b.total_sessions} remaining</span>
                    </div>
                    <button class="btn btn--ghost btn--sm dash-bundle-use-btn" data-bundle-id="${b.id}" data-bundle-name="${b.treatment_name}">
                        Use Session
                    </button>
                </div>`).join('') || '<p class="dash-muted">No active bundles.</p>'
            : '<p class="dash-muted">No bundles.</p>';

        // Record cards
        const cardsHtml = data.record_cards.length
            ? data.record_cards.map(rc => `
                <a href="${DASHBOARD_URLS.recordCardView.replace('{id}', rc.id)}" target="_blank" class="dash-record-row">
                    <span class="dash-record-row__num">#${rc.treatment_number}</span>
                    <span class="dash-record-row__date">${rc.date}</span>
                    <span class="dash-record-row__treatment">${rc.treatment_for || '—'}</span>
                </a>`).join('')
            : '<p class="dash-muted">No record cards yet.</p>';

        profilePanelBody.innerHTML = `

            <!-- Personal details -->
            <div class="dash-panel-section" id="panelViewMode">
                <div class="dash-panel-section__header">
                    <h3 class="dash-panel-section__title">Personal Details</h3>
                </div>
                <dl class="dash-panel-dl">
                    <dt>Phone</dt>        <dd>${u.phone || '—'}</dd>
                    <dt>Date of birth</dt><dd>${u.dob || '—'}</dd>
                    <dt>Skin type</dt>    <dd>${u.skin_type || '—'}</dd>
                    <dt>Address</dt>      <dd>${u.address ? u.address.replace(/\n/g, '<br>') : '—'}</dd>
                    <dt>GDPR consent</dt> <dd>${u.gdpr_consent ? '✓ Given' : '✗ Not given'}</dd>
                </dl>
                <div class="dash-panel-section__header" style="margin-top:1rem;">
                    <h3 class="dash-panel-section__title">Medical Notes <span class="dash-operator-only">Operator only</span></h3>
                </div>
                <p class="dash-medical-notes">${u.medical_notes || 'No notes on file.'}</p>
            </div>

            <!-- Edit mode (hidden by default) -->
            <div class="dash-panel-section" id="panelEditMode" style="display:none;">
                <h3 class="dash-panel-section__title">Edit Profile</h3>
                <div class="cform-grid cform-grid--2" style="gap:0.75rem;">
                    <div class="dash-form-group"><label class="dash-label">First Name</label><input class="dash-input" id="editFirstName" value="${u.name.split(' ')[0] || ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Last Name</label><input class="dash-input" id="editLastName" value="${u.name.split(' ').slice(1).join(' ') || ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Phone</label><input class="dash-input" id="editPhone" value="${u.phone || ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Date of Birth</label><input class="dash-input" type="date" id="editDob" value="${u.dob ? new Date(u.dob).toISOString().split('T')[0] : ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Address Line 1</label><input class="dash-input" id="editAddr1" value="${u.address.split('\n')[0] || ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Address Line 2</label><input class="dash-input" id="editAddr2" value="${u.address.split('\n')[1] || ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Town / City</label><input class="dash-input" id="editCity" value="${u.address.split('\n')[2] || ''}"></div>
                    <div class="dash-form-group"><label class="dash-label">Postcode</label><input class="dash-input" id="editPostcode" value="${u.address.split('\n')[3] || ''}"></div>
                    <div class="dash-form-group" style="grid-column:1/-1;"><label class="dash-label">Medical Notes</label><textarea class="dash-input" id="editMedicalNotes" rows="3">${u.medical_notes || ''}</textarea></div>
                </div>
                <div class="dash-modal__actions" style="padding:1rem 0 0;">
                    <button class="btn btn--ghost btn--sm" id="panelEditCancel">Cancel</button>
                    <button class="btn btn--primary btn--sm" id="panelEditSave">Save Changes</button>
                </div>
            </div>

            <!-- Upcoming bookings -->
            <div class="dash-panel-section">
                <h3 class="dash-panel-section__title">Upcoming Appointments</h3>
                ${data.upcoming_bookings.length
                    ? data.upcoming_bookings.map(b => `
                        <div class="dash-appt-row">
                            <div class="dash-appt-row__info">
                                <span class="dash-appt-row__treatment">${b.treatment}</span>
                                <span class="dash-appt-row__date">${b.date} at ${b.time}</span>
                            </div>
                            <span class="dash-appt-row__duration">${b.duration} min</span>
                        </div>`).join('')
                    : '<p class="dash-muted">No upcoming appointments.</p>'
                }
            </div>

            <!-- Past bookings (collapsible) -->
            <div class="dash-panel-section">
                <button class="dash-collapsible-toggle" id="pastBookingsToggle">
                    Past Appointments <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                <div id="pastBookingsContent" style="display:none;">
                    ${data.past_bookings.length
                        ? data.past_bookings.map(b => `
                            <div class="dash-appt-row dash-appt-row--past">
                                <div class="dash-appt-row__info">
                                    <span class="dash-appt-row__treatment">${b.treatment}</span>
                                    <span class="dash-appt-row__date">${b.date} at ${b.time}</span>
                                </div>
                                <span class="dash-appt-badge dash-appt-badge--${b.status}">${b.status}</span>
                            </div>`).join('')
                        : '<p class="dash-muted">No past appointments.</p>'
                    }
                </div>
            </div>

            <!-- Forms -->
            <div class="dash-panel-section">
                <h3 class="dash-panel-section__title">Consent Forms</h3>
                <div class="dash-form-pills">
                    ${consultPill}
                    ${photoPill}
                    ${botoxClientPill}
                    ${botoxOpPill}
                    ${prpClientPill}
                    ${prpOpPill}
                    ${laserPill}
                </div>
                <div class="dash-form-actions">
                    <a href="${DASHBOARD_URLS.formConsultation.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">Consultation Form</a>
                    <a href="${DASHBOARD_URLS.formPhotography.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">Photography Consent</a>
                    <a href="${DASHBOARD_URLS.formBotoxClient.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">Botox (Client)</a>
                    <a href="${forms.botox.id ? DASHBOARD_URLS.botoxOperator.replace('{id}', forms.botox.id) : DASHBOARD_URLS.formBotoxClient.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">Botox (Operator)</a>
                    <a href="${DASHBOARD_URLS.formPrpClient.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">PRP (Client)</a>
                    <a href="${forms.prp.id ? DASHBOARD_URLS.prpOperator.replace('{id}', forms.prp.id) : DASHBOARD_URLS.formPrpClient.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">PRP (Operator)</a>
                    <a href="${DASHBOARD_URLS.formLaserReconsent.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">Laser Re-Consent</a>
                </div>
            </div>

            <!-- Record cards -->
            <div class="dash-panel-section">
                <div class="dash-panel-section__header">
                    <h3 class="dash-panel-section__title">Record Cards</h3>
                    <a href="${DASHBOARD_URLS.recordCardNew.replace('{id}', u.id)}" class="btn btn--ghost btn--sm" target="_blank">+ New Record Card</a>
                </div>
                <div class="dash-record-list">${cardsHtml}</div>
            </div>

            <!-- Bundles -->
            <div class="dash-panel-section">
                <div class="dash-panel-section__header">
                    <h3 class="dash-panel-section__title">Pre-Paid Bundles</h3>
                    <button class="btn btn--ghost btn--sm" id="addBundleBtn">+ Add Bundle</button>
                </div>
                <div id="bundlesList">${bundlesHtml}</div>
            </div>

            <!-- Account credit -->
            <div class="dash-panel-section">
                <div class="dash-panel-section__header">
                    <h3 class="dash-panel-section__title">Account Credit</h3>
                    <button class="btn btn--ghost btn--sm" id="adjustCreditBtn">Adjust</button>
                </div>
                <p class="dash-credit-balance">£<span id="creditBalance">${credit.balance}</span></p>
            </div>
        `;

        // Wire up edit toggle
        panelEditBtn.addEventListener('click', () => {
            document.getElementById('panelViewMode').style.display = 'none';
            document.getElementById('panelEditMode').style.display = 'block';
            panelEditBtn.style.display = 'none';
        });

        document.getElementById('panelEditCancel').addEventListener('click', () => {
            document.getElementById('panelViewMode').style.display = 'block';
            document.getElementById('panelEditMode').style.display = 'none';
            panelEditBtn.style.display = 'inline-flex';
        });

        document.getElementById('panelEditSave').addEventListener('click', () => {
            const payload = {
                first_name:    document.getElementById('editFirstName').value,
                last_name:     document.getElementById('editLastName').value,
                phone_number:  document.getElementById('editPhone').value,
                date_of_birth: document.getElementById('editDob').value,
                address_line_1: document.getElementById('editAddr1').value,
                address_line_2: document.getElementById('editAddr2').value,
                town_city:     document.getElementById('editCity').value,
                postcode:      document.getElementById('editPostcode').value,
                medical_notes: document.getElementById('editMedicalNotes').value,
            };

            fetch(DASHBOARD_URLS.clientEdit.replace('{id}', u.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify(payload),
            })
            .then(r => r.json())
            .then(data => {
                if (data.ok) openProfilePanel(u.id);
            });
        });

        // Past bookings toggle
        document.getElementById('pastBookingsToggle').addEventListener('click', function () {
            const content = document.getElementById('pastBookingsContent');
            const open    = content.style.display !== 'none';
            content.style.display = open ? 'none' : 'block';
            this.classList.toggle('dash-collapsible-toggle--open', !open);
        });

        // Bundle use session
        profilePanelBody.querySelectorAll('.dash-bundle-use-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (!confirm(`Mark one session as used for "${btn.dataset.bundleName}"?`)) return;
                fetch(
                    DASHBOARD_URLS.bundleUse
                        .replace('{id}', u.id)
                        .replace('{bundle_id}', btn.dataset.bundleId),
                    { method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN } }
                )
                .then(r => r.json())
                .then(data => { if (data.ok) openProfilePanel(u.id); });
            });
        });

        // Add bundle
        document.getElementById('addBundleBtn').addEventListener('click', () => {
            openModal(bundleModalOverlay);
        });

        // Adjust credit
        document.getElementById('adjustCreditBtn').addEventListener('click', () => {
            openModal(creditModalOverlay);
        });
    }

    // Profile panel edit button (header)
    panelEditBtn.addEventListener('click', () => {}); // delegated above after render

    // ---------------------------------------------------------------
    // Bundle modal
    // ---------------------------------------------------------------

    bundleModalClose.addEventListener('click',  () => closeModal(bundleModalOverlay));
    bundleModalCancel.addEventListener('click', () => closeModal(bundleModalOverlay));

    bundleModalSave.addEventListener('click', () => {
        const name     = document.getElementById('bundleTreatmentName').value.trim();
        const sessions = document.getElementById('bundleTotalSessions').value;
        const expiry   = document.getElementById('bundleExpiryDate').value;
        const notes    = document.getElementById('bundleNotes').value;
        const errEl    = document.getElementById('bundleError');
        errEl.textContent = '';

        if (!name || !sessions) { errEl.textContent = 'Treatment name and sessions are required.'; return; }

        fetch(DASHBOARD_URLS.bundleAdd.replace('{id}', activePanelUserId), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify({ treatment_name: name, total_sessions: sessions, expiry_date: expiry, notes }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                closeModal(bundleModalOverlay);
                // Clear fields
                document.getElementById('bundleTreatmentName').value = '';
                document.getElementById('bundleTotalSessions').value = '6';
                document.getElementById('bundleExpiryDate').value    = '';
                document.getElementById('bundleNotes').value         = '';
                openProfilePanel(activePanelUserId);
            } else {
                errEl.textContent = data.error || 'Something went wrong.';
            }
        });
    });

    // ---------------------------------------------------------------
    // Credit modal
    // ---------------------------------------------------------------

    creditModalClose.addEventListener('click',  () => closeModal(creditModalOverlay));
    creditModalCancel.addEventListener('click', () => closeModal(creditModalOverlay));

    creditModalSave.addEventListener('click', () => {
        const type   = document.getElementById('creditType').value;
        const amount = document.getElementById('creditAmount').value;
        const desc   = document.getElementById('creditDescription').value;
        const errEl  = document.getElementById('creditError');
        errEl.textContent = '';

        if (!amount || parseFloat(amount) <= 0) { errEl.textContent = 'Please enter a valid amount.'; return; }

        fetch(DASHBOARD_URLS.creditAdjust.replace('{id}', activePanelUserId), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify({ type, amount, description: desc }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.ok) {
                closeModal(creditModalOverlay);
                document.getElementById('creditAmount').value      = '';
                document.getElementById('creditDescription').value = '';
                const balEl = document.getElementById('creditBalance');
                if (balEl) balEl.textContent = data.balance;
            } else {
                errEl.textContent = data.error || 'Something went wrong.';
            }
        });
    });

    // ---------------------------------------------------------------
    // Init
    // ---------------------------------------------------------------

    fetchEvents();
});