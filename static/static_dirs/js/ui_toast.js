/*
 * Уведомления (toast) в общем стиле приложения.
 *   notify.success('Сохранено'), notify.error(...), notify.info(...), notify.warning(...)
 * Совместимо со старыми вызовами toastr: toastr["success"](msg), toastr.error(msg, title).
 * Серверные сообщения Django (_messages.html → .js-flash) показываются автоматически.
 */
(function (window, document) {
    'use strict';

    var ICONS = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    var TITLES = {success: 'Готово', error: 'Ошибка', warning: 'Внимание', info: 'Сообщение'};
    var TIMEOUTS = {success: 4000, info: 5000, warning: 7000, error: 8000};
    var MAX_VISIBLE = 4;

    function container() {
        var el = document.getElementById('ui-toasts');
        if (!el) {
            el = document.createElement('div');
            el.id = 'ui-toasts';
            el.className = 'ui-toasts';
            el.setAttribute('aria-live', 'polite');
            document.body.appendChild(el);
        }
        return el;
    }

    function normalizeLevel(level) {
        level = String(level || 'info').toLowerCase();
        if (level === 'danger') return 'error';
        return ICONS[level] ? level : 'info';
    }

    function close(toast) {
        if (!toast || toast.classList.contains('is-leaving')) return;
        clearTimeout(toast._timer);
        toast.classList.add('is-leaving');
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 220);
    }

    function show(level, message, title) {
        level = normalizeLevel(level);
        if (!message && !title) return null;

        var box = container();
        while (box.children.length >= MAX_VISIBLE) close(box.firstElementChild);

        var toast = document.createElement('div');
        toast.className = 'ui-toast ui-toast--' + level;
        toast.setAttribute('role', level === 'error' ? 'alert' : 'status');

        var icon = document.createElement('i');
        icon.className = 'fas ' + ICONS[level] + ' ui-toast__icon';
        icon.setAttribute('aria-hidden', 'true');

        var body = document.createElement('div');
        body.className = 'ui-toast__body';
        var heading = document.createElement('div');
        heading.className = 'ui-toast__title';
        heading.textContent = title || TITLES[level];
        var text = document.createElement('div');
        text.className = 'ui-toast__text';
        text.textContent = message || '';
        body.appendChild(heading);
        if (message) body.appendChild(text);

        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'ui-toast__close';
        closeBtn.setAttribute('aria-label', 'Закрыть');
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', function () { close(toast); });

        var progress = document.createElement('span');
        progress.className = 'ui-toast__progress';
        progress.style.animationDuration = TIMEOUTS[level] + 'ms';

        toast.appendChild(icon);
        toast.appendChild(body);
        toast.appendChild(closeBtn);
        toast.appendChild(progress);
        box.appendChild(toast);

        var remaining = TIMEOUTS[level];
        var startedAt;
        function start() {
            startedAt = Date.now();
            toast._timer = setTimeout(function () { close(toast); }, remaining);
            toast.classList.remove('is-paused');
        }
        // Наведение мышью останавливает таймер — сообщение можно спокойно дочитать.
        toast.addEventListener('mouseenter', function () {
            clearTimeout(toast._timer);
            remaining -= Date.now() - startedAt;
            toast.classList.add('is-paused');
        });
        toast.addEventListener('mouseleave', start);
        start();
        return toast;
    }

    var notify = {
        show: show,
        success: function (m, t) { return show('success', m, t); },
        error: function (m, t) { return show('error', m, t); },
        warning: function (m, t) { return show('warning', m, t); },
        info: function (m, t) { return show('info', m, t); },
        clear: function () {
            var box = document.getElementById('ui-toasts');
            if (box) Array.prototype.slice.call(box.children).forEach(close);
        }
    };
    notify.remove = notify.clear;
    notify.options = {};

    window.notify = notify;
    // Совместимость со старым кодом, вызывающим toastr.
    window.toastr = notify;

    function showServerMessages() {
        document.querySelectorAll('.js-flash').forEach(function (el) {
            show(el.getAttribute('data-level'), el.textContent.trim());
            el.parentNode.removeChild(el);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', showServerMessages);
    } else {
        showServerMessages();
    }
})(window, document);
