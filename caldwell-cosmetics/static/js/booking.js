// booking.js

document.addEventListener('DOMContentLoaded', function () {

    // ─── Safe JSON Load ─────────────────────────────
    const bookedSlots = JSON.parse(
        document.getElementById('booked-slots-data').textContent
    );

    // ─── State ──────────────────────────────────────
    let selectedTreatment = null;
    let selectedDate = null;
    let selectedTime = null;
    let currentDate = new Date();

    const OPEN_DAYS = [1, 2, 3]; // Mon–Wed
    const OPEN_TIME = '09:30';
    const CLOSE_TIME = '14:30';

    // ─── Step Navigation ────────────────────────────
    function goToStep(stepNumber) {
        document.querySelectorAll('.booking-step').forEach(el => {
            el.classList.add('booking-step--hidden');
        });

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

    // ─── Treatment Selection ────────────────────────
    const categoryTabs = document.querySelectorAll('.category-tab');
    const treatmentCards = document.querySelectorAll('.treatment-card');

    categoryTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            categoryTabs.forEach(t => t.classList.remove('category-tab--active'));
            this.classList.add('category-tab--active');

            const catId = this.dataset.category;
            treatmentCards.forEach(card => {
                card.classList.toggle(
                    'treatment-card--hidden',
                    card.dataset.category !== catId
                );
            });
        });
    });

    if (categoryTabs.length > 0) categoryTabs[0].click();

    window.selectTreatment = function (card) {
        selectedTreatment = {
            id: card.dataset.treatmentId,
            name: card.dataset.treatmentName,
            duration: parseInt(card.dataset.duration),
            price: card.dataset.price,
            requiresDeposit: card.dataset.requiresDeposit === 'true',
            depositAmount: card.dataset.depositAmount
        };

        document.getElementById('stripTreatmentName').textContent = selectedTreatment.name;
        document.getElementById('stripDuration').textContent = selectedTreatment.duration + ' min';
        document.getElementById('stripPrice').textContent = '£' + selectedTreatment.price;

        goToStep(2);
        renderCalendar();
    };

    // ─── Calendar ───────────────────────────────────
    const calendarEl = document.getElementById('calendar');
    const monthLabel = document.getElementById('currentMonth');

    function renderCalendar() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        monthLabel.textContent = new Date(year, month)
            .toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });

        calendarEl.innerHTML = '';

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        for (let i = 0; i < firstDay; i++) {
            calendarEl.appendChild(document.createElement('div'));
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dayEl = document.createElement('div');
            dayEl.textContent = day;
            dayEl.classList.add('calendar-day');

            const dateObj = new Date(year, month, day);
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

            if (dateObj < today || !OPEN_DAYS.includes(dateObj.getDay())) {
                dayEl.classList.add('calendar-day--unavailable');
            } else {
                dayEl.classList.add('calendar-day--available');
                dayEl.addEventListener('click', () => selectDate(dateStr, dateObj, dayEl));
            }

            calendarEl.appendChild(dayEl);
        }
    }

    function selectDate(dateStr, dateObj, el) {
        selectedDate = dateStr;
        selectedTime = null;

        document.querySelectorAll('.calendar-day')
            .forEach(d => d.classList.remove('calendar-day--selected'));

        el.classList.add('calendar-day--selected');

        showTimeSlots(dateStr, dateObj);
    }

    function generateTimeSlots(open, close, interval, duration) {
        const slots = [];

        let [h, m] = open.split(':').map(Number);
        const [ch, cm] = close.split(':').map(Number);

        while (true) {
            const start = new Date(0, 0, 0, h, m);
            const end = new Date(start.getTime() + duration * 60000);
            const closing = new Date(0, 0, 0, ch, cm);

            if (end > closing) break;

            slots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);

            m += interval;
            if (m >= 60) { h++; m -= 60; }
        }

        return slots;
    }

    function showTimeSlots(dateStr, dateObj) {
        const grid = document.getElementById('timeslotGrid');
        const taken = bookedSlots[dateStr] || [];

        grid.innerHTML = '';

        const slots = generateTimeSlots(
            OPEN_TIME,
            CLOSE_TIME,
            30,
            selectedTreatment.duration
        );

        if (!slots.length) {
            grid.innerHTML = '<p>No availability for this day</p>';
            return;
        }

        slots.forEach(slot => {
            const el = document.createElement('div');
            el.textContent = slot;
            el.classList.add('timeslot');

            if (taken.includes(slot)) {
                el.classList.add('timeslot--booked');
            } else {
                el.addEventListener('click', () => selectTime(slot, el));
            }

            grid.appendChild(el);
        });
    }

    function selectTime(time, el) {
        selectedTime = time;

        document.querySelectorAll('.timeslot')
            .forEach(s => s.classList.remove('timeslot--selected'));

        el.classList.add('timeslot--selected');

        populateConfirmation();
        goToStep(3);
    }

    function populateConfirmation() {
        document.getElementById('confirmTreatment').textContent = selectedTreatment.name;
        document.getElementById('confirmDate').textContent = selectedDate;
        document.getElementById('confirmTime').textContent = selectedTime;
        document.getElementById('confirmDuration').textContent = selectedTreatment.duration + ' minutes';
        document.getElementById('confirmPrice').textContent = '£' + selectedTreatment.price;

        document.getElementById('hiddenTreatmentId').value = selectedTreatment.id;
        document.getElementById('hiddenDate').value = selectedDate;
        document.getElementById('hiddenTime').value = selectedTime;
    }

});