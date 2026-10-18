'use strict';

const list = document.getElementById('cards');
const listStatus = document.getElementById('list-status');
const template = document.getElementById('card-template');
const form = document.getElementById('card-form');
const formError = document.getElementById('form-error');
const submitButton = form.querySelector('button');

// Текст карточек выводится только через textContent, чтобы HTML в нём не интерпретировался.
function renderCard(card) {
    const item = template.content.firstElementChild.cloneNode(true);
    item.querySelector('.quiz-question').textContent = card.question;
    item.querySelector('.quiz-answer').textContent = card.answer;
    item.addEventListener('click', () => toggle(item));
    item.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggle(item);
        }
    });
    list.append(item);
}

function toggle(item) {
    const revealed = item.classList.toggle('revealed');
    item.setAttribute('aria-expanded', String(revealed));
}

function updateEmptyState() {
    listStatus.textContent = list.children.length === 0 ? 'Карточек пока нет. Добавьте первую.' : '';
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
        updateEmptyState();
    } catch (e) {
        listStatus.textContent = 'Не удалось загрузить карточки. Проверьте, что сервер запущен, и обновите страницу.';
    }
}

function showFormError(message) {
    formError.textContent = message;
    formError.hidden = false;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    formError.hidden = true;
    submitButton.disabled = true;
    try {
        const response = await fetch('/api/cards', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                question: form.elements.question.value,
                answer: form.elements.answer.value,
            }),
        });
        const body = await response.json().catch(() => null);
        if (!response.ok) {
            showFormError(body?.error ?? `Сервер ответил ошибкой ${response.status}`);
            return;
        }
        renderCard(body);
        updateEmptyState();
        form.reset();
        form.elements.question.focus();
    } catch (e) {
        showFormError('Сервер недоступен. Проверьте, что приложение запущено, и попробуйте ещё раз.');
    } finally {
        submitButton.disabled = false;
    }
});

loadCards();
