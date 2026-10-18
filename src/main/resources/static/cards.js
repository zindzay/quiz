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
