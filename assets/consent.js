/*
 * Cloudberry VC cookie consent.
 * Google Tag Manager (and with it Google Analytics) is only loaded after the
 * visitor clicks Accept. The choice is stored in localStorage for 12 months.
 * Any element with class "cookie-settings" reopens the banner.
 */
(function () {
    var GTM_ID = 'GTM-5R376Z6C';
    var KEY = 'cb-cookie-consent';
    var MAX_AGE_MS = 365 * 24 * 60 * 60 * 1000;
    var gtmLoaded = false;

    function readChoice() {
        try {
            var raw = localStorage.getItem(KEY);
            if (!raw) return null;
            var c = JSON.parse(raw);
            if (!c || !c.t || Date.now() - c.t > MAX_AGE_MS) return null;
            return c.v === 'granted' || c.v === 'denied' ? c.v : null;
        } catch (e) { return null; }
    }

    function saveChoice(v) {
        try { localStorage.setItem(KEY, JSON.stringify({ v: v, t: Date.now() })); } catch (e) {}
    }

    function loadGTM() {
        if (gtmLoaded) return;
        gtmLoaded = true;
        (function (w, d, s, l, i) {
            w[l] = w[l] || []; w[l].push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
            var f = d.getElementsByTagName(s)[0], j = d.createElement(s), dl = l != 'dataLayer' ? '&l=' + l : '';
            j.async = true; j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl; f.parentNode.insertBefore(j, f);
        })(window, document, 'script', 'dataLayer', GTM_ID);
    }

    function clearAnalyticsCookies() {
        var host = location.hostname;
        var domains = ['', host, '.' + host, '.' + host.split('.').slice(-2).join('.')];
        document.cookie.split(';').forEach(function (c) {
            var name = c.split('=')[0].trim();
            if (/^(_ga|_gid|_gat)/.test(name)) {
                domains.forEach(function (d) {
                    document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + (d ? '; domain=' + d : '');
                });
            }
        });
    }

    var css = '' +
        '#cb-consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;max-width:880px;margin:0 auto;' +
        'background:#181D38;color:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.25);' +
        'padding:22px 24px;display:flex;gap:20px;align-items:center;font-family:inherit;font-size:.9rem;line-height:1.55}' +
        '#cb-consent[hidden]{display:none}' +
        '#cb-consent .cb-text{flex:1}' +
        '#cb-consent .cb-title{font-weight:700;font-size:1rem;margin:0 0 4px}' +
        '#cb-consent p{margin:0;color:rgba(255,255,255,.8)}' +
        '#cb-consent a{color:#FFBD48;text-decoration:underline;text-underline-offset:3px}' +
        '#cb-consent .cb-actions{display:flex;gap:10px;flex-shrink:0}' +
        '#cb-consent button{font:inherit;font-weight:600;font-size:.9rem;cursor:pointer;border-radius:100px;' +
        'padding:10px 22px;min-width:110px;background:#fff;color:#181D38;border:2px solid #fff}' +
        '#cb-consent button:hover{background:#FFBD48;border-color:#FFBD48}' +
        '#cb-consent button:focus-visible{outline:3px solid #FFBD48;outline-offset:2px}' +
        '@media (max-width:640px){#cb-consent{flex-direction:column;align-items:stretch;padding:20px}' +
        '#cb-consent .cb-actions button{flex:1}}';

    var banner;

    function buildBanner() {
        var style = document.createElement('style');
        style.textContent = css;
        document.head.appendChild(style);

        banner = document.createElement('div');
        banner.id = 'cb-consent';
        banner.setAttribute('role', 'dialog');
        banner.setAttribute('aria-label', 'Cookie consent');
        banner.hidden = true;
        banner.innerHTML =
            '<div class="cb-text">' +
                '<p class="cb-title">Cookies</p>' +
                '<p>We would like to use analytics cookies (Google Analytics) to understand how visitors use our site. ' +
                'They are only set if you accept. You can change your choice at any time via Cookie settings at the bottom of the page. ' +
                'Read more in our <a href="/privacy-policy.html">Privacy &amp; Cookie Policy</a>.</p>' +
            '</div>' +
            '<div class="cb-actions">' +
                '<button type="button" data-choice="denied">Reject</button>' +
                '<button type="button" data-choice="granted">Accept</button>' +
            '</div>';
        document.body.appendChild(banner);

        banner.addEventListener('click', function (e) {
            var btn = e.target.closest('button[data-choice]');
            if (!btn) return;
            var v = btn.getAttribute('data-choice');
            saveChoice(v);
            banner.hidden = true;
            if (v === 'granted') {
                loadGTM();
            } else {
                clearAnalyticsCookies();
                if (gtmLoaded) location.reload();
            }
        });
    }

    function openBanner() {
        if (!banner) buildBanner();
        banner.hidden = false;
    }

    function init() {
        document.addEventListener('click', function (e) {
            var link = e.target.closest('.cookie-settings');
            if (!link) return;
            e.preventDefault();
            openBanner();
        });
        var choice = readChoice();
        if (choice === 'granted') loadGTM();
        else if (choice === 'denied') clearAnalyticsCookies();
        else openBanner();
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
