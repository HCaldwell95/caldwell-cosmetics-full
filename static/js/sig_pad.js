(function () {
    function initPad(canvasId, clearId, dataId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return { hasData: () => false };

        const ctx    = canvas.getContext('2d');
        const hidden = document.getElementById(dataId);
        let drawing = false;
        let hasSig  = false;

        function resize() {
            canvas.width  = canvas.offsetWidth;
            canvas.height = 160;
            ctx.strokeStyle = '#1a1a2e';
            ctx.lineWidth   = 2;
            ctx.lineCap     = 'round';
            ctx.lineJoin    = 'round';
        }
        resize();
        window.addEventListener('resize', resize);

        function pos(e) {
            const r = canvas.getBoundingClientRect();
            const t = e.touches ? e.touches[0] : e;
            return { x: t.clientX - r.left, y: t.clientY - r.top };
        }

        canvas.addEventListener('mousedown',  e => { drawing = true; ctx.beginPath(); const p = pos(e); ctx.moveTo(p.x, p.y); });
        canvas.addEventListener('mousemove',  e => { if (!drawing) return; const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); hasSig = true; });
        canvas.addEventListener('mouseup',    () => { drawing = false; if (hidden) hidden.value = canvas.toDataURL(); });
        canvas.addEventListener('mouseleave', () => { drawing = false; });
        canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; ctx.beginPath(); const p = pos(e); ctx.moveTo(p.x, p.y); }, { passive: false });
        canvas.addEventListener('touchmove',  e => { e.preventDefault(); if (!drawing) return; const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); hasSig = true; }, { passive: false });
        canvas.addEventListener('touchend',   () => { drawing = false; if (hidden) hidden.value = canvas.toDataURL(); });

        const clearBtn = document.getElementById(clearId);
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                if (hidden) hidden.value = '';
                hasSig = false;
            });
        }

        return { hasData: () => hasSig };
    }

    const main     = initPad('sigCanvas',         'sigClear',         'sigData');
    const guardian = initPad('guardianSigCanvas', 'guardianSigClear', 'guardianSigData');

    const form = document.querySelector('form.cform');
    if (form) {
        form.addEventListener('submit', function (e) {
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
