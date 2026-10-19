'use strict';

const list = document.getElementById('cards');
const listStatus = document.getElementById('list-status');
const listEmpty = document.getElementById('list-empty');
const template = document.getElementById('card-template');

// Текст карточек выводится только через textContent, чтобы HTML в нём не интерпретировался.
function renderCard(card) {
    const item = template.content.firstElementChild.cloneNode(true);
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
    list.append(item);
}

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
            item.remove();
            if (list.children.length === 0) {
                listStatus.hidden = true;
                listEmpty.hidden = false;
            }
        } catch (e) {
            yes.disabled = false;
            cancel.disabled = false;
            showConfirm(false);
            error.textContent = 'Не удалось удалить карточку. Проверьте, что сервер запущен, и попробуйте ещё раз.';
            error.hidden = false;
        }
    });
}

async function loadCards() {
    listStatus.textContent = 'Загрузка…';
    try {
        const response = await fetch('/api/cards');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const cards = await response.json();
        list.replaceChildren();
        cards.forEach(renderCard);
        listStatus.textContent = '';
        listStatus.hidden = cards.length === 0;
        listEmpty.hidden = cards.length !== 0;
    } catch (e) {
        listStatus.textContent = 'Не удалось загрузить карточки. Проверьте, что сервер запущен, и обновите страницу.';
    }
}

loadCards();
