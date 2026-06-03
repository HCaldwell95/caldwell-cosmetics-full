document.addEventListener('DOMContentLoaded', function () {

    // Structure: { treatmentId: { "YYYY-MM-DD": { times: [...], booked: [...] } } }
    const allSlots = JSON.parse(
        document.getElementById('booked-slots-data').textContent
    );

    let selectedTreatment = null;
    let selectedDate      = null;
    let selectedTime      = null;
    let currentDate       = new Date();

    // Must match views.py config
    const OPEN_DAYS = [1, 2, 3]; // Mon, Tue, Wed (JS: 0=Sun)

    // ---------------------------------------------------------------
    // Step navigation
    // ---------------------------------------------------------------

    function goToStep(stepNumber) {
        document.querySelectorAll('.booking-step')
            .forEach(el => el.classList.add('booking-step--hidden'));

        const target = document.getElementById(`step-${stepNumber}`);
        if (target) target.classList.remove('booking-step--hidden');

        [1, 2, 3].forEach(n => {
            const ind = document.getElementById(`step-ind-${n}`);
            ind.classList.remove('step-indicator--active', 'step-indicator--done');
            if (n < stepNumber) ind.classList.add('step-indicator--done');
            if (n === stepNumber) ind.classList.add('step-indicator--active');
        });

        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    window.goToStep = goToStep;

    // ---------------------------------------------------------------
    // Step 1 — Treatment selection
    // ---------------------------------------------------------------

    const categoryTabs    = document.querySelectorAll('.category-tab');
    const treatmentCards  = document.querySelectorAll('.treatment-card');
    const groupHeadings   = document.querySelectorAll('.treatment-group-heading');

    categoryTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            categoryTabs.forEach(t => t.classList.remove('category-tab--active'));
            this.classList.add('category-tab--active');
            scrollCatStripToActive();

            const catId = this.dataset.category;
            treatmentCards.forEach(card => {
                card.classList.toggle(
                    'treatment-card--hidden',
                    card.dataset.category !== catId
                );
            });
            groupHeadings.forEach(heading => {
                heading.classList.toggle(
                    'treatment-card--hidden',
                    heading.dataset.category !== catId
                );
            });
        });
    });

    if (categoryTabs.length) setTimeout(() => categoryTabs[0].click(), 0);

    // Auto-filter to the active tab on load
    const activeTab = document.querySelector('.category-tab--active');
    if (activeTab) activeTab.click();

    // Category strip scrolling
    const catStripTrack = document.getElementById('categoryTabs');
    const catStripPrev  = document.getElementById('catStripPrev');
    const catStripNext  = document.getElementById('catStripNext');
    let catStripOffset  = 0;

    function getCatScrollAmount() {
        const pill = catStripTrack && catStripTrack.querySelector('.category-tab');
        return pill ? pill.offsetWidth + 8 : 160;
    }

    function scrollCatStrip(direction) {
        const viewport   = catStripTrack.parentElement;
        const maxScroll  = catStripTrack.scrollWidth - viewport.offsetWidth;
        catStripOffset   = Math.max(0, Math.min(catStripOffset + direction * getCatScrollAmount() * 2, maxScroll));
        catStripTrack.style.transform = `translateX(-${catStripOffset}px)`;
        catStripPrev.disabled = catStripOffset <= 0;
        catStripNext.disabled = catStripOffset >= maxScroll;
    }

    function scrollCatStripToActive() {
        const active = catStripTrack && catStripTrack.querySelector('.category-tab--active');
        if (!active) return;
        const viewport   = catStripTrack.parentElement;
        const pillLeft   = active.offsetLeft;
        const pillRight  = pillLeft + active.offsetWidth;
        const viewWidth  = viewport.offsetWidth;
        if (pillLeft < catStripOffset) {
            catStripOffset = Math.max(0, pillLeft - 8);
        } else if (pillRight > catStripOffset + viewWidth) {
            catStripOffset = pillRight - viewWidth + 8;
        }
        catStripTrack.style.transform = `translateX(-${catStripOffset}px)`;
        const maxScroll = catStripTrack.scrollWidth - viewWidth;
        catStripPrev.disabled = catStripOffset <= 0;
        catStripNext.disabled = maxScroll <= 0 || catStripOffset >= maxScroll;
    }

    if (catStripPrev && catStripNext) {
        catStripPrev.addEventListener('click', () => scrollCatStrip(-1));
        catStripNext.addEventListener('click', () => scrollCatStrip(1));
        catStripPrev.disabled = true;
        setTimeout(() => {
            if (catStripTrack) {
                const viewport  = catStripTrack.parentElement;
                const maxScroll = catStripTrack.scrollWidth - viewport.offsetWidth;
                catStripNext.disabled = maxScroll <= 0;
            }
        }, 100);
    }

    window.selectTreatment = function (card) {
        selectedTreatment = {
            id:              card.dataset.treatmentId,
            name:            card.dataset.treatmentName,
            duration:        parseInt(card.dataset.duration),
            price:           card.dataset.price,
            requiresDeposit: card.dataset.requiresDeposit === 'true',
            depositAmount:   card.dataset.depositAmount,
        };

        // Reset previous selections
        selectedDate = null;
        selectedTime = null;

        document.getElementById('stripTreatmentName').textContent = selectedTreatment.name;
        document.getElementById('stripDuration').textContent      = selectedTreatment.duration + ' min';
        document.getElementById('stripPrice').textContent         = '£' + selectedTreatment.price;

        document.getElementById('timeslotEmpty').style.display   = 'block';
        document.getElementById('timeslotContent').style.display = 'none';

        goToStep(2);
        renderCalendar();
    };

    // ---------------------------------------------------------------
    // Step 2 — Calendar
    // ---------------------------------------------------------------

    const calendarEl = document.getElementById('calendar');
    const monthLabel = document.getElementById('currentMonth');

    function renderCalendar() {
        const year  = currentDate.getFullYear();
        const month = currentDate.getMonth();

        monthLabel.textContent = new Date(year, month).toLocaleDateString('en-GB', {
            month: 'long', year: 'numeric',
        });

        calendarEl.innerHTML = '';

        const firstDay    = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        // Blank cells before the 1st
        for (let i = 0; i < firstDay; i++) {
            calendarEl.appendChild(document.createElement('div'));
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dateObj = new Date(year, month, day);
            const dateStr = formatDate(dateObj);

            const dayEl = document.createElement('div');
            dayEl.textContent = day;
            dayEl.classList.add('calendar-day');

            const isPast      = dateObj < today;
            const isClosedDay = !OPEN_DAYS.includes(dateObj.getDay());

            if (isPast || isClosedDay) {
                dayEl.classList.add('calendar-day--unavailable');
            } else {
                dayEl.classList.add('calendar-day--available');
                dayEl.addEventListener('click', () => selectDate(dateStr, dateObj, dayEl));
            }

            calendarEl.appendChild(dayEl);
        }
    }

    document.getElementById('prevMonth').addEventListener('click', function () {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    document.getElementById('nextMonth').addEventListener('click', function () {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    function selectDate(dateStr, dateObj, el) {
        selectedDate = dateStr;
        selectedTime = null;

        document.querySelectorAll('.calendar-day')
            .forEach(d => d.classList.remove('calendar-day--selected'));
        el.classList.add('calendar-day--selected');

        showTimeSlots(dateStr, dateObj);
    }

    // ---------------------------------------------------------------
    // Step 2 — Time slots
    // ---------------------------------------------------------------

    function showTimeSlots(dateStr, dateObj) {
        document.getElementById('timeslotEmpty').style.display   = 'none';
        document.getElementById('timeslotContent').style.display = 'block';

        document.getElementById('timeslotDate').textContent =
            dateObj.toLocaleDateString('en-GB', {
                weekday: 'long', day: 'numeric', month: 'long',
            });

        const grid = document.getElementById('timeslotGrid');
        grid.innerHTML = '';

        const treatmentSlots = allSlots[selectedTreatment.id] || {};
        // If no entry for this date, no bookings exist — all times are free
        const dayData = treatmentSlots[dateStr] || { times: [], booked: [] };

        // Generate times client-side from the treatment duration
        // so we're never dependent on the DB having records
        const times = generateTimes(selectedTreatment.duration);

        if (times.length === 0) {
            grid.innerHTML = '<p class="timeslot-none">No slots available for this date.</p>';
            return;
        }

        times.forEach(time => {
            const isBooked = dayData.booked.includes(time);

            const el = document.createElement('div');
            el.textContent = time;
            el.classList.add('timeslot');

            if (isBooked) {
                el.classList.add('timeslot--booked');
                el.setAttribute('aria-disabled', 'true');
                el.dataset.booked = 'true';
                // pointer-events: none in CSS blocks clicks entirely;
                // no click listener needed or attached.
            } else {
                el.classList.add('timeslot--available');
                el.addEventListener('click', () => {
                    selectedTime = time;

                    document.querySelectorAll('.timeslot')
                        .forEach(s => s.classList.remove('timeslot--selected'));
                    el.classList.add('timeslot--selected');

                    populateConfirmation(time);
                    goToStep(3);
                });
            }

            grid.appendChild(el);
        });
    }

    function generateTimes(durationMinutes) {
        const slots  = [];
        const [oh, om]  = '09:30'.split(':').map(Number);
        const [ch, cm]  = '14:30'.split(':').map(Number);
        let h = oh, m = om;

        while (true) {
            const endMinutes  = h * 60 + m + durationMinutes;
            const closeMinutes = ch * 60 + cm;

            if (endMinutes > closeMinutes) break;

            slots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);

            m += durationMinutes; // interval = duration, no overlapping bookings
            if (m >= 60) { h += Math.floor(m / 60); m = m % 60; }
        }

        return slots;
    }

    // ---------------------------------------------------------------
    // Step 3 — Confirmation
    // ---------------------------------------------------------------

    function populateConfirmation(time) {
        const dateObj = new Date(selectedDate + 'T00:00:00');

        document.getElementById('confirmTreatment').textContent =
            selectedTreatment.name;
        document.getElementById('confirmDate').textContent =
            dateObj.toLocaleDateString('en-GB', {
                weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
            });
        document.getElementById('confirmTime').textContent     = time;
        document.getElementById('confirmDuration').textContent = selectedTreatment.duration + ' minutes';
        document.getElementById('confirmPrice').textContent    = '£' + selectedTreatment.price;

        // Populate hidden form fields — note slot_id is gone, we now
        // send treatment_id + date + start_time instead
        document.getElementById('hiddenTreatmentId').value = selectedTreatment.id;
        document.getElementById('hiddenDate').value        = selectedDate;
        document.getElementById('hiddenStartTime').value   = time;

        if (selectedTreatment.requiresDeposit) {
            document.getElementById('depositNotice').style.display = 'flex';
            document.getElementById('depositAmount').textContent   = '£' + selectedTreatment.depositAmount;
        } else {
            document.getElementById('depositNotice').style.display = 'none';
        }
    }

    // ---------------------------------------------------------------
    // Utility
    // ---------------------------------------------------------------

    function formatDate(d) {
        return (
            d.getFullYear() + '-' +
            String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0')
        );
    }

    // ---------------------------------------------------------------
    // Success state
    // ---------------------------------------------------------------

    if (typeof BOOKING_SUCCESS !== 'undefined' && BOOKING_SUCCESS) {
        document.querySelectorAll('.booking-step')
            .forEach(el => el.classList.add('booking-step--hidden'));
        document.getElementById('step-success')
            .classList.remove('booking-step--hidden');
    }

});