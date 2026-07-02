/**
 * client-panel.js
 * Shared profile panel, bundle modal, and credit modal logic.
 * Loaded on both the dashboard and clients pages before page-specific scripts.
 * Requires: DASHBOARD_URLS and CSRF_TOKEN globals defined by the page.
 */

function esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function safeColour(c) {
    return (c || '').replace(/[^a-zA-Z0-9#()%., ]/g, '');
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------

let _toastTimer = null;

function showToast(message, type) {
    type = type || 'success';
    const el = document.getElementById('dashToast');
    if (!el) return;
    el.textContent = message;
    el.className = 'dash-toast dash-toast--' + type + ' dash-toast--visible';
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function () {
        el.classList.remove('dash-toast--visible');
    }, 3500);
}

// ---------------------------------------------------------------------------
// Modal helpers (used by profile panel AND booking modal in dashboard.js)
// ---------------------------------------------------------------------------

function openModal(overlay) {
    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal(overlay) {
    overlay.style.display = 'none';
    document.body.style.overflow = '';
}

// ---------------------------------------------------------------------------
// Profile panel state
// ---------------------------------------------------------------------------

let activePanelUserId = null;

// ---------------------------------------------------------------------------
// Profile panel — open / close
// ---------------------------------------------------------------------------

function openProfilePanel(userId) {
    activePanelUserId = userId;

    const profilePanel     = document.getElementById('profilePanel');
    const profileOverlay   = document.getElementById('profileOverlay');
    const profilePanelBody = document.getElementById('profilePanelBody');
    const panelName        = document.getElementById('panelName');
    const panelEmail       = document.getElementById('panelEmail');

    if (!profilePanel) return;

    profilePanel.classList.add('dash-profile-panel--open');
    profileOverlay.style.display  = 'block';
    document.body.style.overflow  = 'hidden';
    profilePanelBody.innerHTML    = '<div class="dash-profile-loading">Loading…</div>';
    panelName.textContent  = '—';
    panelEmail.textContent = '—';

    fetch(DASHBOARD_URLS.clientProfile.replace('{id}', userId))
        .then(function (r) { return r.json(); })
        .then(function (data) { renderProfilePanel(data); });
}

function closeProfilePanel() {
    const profilePanel   = document.getElementById('profilePanel');
    const profileOverlay = document.getElementById('profileOverlay');
    if (!profilePanel) return;
    profilePanel.classList.remove('dash-profile-panel--open');
    profileOverlay.style.display = 'none';
    document.body.style.overflow = '';
    activePanelUserId = null;
}

// ---------------------------------------------------------------------------
// Profile panel — render
// ---------------------------------------------------------------------------

function renderProfilePanel(data) {
    const profilePanelBody = document.getElementById('profilePanelBody');
    const panelName        = document.getElementById('panelName');
    const panelEmail       = document.getElementById('panelEmail');
    const panelEditBtn     = document.getElementById('panelEditBtn');

    const u       = data.user;
    const forms   = data.forms;
    const bundles = data.bundles;
    const credit  = data.credit;

    panelName.textContent  = u.name;
    panelEmail.textContent = u.email;
    profilePanel_store_userId(u.id);

    function pill(label, state, href, subline) {
        var cls = state === 'complete'  ? 'dash-form-pill--complete'
                : state === 'archived'  ? 'dash-form-pill--archived'
                :                         'dash-form-pill--incomplete';
        var sub   = '<span class="dash-form-pill__sub">' + subline + '</span>';
        var inner = '<span class="dash-form-pill__name">' + label + '</span>' + sub;
        if (href) {
            return '<a href="' + href + '" class="dash-form-pill ' + cls + '" target="_blank">' + inner + '</a>';
        }
        return '<span class="dash-form-pill ' + cls + '">' + inner + '</span>';
    }

    function archiveToggle(toggleId, contentId, archiveHtml) {
        if (!archiveHtml) return '';
        var chevron = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>';
        return '<button class="dash-collapsible-toggle dash-archive-toggle" id="' + toggleId + '" style="margin-top:0.5rem;">Previous ' + chevron + '</button>'
             + '<div id="' + contentId + '" class="dash-form-pills" style="display:none;margin-top:0.4rem;">' + archiveHtml + '</div>';
    }

    // Consultation
    function mkConsultPill(f, archived) {
        var href  = DASHBOARD_URLS.formConsultationView.replace('{id}', u.id) + '?form_pk=' + f.id;
        var label = f.by_practitioner ? 'Consultation (Operator-assisted)' : 'Consultation';
        return pill(label, archived ? 'archived' : 'complete', href, 'Completed ' + f.date);
    }
    var consultCurrentPills = forms.consultation.forms.length
        ? mkConsultPill(forms.consultation.forms[0], false)
        : pill('Consultation', 'incomplete', null, 'Not completed');
    var consultArchivePills = forms.consultation.forms.slice(1).map(function (f) { return mkConsultPill(f, true); }).join('');

    // Photography
    function mkPhotoPill(f, archived) {
        var label = f.by_practitioner ? 'Photography (Operator-assisted)' : 'Photography';
        return pill(label, archived ? 'archived' : 'complete', DASHBOARD_URLS.formPhotography.replace('{id}', u.id), 'Completed ' + f.date);
    }
    var photoCurrentPills = forms.photography.forms.length
        ? mkPhotoPill(forms.photography.forms[0], false)
        : pill('Photography Consent', 'incomplete', null, 'Not completed');
    var photoArchivePills = forms.photography.forms.slice(1).map(function (f) { return mkPhotoPill(f, true); }).join('');

    // Botox
    function mkBotoxPill(f, archived) {
        var opHref = DASHBOARD_URLS.botoxOperator.replace('{id}', f.id);
        if (f.fully_complete) return pill('Anti-Wrinkle Consent — ' + f.date, archived ? 'archived' : 'complete', opHref, 'Client ✓ · Operator ✓');
        if (f.client_signed)  return pill('Anti-Wrinkle Consent — ' + f.date, 'incomplete', opHref, 'Client ✓ · Awaiting operator');
        return pill('Anti-Wrinkle Consent — ' + f.date, 'incomplete', null, 'Incomplete');
    }
    var botoxCurrentPills = forms.botox.forms.length
        ? mkBotoxPill(forms.botox.forms[0], false)
        : pill('Anti-Wrinkle Consent', 'incomplete', null, 'Not completed');
    var botoxArchivePills = forms.botox.forms.slice(1).map(function (f) { return mkBotoxPill(f, true); }).join('');

    // PRP
    function mkPrpPill(f, archived) {
        var opHref = DASHBOARD_URLS.prpOperator.replace('{id}', f.id);
        if (f.fully_complete) return pill('PRP Consent — ' + f.date, archived ? 'archived' : 'complete', opHref, 'Client ✓ · Operator ✓');
        if (f.client_signed)  return pill('PRP Consent — ' + f.date, 'incomplete', opHref, 'Client ✓ · Awaiting operator');
        return pill('PRP Consent — ' + f.date, 'incomplete', null, 'Incomplete');
    }
    var prpCurrentPills = forms.prp.forms.length
        ? mkPrpPill(forms.prp.forms[0], false)
        : pill('PRP Consent', 'incomplete', null, 'Not completed');
    var prpArchivePills = forms.prp.forms.slice(1).map(function (f) { return mkPrpPill(f, true); }).join('');

    // Laser
    function mkLaserPill(f, archived) {
        var href = DASHBOARD_URLS.laserReconsentView.replace('{id}', f.id);
        if (f.operator_signed) return pill('Laser Re-Consent — ' + f.date, archived ? 'archived' : 'complete', href, 'Client ✓ · Operator ✓');
        if (f.client_signed)   return pill('Laser Re-Consent — ' + f.date, 'incomplete', href, 'Client ✓ · Awaiting operator');
        return pill('Laser Re-Consent — ' + f.date, 'incomplete', null, 'Incomplete');
    }
    var laserCurrentPills = forms.laser_reconsent.forms.length
        ? mkLaserPill(forms.laser_reconsent.forms[0], false)
        : pill('Laser Re-Consent', 'incomplete', null, 'No re-consents on file');
    var laserArchivePills = forms.laser_reconsent.forms.slice(1).map(function (f) { return mkLaserPill(f, true); }).join('');

    // Bundle pips
    function bundlePips(b) {
        var html = '';
        for (var i = 0; i < b.total_sessions; i++) {
            html += '<span class="pip' + (i < b.sessions_used ? ' pip--used' : '') + '"></span>';
        }
        return html;
    }

    var bundlesHtml = bundles.length
        ? bundles.filter(function (b) { return b.status === 'active'; }).map(function (b) {
            return '<div class="dash-bundle-row">'
                + '<div class="dash-bundle-row__info">'
                + '<span class="dash-bundle-row__name">' + esc(b.treatment_name) + '</span>'
                + '<div class="dash-bundle-row__pips">' + bundlePips(b) + '</div>'
                + '<span class="dash-bundle-row__count">' + b.sessions_remaining + ' of ' + b.total_sessions + ' remaining</span>'
                + '</div>'
                + '<button class="btn btn--ghost btn--sm dash-bundle-use-btn" data-bundle-id="' + b.id + '" data-bundle-name="' + esc(b.treatment_name) + '">Use Session</button>'
                + '</div>';
          }).join('') || '<p class="dash-muted">No active bundles.</p>'
        : '<p class="dash-muted">No bundles.</p>';

    // Record cards
    var cardsHtml = data.record_cards.length
        ? data.record_cards.map(function (rc) {
            return '<a href="' + DASHBOARD_URLS.recordCardView.replace('{id}', rc.id) + '" target="_blank" class="dash-record-row">'
                + '<span class="dash-record-row__num">#' + rc.treatment_number + '</span>'
                + '<span class="dash-record-row__date">' + esc(rc.date) + '</span>'
                + '<span class="dash-record-row__treatment">' + (rc.treatment_for ? esc(rc.treatment_for) : '—') + '</span>'
                + '</a>';
          }).join('')
        : '<p class="dash-muted">No record cards yet.</p>';

    // Notes
    var notesHtml = (data.notes && data.notes.length)
        ? data.notes.map(function (n) {
            return '<a href="' + DASHBOARD_URLS.noteView.replace('{pk}', u.id).replace('{note_pk}', n.id) + '" target="_blank" class="dash-note-row">'
                + '<span class="dash-note-row__num">#' + n.number + '</span>'
                + '<span class="dash-note-row__title">' + esc(n.title) + '</span>'
                + '<span class="dash-note-row__date">' + esc(n.date) + '</span>'
                + '</a>';
          }).join('')
        : '<p class="dash-muted">No notes yet.</p>';

    var dobRaw = u.dob ? u.dob : '';
    var dobIso = '';
    if (dobRaw) {
        try { dobIso = new Date(dobRaw).toISOString().split('T')[0]; } catch(e) {}
    }
    var addrParts = u.address ? u.address.split('\n') : ['','','',''];

    profilePanelBody.innerHTML =
        // Personal details
        '<div class="dash-panel-section" id="panelViewMode">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Personal Details</h3></div>'
        + '<dl class="dash-panel-dl">'
        + '<dt>Phone</dt><dd>' + (u.phone ? esc(u.phone) : '—') + '</dd>'
        + '<dt>Date of birth</dt><dd>' + (u.dob ? esc(u.dob) : '—') + '</dd>'
        + '<dt>Skin type</dt><dd>' + (u.skin_type ? esc(u.skin_type) : '—') + '</dd>'
        + '<dt>Address</dt><dd>' + (u.address ? u.address.split('\n').map(esc).join('<br>') : '—') + '</dd>'
        + '<dt>GDPR consent</dt><dd>' + (u.gdpr_consent ? '✓ Given' : '✗ Not given') + '</dd>'
        + '</dl>'
        + '<div class="dash-panel-section__header" style="margin-top:1rem;"><h3 class="dash-panel-section__title">Medical Notes <span class="dash-operator-only">Operator only</span></h3></div>'
        + '<p class="dash-medical-notes">' + (u.medical_notes ? esc(u.medical_notes) : 'No notes on file.') + '</p>'
        + '</div>'

        // Edit mode
        + '<div class="dash-panel-section" id="panelEditMode" style="display:none;">'
        + '<h3 class="dash-panel-section__title">Edit Profile</h3>'
        + '<div class="cform-grid cform-grid--2" style="gap:0.75rem;">'
        + '<div class="dash-form-group"><label class="dash-label">First Name</label><input class="dash-input" id="editFirstName" value="' + esc(u.name.split(' ')[0] || '') + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Last Name</label><input class="dash-input" id="editLastName" value="' + esc(u.name.split(' ').slice(1).join(' ') || '') + '"></div>'
        + '<div class="dash-form-group" style="grid-column:1/-1;"><label class="dash-label">Email</label><input class="dash-input" type="email" id="editEmail" value="' + esc(u.email || '') + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Phone</label><input class="dash-input" id="editPhone" value="' + esc(u.phone || '') + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Date of Birth</label><input class="dash-input" type="date" id="editDob" value="' + dobIso + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Address Line 1</label><input class="dash-input" id="editAddr1" value="' + esc(addrParts[0] || '') + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Address Line 2</label><input class="dash-input" id="editAddr2" value="' + esc(addrParts[1] || '') + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Town / City</label><input class="dash-input" id="editCity" value="' + esc(addrParts[2] || '') + '"></div>'
        + '<div class="dash-form-group"><label class="dash-label">Postcode</label><input class="dash-input" id="editPostcode" value="' + esc(addrParts[3] || '') + '"></div>'
        + '<div class="dash-form-group" style="grid-column:1/-1;">'
        + '<label class="dash-label">Skin Type</label>'
        + '<select class="dash-input" id="editSkinType">'
        + '<option value="unknown"' + (u.skin_type_key === 'unknown' ? ' selected' : '') + '>Unknown / Not assessed</option>'
        + '<option value="type_1"'  + (u.skin_type_key === 'type_1'  ? ' selected' : '') + '>Type 1 – Always burns, never tans</option>'
        + '<option value="type_2"'  + (u.skin_type_key === 'type_2'  ? ' selected' : '') + '>Type 2 – Easily burns, eventually gets a moderate tan</option>'
        + '<option value="type_3"'  + (u.skin_type_key === 'type_3'  ? ' selected' : '') + '>Type 3 – Sometimes burns, quickly gets an average tan</option>'
        + '<option value="type_4"'  + (u.skin_type_key === 'type_4'  ? ' selected' : '') + '>Type 4 – Rarely burns, quickly gets a deep tan</option>'
        + '<option value="type_5"'  + (u.skin_type_key === 'type_5'  ? ' selected' : '') + '>Type 5 – Very rarely burns, consistent tan</option>'
        + '<option value="type_6"'  + (u.skin_type_key === 'type_6'  ? ' selected' : '') + '>Type 6 – Never burns, consistent tan</option>'
        + '</select>'
        + '</div>'
        + '<div class="dash-form-group" style="grid-column:1/-1;"><label class="dash-label">Medical Notes</label><textarea class="dash-input" id="editMedicalNotes" rows="3">' + esc(u.medical_notes || '') + '</textarea></div>'
        + '</div>'
        + '<div class="dash-modal__actions" style="padding:1rem 0 0;">'
        + '<button class="btn btn--ghost btn--sm" id="panelEditCancel">Cancel</button>'
        + '<button class="btn btn--primary btn--sm" id="panelEditSave">Save Changes</button>'
        + '</div>'
        + '</div>'

        // Upcoming bookings
        + '<div class="dash-panel-section"><h3 class="dash-panel-section__title">Upcoming Appointments</h3>'
        + (data.upcoming_bookings.length
            ? data.upcoming_bookings.map(function (b) {
                return '<div class="dash-appt-row">'
                    + '<span class="dash-appt-row__dot" style="background:' + (safeColour(b.category_colour) || 'var(--color-primary)') + '"></span>'
                    + '<div class="dash-appt-row__info">'
                    + '<span class="dash-appt-row__treatment">' + esc(b.treatment)
                    + '<span class="dash-appt-row__category" style="color:' + (safeColour(b.category_colour) || 'var(--color-primary)') + '">' + esc(b.category) + '</span>'
                    + '</span>'
                    + '<span class="dash-appt-row__date">' + esc(b.date) + ' at ' + esc(b.time) + '</span>'
                    + '</div>'
                    + '<span class="dash-appt-row__duration">' + b.duration + ' min</span>'
                    + '</div>';
              }).join('')
            : '<p class="dash-muted">No upcoming appointments.</p>')
        + '</div>'

        // Past bookings (collapsible)
        + '<div class="dash-panel-section">'
        + '<button class="dash-collapsible-toggle" id="pastBookingsToggle">Past Appointments '
        + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg></button>'
        + '<div id="pastBookingsContent" style="display:none;">'
        + (data.past_bookings.length
            ? data.past_bookings.map(function (b) {
                return '<div class="dash-appt-row dash-appt-row--past">'
                    + '<span class="dash-appt-row__dot" style="background:' + (safeColour(b.category_colour) || 'var(--color-primary)') + '"></span>'
                    + '<div class="dash-appt-row__info">'
                    + '<span class="dash-appt-row__treatment">' + esc(b.treatment)
                    + '<span class="dash-appt-row__category" style="color:' + (safeColour(b.category_colour) || 'var(--color-primary)') + '">' + esc(b.category) + '</span>'
                    + '</span>'
                    + '<span class="dash-appt-row__date">' + esc(b.date) + ' at ' + esc(b.time) + '</span>'
                    + '</div>'
                    + '<span class="dash-appt-badge dash-appt-badge--' + esc(b.status) + '">' + esc(b.status) + '</span>'
                    + '</div>';
              }).join('')
            : '<p class="dash-muted">No past appointments.</p>')
        + '</div></div>'

        // Forms: General
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">General</h3>'
        + '<div class="dash-form-launch">'
        + '<button class="dash-form-launch-btn" id="formPickerToggle">Create a new form '
        + '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg></button>'
        + '<div class="dash-form-dropdown" id="formPickerDropdown" hidden>'
        + '<a href="' + DASHBOARD_URLS.formConsultationNew.replace('{id}', u.id) + '" class="dash-form-dropdown__item" target="_blank">Consultation Form</a>'
        + '<a href="' + DASHBOARD_URLS.formBotoxClient.replace('{id}', u.id) + '" class="dash-form-dropdown__item" target="_blank">Botox Consent</a>'
        + '<a href="' + DASHBOARD_URLS.formPrpClient.replace('{id}', u.id) + '" class="dash-form-dropdown__item" target="_blank">PRP Consent</a>'
        + '<a href="' + DASHBOARD_URLS.formLaserReconsent.replace('{id}', u.id) + '" class="dash-form-dropdown__item" target="_blank">Laser Re-Consent</a>'
        + '</div></div></div>'
        + '<div class="dash-form-pills">' + consultCurrentPills + photoCurrentPills + '</div>'
        + archiveToggle('formArchiveGeneralToggle', 'formArchiveGeneralContent', consultArchivePills + photoArchivePills)
        + '</div>'

        // Forms: Injectables
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Injectables</h3></div>'
        + '<div class="dash-form-pills">' + botoxCurrentPills + prpCurrentPills + '</div>'
        + archiveToggle('formArchiveInjectablesToggle', 'formArchiveInjectablesContent', botoxArchivePills + prpArchivePills)
        + '</div>'

        // Forms: Laser
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Laser</h3></div>'
        + '<div class="dash-form-pills">' + laserCurrentPills + '</div>'
        + archiveToggle('formArchiveLaserToggle', 'formArchiveLaserContent', laserArchivePills)
        + '</div>'

        // Record cards
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Record Cards</h3>'
        + '<a href="' + DASHBOARD_URLS.recordCardNew.replace('{id}', u.id) + '" class="btn btn--ghost btn--sm" target="_blank">+ New Record Card</a>'
        + '</div><div class="dash-record-list">' + cardsHtml + '</div></div>'

        // Notes
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Notes</h3>'
        + '<a href="' + DASHBOARD_URLS.noteNew.replace('{id}', u.id) + '" class="btn btn--ghost btn--sm" target="_blank">+ New Note</a>'
        + '</div><div class="dash-notes-list">' + notesHtml + '</div></div>'

        // Bundles
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Pre-Paid Bundles</h3>'
        + '<button class="btn btn--ghost btn--sm" id="addBundleBtn">+ Add Bundle</button>'
        + '</div><div id="bundlesList">' + bundlesHtml + '</div></div>'

        // Credit
        + '<div class="dash-panel-section">'
        + '<div class="dash-panel-section__header"><h3 class="dash-panel-section__title">Account Credit</h3>'
        + '<button class="btn btn--ghost btn--sm" id="adjustCreditBtn">Adjust</button>'
        + '</div>'
        + '<p class="dash-credit-balance">£<span id="creditBalance">' + credit.balance + '</span></p>'
        + '<button class="dash-collapsible-toggle" id="creditHistoryToggle">Show history '
        + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg></button>'
        + '<div id="creditHistoryContent" style="display:none;margin-top:0.75rem;">'
        + (credit.transactions.length
            ? '<ul style="list-style:none;padding:0;margin:0;">'
              + credit.transactions.map(function (t) {
                  return '<li style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;border-bottom:1px solid #f0ece5;font-size:0.82rem;">'
                      + '<span style="color:#999;white-space:nowrap;min-width:72px;">' + esc(t.date) + '</span>'
                      + '<span style="flex:1;color:var(--color-text);">' + (esc(t.description) || (t.type === 'credit' ? 'Credit added' : t.type === 'deduct' ? 'Credit deducted' : 'Refund')) + '</span>'
                      + '<span style="font-weight:600;white-space:nowrap;color:' + (t.type === 'deduct' ? '#dc2626' : t.type === 'refund' ? '#2563eb' : '#16a34a') + ';">'
                      + (t.type === 'deduct' ? '−' : '+') + '£' + parseFloat(t.amount).toFixed(2)
                      + '</span></li>';
                }).join('')
              + '</ul>'
            : '<p class="dash-muted">No transactions yet.</p>')
        + '</div></div>';

    // Form picker dropdown
    var formPickerToggle   = document.getElementById('formPickerToggle');
    var formPickerDropdown = document.getElementById('formPickerDropdown');
    if (formPickerToggle && formPickerDropdown) {
        formPickerToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            var isHidden = formPickerDropdown.hasAttribute('hidden');
            formPickerDropdown.toggleAttribute('hidden', !isHidden);
            formPickerToggle.classList.toggle('dash-form-launch-btn--open', isHidden);
        });
        document.addEventListener('click', function closePicker(e) {
            if (!formPickerToggle.contains(e.target) && !formPickerDropdown.contains(e.target)) {
                formPickerDropdown.setAttribute('hidden', '');
                formPickerToggle.classList.remove('dash-form-launch-btn--open');
                document.removeEventListener('click', closePicker);
            }
        });
    }

    // Edit toggle
    if (panelEditBtn) {
        panelEditBtn.onclick = function () {
            document.getElementById('panelViewMode').style.display = 'none';
            document.getElementById('panelEditMode').style.display = 'block';
            panelEditBtn.style.display = 'none';
        };
    }

    document.getElementById('panelEditCancel').addEventListener('click', function () {
        document.getElementById('panelViewMode').style.display = 'block';
        document.getElementById('panelEditMode').style.display = 'none';
        if (panelEditBtn) panelEditBtn.style.display = 'inline-flex';
    });

    document.getElementById('panelEditSave').addEventListener('click', function () {
        var payload = {
            first_name:    document.getElementById('editFirstName').value,
            last_name:     document.getElementById('editLastName').value,
            email:         document.getElementById('editEmail').value,
            phone_number:  document.getElementById('editPhone').value,
            date_of_birth: document.getElementById('editDob').value,
            address_line_1: document.getElementById('editAddr1').value,
            address_line_2: document.getElementById('editAddr2').value,
            town_city:     document.getElementById('editCity').value,
            postcode:      document.getElementById('editPostcode').value,
            skin_type:     document.getElementById('editSkinType').value,
            medical_notes: document.getElementById('editMedicalNotes').value,
        };
        fetch(DASHBOARD_URLS.clientEdit.replace('{id}', u.id), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
            body: JSON.stringify(payload),
        })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.ok) openProfilePanel(u.id); });
    });

    // Archive toggles
    ['General', 'Injectables', 'Laser'].forEach(function (cat) {
        var toggle = document.getElementById('formArchive' + cat + 'Toggle');
        if (!toggle) return;
        toggle.addEventListener('click', function () {
            var content = document.getElementById('formArchive' + cat + 'Content');
            var open    = content.style.display !== 'none';
            content.style.display = open ? 'none' : 'block';
            this.classList.toggle('dash-collapsible-toggle--open', !open);
        });
    });

    // Past bookings toggle
    document.getElementById('pastBookingsToggle').addEventListener('click', function () {
        var content = document.getElementById('pastBookingsContent');
        var open    = content.style.display !== 'none';
        content.style.display = open ? 'none' : 'block';
        this.classList.toggle('dash-collapsible-toggle--open', !open);
    });

    // Credit history toggle
    document.getElementById('creditHistoryToggle').addEventListener('click', function () {
        var content = document.getElementById('creditHistoryContent');
        var open    = content.style.display !== 'none';
        content.style.display = open ? 'none' : 'block';
        this.classList.toggle('dash-collapsible-toggle--open', !open);
        this.innerHTML = (open ? 'Show' : 'Hide') + ' history <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transform:' + (open ? '' : 'rotate(180deg)') + '"><polyline points="6 9 12 15 18 9"/></svg>';
    });

    // Bundle use session
    profilePanelBody.querySelectorAll('.dash-bundle-use-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (!confirm('Mark one session as used for "' + btn.dataset.bundleName + '"?')) return;
            fetch(
                DASHBOARD_URLS.bundleUse.replace('{id}', u.id).replace('{bundle_id}', btn.dataset.bundleId),
                { method: 'POST', headers: { 'X-CSRFToken': CSRF_TOKEN } }
            )
            .then(function (r) { return r.json(); })
            .then(function (d) { if (d.ok) openProfilePanel(u.id); });
        });
    });

    // Add bundle
    document.getElementById('addBundleBtn').addEventListener('click', function () {
        openModal(document.getElementById('bundleModalOverlay'));
    });

    // Adjust credit
    document.getElementById('adjustCreditBtn').addEventListener('click', function () {
        openModal(document.getElementById('creditModalOverlay'));
    });
}

