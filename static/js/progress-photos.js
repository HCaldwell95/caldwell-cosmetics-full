/*
 * Progress photos
 *   [data-pphotos]      a row of date boxes, cycled with the header arrows
 *   [data-photo-set]    one date's photos, cycled inside the box
 *   .pphotos-slide      click to open the full-screen viewer, which cycles
 *                       through that date's photos
 *   [data-photo-upload] practitioner upload: preview + label each file
 */
(function () {
    var CHEVRON_LEFT  = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>';
    var CHEVRON_RIGHT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>';
    var LABELS = { before: 'Before', after: 'After' };

    function stampHtml(label) {
        return LABELS[label] ? '<span class="pphoto-stamp pphoto-stamp--' + label + '">' + LABELS[label] + '</span>' : '';
    }

    // Left / right swipe on touch screens.
    function onSwipe(el, onLeft, onRight) {
        var startX = null;
        el.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
        el.addEventListener('touchend', function (e) {
            if (startX === null) return;
            var dx = e.changedTouches[0].clientX - startX;
            startX = null;
            if (Math.abs(dx) < 40) return;
            if (dx < 0) onLeft(); else onRight();
        });
    }

    // ---------------------------------------------------------------
    // Full-screen viewer (one shared element)
    // ---------------------------------------------------------------
    var viewer = null;

    function buildViewer() {
        var el = document.createElement('div');
        el.className = 'pphoto-lightbox';
        el.hidden = true;
        el.setAttribute('role', 'dialog');
        el.setAttribute('aria-modal', 'true');
        el.setAttribute('aria-label', 'Photo viewer');
        el.innerHTML =
              '<button type="button" class="pphoto-lightbox__close" aria-label="Close">&times;</button>'
            + '<button type="button" class="pphotos-arrow pphoto-lightbox__prev" aria-label="Previous photo">' + CHEVRON_LEFT + '</button>'
            + '<figure class="pphoto-lightbox__figure"><span class="pphoto-lightbox__stamp"></span><img class="pphoto-lightbox__img" alt=""></figure>'
            + '<p class="pphoto-lightbox__caption"></p>'
            + '<button type="button" class="pphotos-arrow pphoto-lightbox__next" aria-label="Next photo">' + CHEVRON_RIGHT + '</button>';
        document.body.appendChild(el);

        var state = { items: [], index: 0, title: '', onChange: null, returnFocus: null };
        var img     = el.querySelector('.pphoto-lightbox__img');
        var stamp   = el.querySelector('.pphoto-lightbox__stamp');
        var caption = el.querySelector('.pphoto-lightbox__caption');
        var prev    = el.querySelector('.pphoto-lightbox__prev');
        var next    = el.querySelector('.pphoto-lightbox__next');

        function show(i) {
            var n = state.items.length;
            state.index = (i + n) % n;
            var item = state.items[state.index];
            img.src = item.src;
            img.alt = item.alt;
            stamp.innerHTML = stampHtml(item.label);
            caption.innerHTML = state.title + (n > 1 ? ' <span>· ' + (state.index + 1) + ' of ' + n + '</span>' : '');
            prev.hidden = next.hidden = n < 2;
            if (state.onChange) state.onChange(state.index);
        }

        function close() {
            el.hidden = true;
            img.removeAttribute('src');
            document.body.style.overflow = '';
            if (state.returnFocus) state.returnFocus.focus();
        }

        prev.addEventListener('click', function () { show(state.index - 1); });
        next.addEventListener('click', function () { show(state.index + 1); });
        el.querySelector('.pphoto-lightbox__close').addEventListener('click', close);
        el.addEventListener('click', function (e) { if (e.target === el) close(); });
        onSwipe(el, function () { show(state.index + 1); }, function () { show(state.index - 1); });
        document.addEventListener('keydown', function (e) {
            if (el.hidden) return;
            if (e.key === 'Escape') close();
            else if (e.key === 'ArrowLeft') show(state.index - 1);
            else if (e.key === 'ArrowRight') show(state.index + 1);
        });

        return {
            open: function (items, index, title, onChange) {
                state.items = items;
                state.title = title;
                state.onChange = onChange || null;
                state.returnFocus = document.activeElement;
                el.hidden = false;
                document.body.style.overflow = 'hidden';
                show(index);
                el.querySelector('.pphoto-lightbox__close').focus();
            },
        };
    }

    function openViewer(items, index, title, onChange) {
        viewer = viewer || buildViewer();
        viewer.open(items, index, title, onChange);
    }

    function slideItems(slides) {
        return slides.map(function (s) {
            var img = s.querySelector('img');
            return { src: s.dataset.full, label: s.dataset.label, alt: img ? img.alt : '' };
        });
    }

    // ---------------------------------------------------------------
    // One date's photos, cycled inside its box
    // ---------------------------------------------------------------
    document.querySelectorAll('[data-photo-set]').forEach(function (set) {
        var slides = Array.prototype.slice.call(set.querySelectorAll('.pphotos-slide'));
        if (!slides.length) return;
        var title   = set.dataset.title || '';
        var dots    = Array.prototype.slice.call(set.querySelectorAll('.pphotos-dot'));
        var counter = set.querySelector('[data-photo-counter]');
        var index   = 0;
        var items   = slideItems(slides);

        function go(i) {
            var n = slides.length;
            slides[index].classList.remove('is-active');
            if (dots[index]) dots[index].classList.remove('is-active');
            index = (i + n) % n;
            slides[index].classList.add('is-active');
            if (dots[index]) dots[index].classList.add('is-active');
            if (counter) counter.textContent = (index + 1) + ' / ' + n;
        }

        var prev = set.querySelector('[data-photo-prev]');
        var next = set.querySelector('[data-photo-next]');
        if (prev) prev.addEventListener('click', function () { go(index - 1); });
        if (next) next.addEventListener('click', function () { go(index + 1); });
        dots.forEach(function (dot, i) { dot.addEventListener('click', function () { go(i); }); });
        var frame = set.querySelector('.pphotos-set__frame');
        if (frame && slides.length > 1) {
            onSwipe(frame, function () { go(index + 1); }, function () { go(index - 1); });
        }

        slides.forEach(function (slide, i) {
            // In a box only the active slide is visible; in the practitioner's
            // grid every tile is its own slide.
            slide.addEventListener('click', function () {
                openViewer(items, i, title, set.hasAttribute('data-photo-sync') ? go : null);
            });
        });
    });

    // ---------------------------------------------------------------
    // The row of date boxes, cycled with the header arrows
    // ---------------------------------------------------------------
    document.querySelectorAll('[data-pphotos]').forEach(function (section) {
        var track = section.querySelector('[data-pphotos-track]');
        var nav   = section.querySelector('[data-pphotos-nav]');
        var prev  = section.querySelector('[data-pphotos-prev]');
        var next  = section.querySelector('[data-pphotos-next]');
        var count = section.querySelector('[data-pphotos-count]');
        var boxes = track ? track.children : [];
        if (!track || !boxes.length) return;

        function step() {
            var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
            return boxes[0].getBoundingClientRect().width + gap;
        }

        function update() {
            var s       = step();
            var visible = Math.max(1, Math.round((track.clientWidth + (parseFloat(getComputedStyle(track).columnGap) || 0)) / s));
            var first   = Math.round(track.scrollLeft / s);
            var last    = Math.min(boxes.length, first + visible);
            nav.hidden  = boxes.length <= visible;
            prev.disabled = first <= 0;
            next.disabled = last >= boxes.length;
            count.textContent = visible === 1
                ? (first + 1) + ' of ' + boxes.length
                : (first + 1) + '–' + last + ' of ' + boxes.length;
        }

        prev.addEventListener('click', function () { track.scrollBy({ left: -step(), behavior: 'smooth' }); });
        next.addEventListener('click', function () { track.scrollBy({ left: step(), behavior: 'smooth' }); });

        var pending = false;
        track.addEventListener('scroll', function () {
            if (pending) return;
            pending = true;
            requestAnimationFrame(function () { pending = false; update(); });
        });
        window.addEventListener('resize', update);
        update();
    });

    // ---------------------------------------------------------------
    // Practitioner upload: preview each chosen photo and pick its label
    // ---------------------------------------------------------------
    document.querySelectorAll('[data-photo-upload]').forEach(function (form) {
        var input    = form.querySelector('input[type="file"]');
        var list     = form.querySelector('[data-photo-upload-list]');
        var labelAll = form.querySelector('[name="default_label"]');
        var options  = labelAll ? labelAll.innerHTML : '';
        var urls     = [];

        function render() {
            urls.forEach(URL.revokeObjectURL);
            urls = [];
            list.innerHTML = '';
            Array.prototype.forEach.call(input.files, function (file, i) {
                var url = URL.createObjectURL(file);
                urls.push(url);
                var row = document.createElement('div');
                row.className = 'pphoto-upload-row';
                row.innerHTML = '<img alt="">'
                    + '<span class="pphoto-upload-row__name"></span>'
                    + '<select class="cform-input" name="label_' + i + '" aria-label="Label">' + options + '</select>';
                var img = row.querySelector('img');
                img.src = url;
                img.onerror = function () { img.removeAttribute('src'); };  // e.g. HEIC: no preview
                row.querySelector('.pphoto-upload-row__name').textContent = file.name;
                row.querySelector('select').value = labelAll ? labelAll.value : '';
                list.appendChild(row);
            });
        }

        input.addEventListener('change', render);
        if (labelAll) {
            labelAll.addEventListener('change', function () {
                list.querySelectorAll('select').forEach(function (s) { s.value = labelAll.value; });
            });
        }
        form.addEventListener('submit', function () {
            var btn = form.querySelector('[type="submit"]');
            if (btn) { btn.disabled = true; btn.textContent = 'Uploading…'; }
        });
    });

    // Label changes save straight away.
    document.querySelectorAll('[data-autosubmit]').forEach(function (select) {
        select.addEventListener('change', function () { select.form.submit(); });
    });
})();
