(function() {
    const canvas  = document.getElementById('sigCanvas');
    const ctx     = canvas.getContext('2d');
    const sigData = document.getElementById('sigData');
    let drawing   = false;
    let hasSig    = false;

    function resize() {
        const w = canvas.offsetWidth;
        canvas.width  = w;
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
    canvas.addEventListener('mouseup',    () => { drawing = false; sigData.value = canvas.toDataURL(); });
    canvas.addEventListener('mouseleave', () => { drawing = false; });
    canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; ctx.beginPath(); const p = pos(e); ctx.moveTo(p.x, p.y); }, { passive: false });
    canvas.addEventListener('touchmove',  e => { e.preventDefault(); if (!drawing) return; const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); hasSig = true; }, { passive: false });
    canvas.addEventListener('touchend',   () => { drawing = false; sigData.value = canvas.toDataURL(); });

    document.getElementById('sigClear').addEventListener('click', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        sigData.value = '';
        hasSig = false;
    });

    const form = canvas.closest('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!hasSig) {
                e.preventDefault();
                alert('Please provide your signature before submitting.');
            }
        });
    }
})();