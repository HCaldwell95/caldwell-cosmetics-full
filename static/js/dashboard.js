document.addEventListener('DOMContentLoaded', function () {

    // esc/safeColour also defined globally in client-panel.js; redefined here
    // for use in the calendar rendering functions below.
    function esc(s) {
        return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
    function safeColour(c) {
        return (c || '').replace(/[^a-zA-Z0-9#()%., ]/g, '');
    }

    // ---------------------------------------------------------------
    // State
    // ---------------------------------------------------------------

    let currentView    = 'month';
    let currentDate    = new Date();
    let allEvents      = [];
    let activeBooking  = null;
    let selectedUserId = null;
    let isEditMode     = false;

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

    // ---------------------------------------------------------------
    // Calendar — fetch & render
    // ---------------------------------------------------------------

    function getDateRange() {
        const y = currentDate.getFullYear();
        const m = currentDate.getMonth();

        if (currentView === 'month') {
            return { start: new Date(y, m, 1), end: new Date(y, m + 1, 0) };
        }

        if (currentView === 'day') {
            const d = new Date(currentDate);
            d.setHours(0, 0, 0, 0);
            return { start: d, end: d };
        }

        // week
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
                if (currentView === 'month')     renderMonth();
                else if (currentView === 'week') renderWeek();
                else                             renderDay();
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

        calendar.querySelectorAll('.dash-month-more').forEach(btn => {
            btn.addEventListener('click', e => {
                e.stopPropagation();
                currentDate = new Date(btn.dataset.date + 'T00:00:00');
                currentView = 'day';
                viewBtns.forEach(b => b.classList.remove('dash-view-btn--active'));
                document.querySelector('[data-view="day"]').classList.add('dash-view-btn--active');
                fetchEvents();
            });
        });
    }

    function eventPill(e) {
        const cls    = e.status === 'cancelled' ? 'dash-event-pill--cancelled' : '';
        const colour = e.status === 'cancelled' ? '' : `style="background:${safeColour(e.category_colour) || '#b8965a'}"`;
        return `
            <div class="dash-event-pill ${cls}" ${colour} data-id="${e.id}" title="${esc(e.client)} — ${esc(e.treatment)}">
                <span class="dash-event-pill__time">${esc(e.start_time)}</span>
                <span class="dash-event-pill__name">${esc(e.client)}</span>
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
                        <span class="dash-week-event__name">${esc(e.client)}</span>
                        <span class="dash-week-event__treatment">${esc(e.treatment)}</span>
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
    // Day view
    // ---------------------------------------------------------------

    function renderDay() {
        const today   = formatISO(new Date());
        const dateStr = formatISO(currentDate);
        const isToday = dateStr === today;
        const isOpen  = OPEN_DAYS.includes(currentDate.getDay());

        periodLabel.textContent = currentDate.toLocaleDateString('en-GB', {
            weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
        });

        const dayEvents = allEvents
            .filter(e => e.date === dateStr)
            .sort((a, b) => a.start_time.localeCompare(b.start_time));

        const HOUR_START = 9;
        const HOUR_END   = 18;
        const HOUR_COUNT = HOUR_END - HOUR_START;
        const PX_PER_MIN = 2;

        let html = '<div class="dash-day-grid">';

        // Header row
        html += '<div class="dash-day-header">';
        html += '<div class="dash-week-time-header"></div>';
        html += `<div class="dash-week-col-header${isToday ? ' dash-week-col-header--today' : ''}">
            <span class="dash-week-col-header__day">${currentDate.toLocaleDateString('en-GB', { weekday: 'long' })}</span>
            <span class="dash-week-col-header__date${isToday ? ' dash-week-col-header__date--today' : ''}">${currentDate.getDate()}</span>
            ${!isOpen ? '<span class="dash-week-closed">Closed</span>' : ''}
        </div>`;
        html += '</div>';

        // Body
        html += '<div class="dash-day-body">';
        html += '<div class="dash-week-gutter">';
        for (let h = HOUR_START; h < HOUR_END; h++) {
            html += `<div class="dash-week-gutter__hour" style="height:${60 * PX_PER_MIN}px">${String(h).padStart(2,'0')}:00</div>`;
        }
        html += '</div>';

        html += `<div class="dash-day-col" data-date="${dateStr}" style="height:${HOUR_COUNT * 60 * PX_PER_MIN}px">`;
        for (let h = 0; h < HOUR_COUNT; h++) {
            html += `<div class="dash-week-hour-line" style="top:${h * 60 * PX_PER_MIN}px"></div>`;
        }
        dayEvents.forEach(e => {
            const [eh, em] = e.start_time.split(':').map(Number);
            const topMins  = (eh - HOUR_START) * 60 + em;
            const height   = e.duration * PX_PER_MIN;
            const colour   = e.status === 'cancelled' ? '' : `background:${e.category_colour || '#b8965a'};`;
            html += `
                <div class="dash-week-event${e.status === 'cancelled' ? ' dash-week-event--cancelled' : ''}"
                     data-id="${e.id}" style="${colour}top:${topMins * PX_PER_MIN}px; height:${height}px;">
                    <span class="dash-week-event__time">${esc(e.start_time)}</span>
                    <span class="dash-week-event__name">${esc(e.client)}</span>
                    <span class="dash-week-event__treatment">${esc(e.treatment)}</span>
                </div>`;
        });
        html += '</div>';
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
        if (currentView === 'month')     currentDate.setMonth(currentDate.getMonth() - 1);
        else if (currentView === 'week') currentDate.setDate(currentDate.getDate() - 7);
        else                             currentDate.setDate(currentDate.getDate() - 1);
        fetchEvents();
    });

    nextBtn.addEventListener('click', () => {
        if (currentView === 'month')     currentDate.setMonth(currentDate.getMonth() + 1);
        else if (currentView === 'week') currentDate.setDate(currentDate.getDate() + 7);
        else                             currentDate.setDate(currentDate.getDate() + 1);
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
    // Modal open/close (openModal/closeModal come from client-panel.js)
    // ---------------------------------------------------------------

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
                        <div class="dash-search-result" data-id="${u.id}" data-name="${esc(u.name)}" data-email="${esc(u.email)}">
                            <span class="dash-search-result__name">${esc(u.name)}</span>
                            <span class="dash-search-result__email">${esc(u.email)}</span>
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
        // Operators aren't restricted to the clinic's public opening hours —
        // offer slots across the full day; the server still blocks overlaps.
        generateTimes(duration, '00:00', '23:59').forEach(t => {
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
    // Init
    // ---------------------------------------------------------------

    fetchEvents();
});
