'use strict';

const form = document.getElementById('card-form');
const formError = document.getElementById('form-error');
const formSuccess = document.getElementById('form-success');
const submitButton = form.querySelector('button');

function showFormError(message) {
    formError.textContent = message;
    formError.hidden = false;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;
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
        form.reset();
        formSuccess.hidden = false;
        form.elements.question.focus();
    } catch (e) {
        showFormError('Сервер недоступен. Проверьте, что приложение запущено, и попробуйте ещё раз.');
    } finally {
        submitButton.disabled = false;
    }
});
