'use strict';

// Тема Bootstrap (data-bs-theme) по системной настройке. Подключается синхронно в <head>
// до стилей, чтобы при загрузке не мелькала светлая тема.
(() => {
    const dark = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => document.documentElement.setAttribute('data-bs-theme', dark.matches ? 'dark' : 'light');
    apply();
    dark.addEventListener('change', apply);
})();
