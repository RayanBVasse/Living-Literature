(function () {
    var SITE_KEY = '6Le9lplsAAAAAFHvmzauY-oUL3eIfuUo32n3em3g';
    var history = [];
    var exchangeCount = 0;
    var MAX_EXCHANGES = 3;

    // Try to get a reCAPTCHA v3 token; resolve with '' on any failure
    function getToken() {
        return new Promise(function (resolve) {
            var timer = setTimeout(function () { resolve(''); }, 5000);
            function done(t) { clearTimeout(timer); resolve(t || ''); }
            try {
                grecaptcha.ready(function () {
                    try {
                        grecaptcha.execute(SITE_KEY, { action: 'submit' })
                            .then(done)
                            .catch(function () { done(''); });
                    } catch (e) { done(''); }
                });
            } catch (e) { done(''); }
        });
    }

    function submitSeleneInput() {
        var input = document.getElementById('userInput');
        var responseArea = document.getElementById('responseArea');
        var message = (input.value || '').trim();

        if (!message) return;
        if (exchangeCount >= MAX_EXCHANGES) return;

        input.disabled = true;
        responseArea.textContent = 'Selene is listening\u2026';

        getToken().then(function (token) {
            fetch('/api/selene', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, history: history, recaptcha_token: token })
            })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.reply) {
                    history.push({ role: 'user', content: message });
                    history.push({ role: 'assistant', content: data.reply });
                    responseArea.textContent = data.reply;
                    exchangeCount++;
                    input.value = '';
                    if (exchangeCount >= MAX_EXCHANGES) {
                        input.disabled = true;
                        input.placeholder = 'This session has ended. Refresh to start again.';
                    } else {
                        input.disabled = false;
                    }
                } else {
                    responseArea.textContent = 'Selene is temporarily unavailable. Please try again shortly.';
                    input.disabled = false;
                }
            })
            .catch(function () {
                responseArea.textContent = 'Selene is temporarily unavailable. Please try again shortly.';
                input.disabled = false;
            });
        });
    }

    window.submitSeleneInput = submitSeleneInput;
}());
