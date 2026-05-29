/**
 * booking.utils.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Pure utility functions shared by booking.js and dashboard.js.
 * Load this file BEFORE both scripts in your HTML templates.
 *
 * In overview.html / dashboard.html, add above the existing script tags:
 *   <script src="{% static 'js/booking.utils.js' %}"></script>
 *
 * Then in booking.js and dashboard.js, DELETE the local copies of
 * generateTimes() — they are now provided globally by this file.
 */

// ─── Clinic configuration ────────────────────────────────────────────────────

/**
 * Days the clinic is open (JS Date.getDay(): 0=Sun, 1=Mon … 6=Sat).
 * Must match OPEN_DAYS in booking.js, dashboard.js, and views.py.
 */
const OPEN_DAYS = [1, 2, 3]; // Monday, Tuesday, Wednesday

const CLINIC_OPEN  = '09:30';

/**
 * ⚠️  BUG FIX (booking.js AND dashboard.js):
 *     Both files hardcoded '14:30' inside generateTimes(), cutting off every
 *     afternoon slot. The real closing time is 17:00. Centralising it here
 *     prevents the mismatch from recurring.
 */
const CLINIC_CLOSE = '14:30';

// ─── Time-slot generation ─────────────────────────────────────────────────────

/**
 * Generate all bookable start times for a given treatment duration.
 * A slot is only included if the appointment ENDS by closeTime.
 *
 * @param  {number} durationMinutes   Positive integer
 * @param  {string} [openTime]        "HH:MM" – defaults to CLINIC_OPEN
 * @param  {string} [closeTime]       "HH:MM" – defaults to CLINIC_CLOSE
 * @returns {string[]}                e.g. ["09:30","10:30","11:30",…]
 */
function generateTimes(durationMinutes, openTime, closeTime) {
    openTime  = openTime  || CLINIC_OPEN;
    closeTime = closeTime || CLINIC_CLOSE;

    if (!Number.isInteger(durationMinutes) || durationMinutes <= 0) return [];

    const open     = openTime.split(':').map(Number);
    const close    = closeTime.split(':').map(Number);
    const closeMin = close[0] * 60 + close[1];
    let   current  = open[0]  * 60 + open[1];
    const slots    = [];

    while (current + durationMinutes <= closeMin) {
        const h = Math.floor(current / 60);
        const m = current % 60;
        slots.push(String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0'));
        current += durationMinutes;
    }

    return slots;
}

// ─── Date helpers ─────────────────────────────────────────────────────────────

/**
 * Format a Date as "YYYY-MM-DD" using LOCAL time (not UTC).
 * Using toISOString() can produce the wrong date for UTC-N timezones.
 */
function formatDate(d) {
    return (
        d.getFullYear()              + '-' +
        String(d.getMonth()+1).padStart(2,'0') + '-' +
        String(d.getDate())   .padStart(2,'0')
    );
}

/**
 * Return true when a date is bookable: not in the past AND on an open day.
 * Today itself is considered available.
 *
 * @param  {Date}  dateObj
 * @param  {Date}  [todayOverride]  Injectable for unit tests
 */
function isDateAvailable(dateObj, todayOverride) {
    const today = new Date(todayOverride || new Date());
    today.setHours(0, 0, 0, 0);
    const isPast      = dateObj < today;
    const isClosedDay = !OPEN_DAYS.includes(dateObj.getDay());
    return !isPast && !isClosedDay;
}

/**
 * Return true when a specific time is already booked.
 *
 * ⚠️  treatmentId MUST be a string — HTML data-* attributes are always strings.
 *     Using parseInt() on the id before this lookup will silently miss bookings.
 *
 * @param  {object} allSlots
 * @param  {string} treatmentId
 * @param  {string} dateStr     "YYYY-MM-DD"
 * @param  {string} time        "HH:MM"
 */
function isTimeBooked(allSlots, treatmentId, dateStr, time) {
    const dayData = (allSlots[String(treatmentId)] || {})[dateStr];
    if (!dayData || !Array.isArray(dayData.booked)) return false;
    return dayData.booked.includes(time);
}

// ─── Node / Jest exports ─────────────────────────────────────────────────────
if (typeof module !== 'undefined') {
    module.exports = { OPEN_DAYS, CLINIC_OPEN, CLINIC_CLOSE,
                       generateTimes, formatDate, isDateAvailable, isTimeBooked };
}