'use strict';

// Тест: экраны «выбор» → «вопрос» → «итог». Ход теста живёт только в памяти страницы;
// на сервер уходит лишь отметка повторения каждой карточки (PUT /api/cards/{id}/review).

const MIN_COUNT = 1;
const MAX_COUNT = 100;

const setup = document.getElementById('setup');
const setupForm = document.getElementById('setup-form');
const countInput = document.getElementById('count');
const setupError = document.getElementById('setup-error');
const setupEmpty = document.getElementById('setup-empty');
const startButton = setupForm.querySelector('button');

const questionScreen = document.getElementById('question');
const progress = document.getElementById('progress');
const notice = document.getElementById('notice');
const card = document.getElementById('quiz-card');
const reviewBadge = document.getElementById('review-badge');
const questionText = card.querySelector('.quiz-question');
const answerText = card.querySelector('.quiz-answer');
const actions = document.getElementById('answer-actions');
const knownButton = document.getElementById('known');
const unknownButton = document.getElementById('unknown');
const answerError = document.getElementById('answer-error');

const resultScreen = document.getElementById('result');
const score = document.getElementById('score');
const restartButton = document.getElementById('restart');

let cards = [];
let index = 0;
let known = 0;

function show(screen) {
    for (const section of [setup, questionScreen, resultScreen]) {
        section.hidden = section !== screen;
    }
}

function showSetupError(message) {
    setupError.textContent = message;
    setupError.hidden = false;
}

/** «1 вопрос», «2 вопроса», «5 вопросов». */
function questionsWord(n) {
    const mod10 = n % 10;
    const mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) {
        return 'вопрос';
    }
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
        return 'вопроса';
    }
    return 'вопросов';
}

setupForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    setupError.hidden = true;
    setupEmpty.hidden = true;
    const raw = countInput.value.trim();
    const count = Number(raw);
    if (raw === '' || !Number.isInteger(count) || count < MIN_COUNT || count > MAX_COUNT) {
        showSetupError(`Количество должно быть целым числом от ${MIN_COUNT} до ${MAX_COUNT}`);
        return;
    }
    startButton.disabled = true;
    try {
        const response = await fetch(`/api/cards/random?count=${count}`);
        const body = await response.json().catch(() => null);
        if (!response.ok) {
            showSetupError(body?.error ?? `Сервер ответил ошибкой ${response.status}`);
            return;
        }
        if (body.length === 0) {
            setupEmpty.hidden = false;
            return;
        }
        cards = body;
        index = 0;
        known = 0;
        notice.hidden = cards.length >= count;
        notice.textContent = `В тесте ${cards.length} ${questionsWord(cards.length)} — карточек в базе меньше, чем запрошено.`;
        show(questionScreen);
        showCard();
    } catch (e) {
        showSetupError('Сервер недоступен. Проверьте, что приложение запущено, и попробуйте ещё раз.');
    } finally {
        startButton.disabled = false;
    }
});

// Текст карточки выводится только через textContent, чтобы HTML в нём не интерпретировался.
function showCard() {
    const current = cards[index];
    progress.textContent = `Вопрос ${index + 1} из ${cards.length}`;
    questionText.textContent = current.question;
    answerText.textContent = current.answer;
    reviewBadge.hidden = !current.review;
    card.classList.remove('revealed');
    card.setAttribute('aria-expanded', 'false');
    actions.hidden = true;
    answerError.hidden = true;
    card.focus();
}

function reveal() {
    if (card.classList.contains('revealed')) {
        return;
    }
    card.classList.add('revealed');
    card.setAttribute('aria-expanded', 'true');
    actions.hidden = false;
}

card.addEventListener('click', reveal);
card.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        reveal();
    }
});

/** «Знал» снимает карточку с повторения, «Не знал» ставит; переход — только после сохранения отметки. */
async function answer(wasKnown) {
    const current = cards[index];
    answerError.hidden = true;
    knownButton.disabled = true;
    unknownButton.disabled = true;
    try {
        const response = await fetch(`/api/cards/${encodeURIComponent(current.id)}/review`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({review: !wasKnown}),
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (e) {
        answerError.textContent = 'Не удалось сохранить ответ. Проверьте, что сервер запущен, и попробуйте ещё раз.';
        answerError.hidden = false;
        return;
    } finally {
        knownButton.disabled = false;
        unknownButton.disabled = false;
    }
    if (wasKnown) {
        known++;
    }
    index++;
    if (index < cards.length) {
        showCard();
    } else {
        score.textContent = `Знал ${known} из ${cards.length}`;
        show(resultScreen);
        restartButton.focus();
    }
}

knownButton.addEventListener('click', () => answer(true));
unknownButton.addEventListener('click', () => answer(false));

restartButton.addEventListener('click', () => {
    show(setup);
    countInput.focus();
});