// ---------------------------------------------------------------------------
// Helper to persist user ID for bundle/credit modals
// ---------------------------------------------------------------------------

var _panelUserId = null;
function profilePanel_store_userId(id) { _panelUserId = id; }

// ---------------------------------------------------------------------------
// DOMContentLoaded — wire up panel close buttons + bundle/credit modals
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {

    var profileClose   = document.getElementById('profileClose');
    var profileOverlay = document.getElementById('profileOverlay');
    if (profileClose)   profileClose.addEventListener('click', closeProfilePanel);
    if (profileOverlay) profileOverlay.addEventListener('click', closeProfilePanel);

    // Bundle modal
    var bundleModalOverlay = document.getElementById('bundleModalOverlay');
    var bundleModalClose   = document.getElementById('bundleModalClose');
    var bundleModalCancel  = document.getElementById('bundleModalCancel');
    var bundleModalSave    = document.getElementById('bundleModalSave');

    if (bundleModalClose)  bundleModalClose.addEventListener('click',  function () { closeModal(bundleModalOverlay); });
    if (bundleModalCancel) bundleModalCancel.addEventListener('click', function () { closeModal(bundleModalOverlay); });

    if (bundleModalSave) {
        bundleModalSave.addEventListener('click', function () {
            var name     = document.getElementById('bundleTreatmentName').value.trim();
            var sessions = document.getElementById('bundleTotalSessions').value;
            var expiry   = document.getElementById('bundleExpiryDate').value;
            var notes    = document.getElementById('bundleNotes').value;
            var errEl    = document.getElementById('bundleError');
            errEl.textContent = '';

            if (!name || !sessions) { errEl.textContent = 'Treatment name and sessions are required.'; return; }

            bundleModalSave.disabled    = true;
            bundleModalSave.textContent = 'Saving…';

            var targetId = activePanelUserId;

            fetch(DASHBOARD_URLS.bundleAdd.replace('{id}', targetId), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({ treatment_name: name, total_sessions: sessions, expiry_date: expiry, notes: notes }),
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                bundleModalSave.disabled    = false;
                bundleModalSave.textContent = 'Add Bundle';
                if (data.ok) {
                    closeModal(bundleModalOverlay);
                    document.getElementById('bundleTreatmentName').value = '';
                    document.getElementById('bundleTotalSessions').value = '6';
                    document.getElementById('bundleExpiryDate').value    = '';
                    document.getElementById('bundleNotes').value         = '';
                    showToast('Bundle "' + name + '" added successfully.');
                    openProfilePanel(targetId);
                } else {
                    errEl.textContent = data.error || 'Something went wrong.';
                }
            })
            .catch(function () {
                bundleModalSave.disabled    = false;
                bundleModalSave.textContent = 'Add Bundle';
                document.getElementById('bundleError').textContent = 'Network error — please try again.';
            });
        });
    }

    // Credit modal
    var creditModalOverlay = document.getElementById('creditModalOverlay');
    var creditModalClose   = document.getElementById('creditModalClose');
    var creditModalCancel  = document.getElementById('creditModalCancel');
    var creditModalSave    = document.getElementById('creditModalSave');

    if (creditModalClose)  creditModalClose.addEventListener('click',  function () { closeModal(creditModalOverlay); });
    if (creditModalCancel) creditModalCancel.addEventListener('click', function () { closeModal(creditModalOverlay); });

    if (creditModalSave) {
        creditModalSave.addEventListener('click', function () {
            var type   = document.getElementById('creditType').value;
            var amount = document.getElementById('creditAmount').value;
            var desc   = document.getElementById('creditDescription').value;
            var errEl  = document.getElementById('creditError');
            errEl.textContent = '';

            if (!amount || parseFloat(amount) <= 0) { errEl.textContent = 'Please enter a valid amount.'; return; }

            creditModalSave.disabled    = true;
            creditModalSave.textContent = 'Saving…';

            var targetId = activePanelUserId;

            fetch(DASHBOARD_URLS.creditAdjust.replace('{id}', targetId), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
                body: JSON.stringify({ type: type, amount: amount, description: desc }),
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                creditModalSave.disabled    = false;
                creditModalSave.textContent = 'Confirm';
                if (data.ok) {
                    closeModal(creditModalOverlay);
                    document.getElementById('creditAmount').value      = '';
                    document.getElementById('creditDescription').value = '';
                    var typeLabel = type === 'credit' ? 'Credit added' : type === 'deduct' ? 'Credit deducted' : 'Refund applied';
                    showToast(typeLabel + ': £' + parseFloat(amount).toFixed(2));
                    openProfilePanel(targetId);
                } else {
                    errEl.textContent = data.error || 'Something went wrong.';
                }
            })
            .catch(function () {
                creditModalSave.disabled    = false;
                creditModalSave.textContent = 'Confirm';
                document.getElementById('creditError').textContent = 'Network error — please try again.';
            });
        });
    }
});
