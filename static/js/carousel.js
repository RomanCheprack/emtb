// Splide carousel for "popular bikes" section.
//
// Splide CSS+JS are lazy-loaded only when the carousel scrolls near the
// viewport. This keeps ~50 KB of CSS/JS off the critical path on first
// paint, which directly improves LCP/TBT on the home page.

(function () {
    var SPLIDE_CSS = 'https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.4/dist/css/splide.min.css';
    var SPLIDE_JS  = 'https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.4/dist/js/splide.min.js';

    var loaded = false;

    function loadStylesheet(href) {
        return new Promise(function (resolve) {
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            link.onload = link.onerror = function () { resolve(); };
            document.head.appendChild(link);
        });
    }

    function loadScript(src) {
        return new Promise(function (resolve, reject) {
            var s = document.createElement('script');
            s.src = src;
            s.async = true;
            s.onload = function () { resolve(); };
            s.onerror = function () { reject(new Error('Failed to load ' + src)); };
            document.head.appendChild(s);
        });
    }

    function initSplide(el) {
        if (!window.Splide) return;
        new window.Splide(el, {
            type: 'loop',
            perPage: 3,
            perMove: 1,
            gap: '20px',
            padding: { left: '40px', right: '40px' },
            breakpoints: {
                1024: { perPage: 2 },
                768:  { perPage: 1 }
            },
            direction: 'rtl'
        }).mount();
    }

    function loadAndInit(el) {
        if (loaded) return;
        loaded = true;
        // CSS first so the slides have correct dimensions when JS mounts.
        loadStylesheet(SPLIDE_CSS).then(function () {
            return loadScript(SPLIDE_JS);
        }).then(function () {
            initSplide(el);
        }).catch(function (err) {
            console.error(err);
        });
    }

    function setup() {
        var el = document.querySelector('#popular-bikes-splide');
        if (!el) return;

        if (!('IntersectionObserver' in window)) {
            // Old browser: just load straight away.
            loadAndInit(el);
            return;
        }

        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    io.disconnect();
                    loadAndInit(el);
                }
            });
        }, { rootMargin: '300px 0px' }); // start loading 300px before it scrolls in

        io.observe(el);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
})();
