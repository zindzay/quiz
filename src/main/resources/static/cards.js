'use strict';

const PAGE_SIZE = 10;
// При большем числе страниц панель сокращается: первая, последняя, текущая с соседями и «…».
const MAX_FULL_PAGES = 7;

const list = document.getElementById('cards');
const listStatus = document.getElementById('list-status');
const listEmpty = document.getElementById('list-empty');
const pagesNav = document.getElementById('pages');
const pagesBar = pagesNav.querySelector('.pagination');
const template = document.getElementById('card-template');

// Все карточки в порядке добавления; номер карточки — её позиция здесь, страница — срез по PAGE_SIZE.
let cards = [];
let page = 1;

function pageCount() {
    return Math.max(1, Math.ceil(cards.length / PAGE_SIZE));
}

// Номер страницы из адреса: нечисловой — первая, вне диапазона — ближайшая существующая.
function pageFromUrl() {
    const value = new URLSearchParams(location.search).get('page');
    const number = /^\d+$/.test(value ?? '') ? Number(value) : 1;
    return Math.min(Math.max(number, 1), pageCount());
}

// Исправленный номер записывается без новой записи в истории.
function syncUrl() {
    const value = new URLSearchParams(location.search).get('page');
    if (value !== null && value !== String(page)) {
        history.replaceState(null, '', `?page=${page}`);
    }
}

/** Номера страниц для панели: все, если их не больше MAX_FULL_PAGES, иначе с «…» на месте пропусков. */
function pageItems(current, total) {
    if (total <= MAX_FULL_PAGES) {
        return Array.from({ length: total }, (_, i) => i + 1);
    }
    const shown = [...new Set([1, current - 1, current, current + 1, total])]
        .filter((n) => n >= 1 && n <= total)
        .sort((a, b) => a - b);
    const items = [];
    shown.forEach((n, i) => {
        if (i > 0 && n - shown[i - 1] > 1) {
            items.push('…');
        }
        items.push(n);
    });
    return items;
}

// Текст карточек выводится только через textContent, чтобы HTML в нём не интерпретировался.
function renderCard(card, number) {
    const item = template.content.firstElementChild.cloneNode(true);
    item.querySelector('.quiz-number').textContent = `${number}.`;
    item.querySelector('.quiz-question').textContent = card.question;
    item.querySelector('.quiz-answer').textContent = card.answer;
    const toggleArea = item.querySelector('.quiz-toggle');
    toggleArea.addEventListener('click', () => toggle(item));
    toggleArea.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggle(item);
        }
    });
    setUpDelete(item, card.id);
    return item;
}

function pageLink(label, target, { current = false, disabled = false } = {}) {
    const item = document.createElement('span');
    item.className = 'page-item';
    const link = document.createElement('a');
    link.className = 'page-link';
    link.textContent = label;
    if (disabled) {
        item.classList.add('disabled');
        link.setAttribute('role', 'link');
        link.setAttribute('aria-disabled', 'true');
    } else {
        link.href = `?page=${target}`;
        link.dataset.page = String(target);
    }
    if (current) {
        item.classList.add('active');
        link.setAttribute('aria-current', 'page');
    }
    item.append(link);
    return item;
}

function renderPages() {
    const total = pageCount();
    pagesNav.hidden = cards.length <= PAGE_SIZE;
    if (pagesNav.hidden) {
        pagesBar.replaceChildren();
        return;
    }
    const items = [pageLink('Назад', page - 1, { disabled: page === 1 })];
    for (const n of pageItems(page, total)) {
        if (n === '…') {
            const gap = document.createElement('span');
            gap.className = 'page-item disabled';
            gap.innerHTML = '<span class="page-link">…</span>';
            items.push(gap);
        } else {
            items.push(pageLink(String(n), n, { current: n === page }));
        }
    }
    items.push(pageLink('Вперёд', page + 1, { disabled: page === total }));
    pagesBar.replaceChildren(...items);
}

function render() {
    const start = (page - 1) * PAGE_SIZE;
    list.replaceChildren(...cards.slice(start, start + PAGE_SIZE).map((card, i) => renderCard(card, start + i + 1)));
    renderPages();
    listStatus.hidden = cards.length === 0;
    listEmpty.hidden = cards.length !== 0;
}

// Переход по панели без перезагрузки; ссылки с модификаторами открываются браузером как обычно.
pagesBar.addEventListener('click', (event) => {
    const link = event.target.closest('a[data-page]');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
    }
    event.preventDefault();
    page = Number(link.dataset.page);
    history.pushState(null, '', `?page=${page}`);
    render();
    window.scrollTo(0, 0);
});

window.addEventListener('popstate', () => {
    page = pageFromUrl();
    syncUrl();
    render();
});

function toggle(item) {
    const revealed = item.classList.toggle('revealed');
    item.querySelector('.quiz-toggle').setAttribute('aria-expanded', String(revealed));
}

// Удаление с подтверждением на самой карточке; по умолчанию фокус на безопасной «Отмене».
function setUpDelete(item, id) {
    const deleteButton = item.querySelector('.quiz-delete');
    const confirm = item.querySelector('.quiz-confirm');
    const yes = item.querySelector('.quiz-confirm-yes');
    const cancel = item.querySelector('.quiz-confirm-cancel');
    const error = item.querySelector('.quiz-delete-error');

    function showConfirm(shown) {
        deleteButton.hidden = shown;
        confirm.hidden = !shown;
        (shown ? cancel : deleteButton).focus();
    }

    deleteButton.addEventListener('click', () => {
        error.hidden = true;
        showConfirm(true);
    });
    cancel.addEventListener('click', () => showConfirm(false));
    yes.addEventListener('click', async () => {
        yes.disabled = true;
        cancel.disabled = true;
        try {
            const response = await fetch(`/api/cards/${encodeURIComponent(id)}`, { method: 'DELETE' });
            // 404 — карточку уже удалили (например, в другой вкладке): результат тот же.
            if (!response.ok && response.status !== 404) {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (e) {
            yes.disabled = false;
            cancel.disabled = false;
            showConfirm(false);
            error.textContent = 'Не удалось удалить карточку. Проверьте, что сервер запущен, и попробуйте ещё раз.';
            error.hidden = false;
            return;
        }
        // Номера сдвигаются, со следующей страницы подтягивается карточка; опустевшая последняя — на предыдущую.
        cards = cards.filter((card) => card.id !== id);
        if (page > pageCount()) {
            page = pageCount();
            history.replaceState(null, '', `?page=${page}`);
        }
        render();
    });
}

async function loadCards() {
    listStatus.textContent = 'Загрузка…';
    try {
        const response = await fetch('/api/cards');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        cards = await response.json();
        listStatus.textContent = '';
        page = pageFromUrl();
        syncUrl();
        render();
    } catch (e) {
        listStatus.textContent = 'Не удалось загрузить карточки. Проверьте, что сервер запущен, и обновите страницу.';
    }
}

loadCards();
