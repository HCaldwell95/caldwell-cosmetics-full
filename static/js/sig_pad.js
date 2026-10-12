(function () {
    function initPad(canvasId, clearId, dataId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return { hasData: () => false, save: () => {} };

        const ctx    = canvas.getContext('2d');
        const hidden = document.getElementById(dataId);
        let drawing = false;
        let hasSig  = false;

        function save() {
            if (hasSig && hidden) hidden.value = canvas.toDataURL();
        }

        function resize(force) {
            // Resizing a canvas wipes it. Mobile browsers fire resize when
            // the address bar shows/hides on scroll, so only resize when the
            // width really changes, and redraw what was there.
            const width = canvas.offsetWidth;
            if (!force && (!width || width === canvas.width)) return;
            let saved = null;
            if (hasSig) {
                saved = document.createElement('canvas');
                saved.width = canvas.width;
                saved.height = canvas.height;
                saved.getContext('2d').drawImage(canvas, 0, 0);
            }
            canvas.width  = width;
            canvas.height = 160;
            ctx.strokeStyle = '#1a1a2e';
            ctx.lineWidth   = 2;
            ctx.lineCap     = 'round';
            ctx.lineJoin    = 'round';
            if (saved) ctx.drawImage(saved, 0, 0);
        }
        resize(true);
        window.addEventListener('resize', () => resize(false));

        function pos(e) {
            const r = canvas.getBoundingClientRect();
            const t = e.touches ? e.touches[0] : e;
            return { x: t.clientX - r.left, y: t.clientY - r.top };
        }

        // Pads inside hidden sections (e.g. guardian) start 0px wide — size
        // them properly the first time someone draws.
        canvas.addEventListener('mousedown',  () => resize(false));
        canvas.addEventListener('touchstart', () => resize(false), { passive: true });
        canvas.addEventListener('mousedown',  e => { drawing = true; ctx.beginPath(); const p = pos(e); ctx.moveTo(p.x, p.y); });
        canvas.addEventListener('mousemove',  e => { if (!drawing) return; const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); hasSig = true; });
        canvas.addEventListener('mouseup',    () => { drawing = false; save(); });
        canvas.addEventListener('mouseleave', () => { drawing = false; save(); });
        canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; ctx.beginPath(); const p = pos(e); ctx.moveTo(p.x, p.y); }, { passive: false });
        canvas.addEventListener('touchmove',  e => { e.preventDefault(); if (!drawing) return; const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); hasSig = true; }, { passive: false });
        canvas.addEventListener('touchend',   () => { drawing = false; save(); });

        const clearBtn = document.getElementById(clearId);
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                if (hidden) hidden.value = '';
                hasSig = false;
            });
        }

        return { hasData: () => hasSig, save: save };
    }

    const main     = initPad('sigCanvas',         'sigClear',         'sigData');
    const guardian = initPad('guardianSigCanvas', 'guardianSigClear', 'guardianSigData');

    const form = document.querySelector('form.cform');
    if (form) {
        form.addEventListener('submit', function (e) {
            // "Save progress" buttons don't need a signature.
            if (e.submitter && e.submitter.hasAttribute('data-no-signature')) return;
            // Always copy the drawn signature into the form on submit, in
            // case a stroke ended somewhere that didn't trigger a save.
            main.save();
            guardian.save();
            if (!main.hasData()) {
                e.preventDefault();
                alert('Please provide your signature before submitting.');
                return;
            }
            const guardianSection = document.getElementById('guardianSection');
            const guardianVisible = guardianSection && !guardianSection.hidden;
            if (guardianVisible && !guardian.hasData()) {
                e.preventDefault();
                alert('A parent or guardian signature is required for clients under 18.');
            }
        });
    }
})();
