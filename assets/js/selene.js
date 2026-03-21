(function () {
    var SITE_KEY = '6Le9lplsAAAAAFHvmzauY-oUL3eIfuUo32n3em3g';
    var history = [];
    var exchangeCount = 0;
    var MAX_EXCHANGES = 3;

    function submitSeleneInput() {
        var input = document.getElementById('userInput');
        var responseArea = document.getElementById('responseArea');
        var message = (input.value || '').trim();

        if (!message) return;
        if (exchangeCount >= MAX_EXCHANGES) return;

        input.disabled = true;
        responseArea.textContent = 'Selene is listening\u2026';

        var captchaTimer;
        var settled = false;

        function onError() {
            if (settled) return;
            settled = true;
            clearTimeout(captchaTimer);
            responseArea.textContent = 'Selene is temporarily unavailable. Please try again shortly.';
            input.disabled = false;
        }

        function doFetch(token) {
            if (settled) return;
            settled = true;
            clearTimeout(captchaTimer);

            fetch('/api/selene', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, history: history, recaptcha_token: token || '' })
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
        }

        // Safety net: if reCAPTCHA doesn't settle in 10s, recover
        captchaTimer = setTimeout(function () {
            if (!settled) onError();
        }, 10000);

        try {
            grecaptcha.ready(function () {
                grecaptcha.execute(SITE_KEY, { action: 'submit' })
                    .then(doFetch)
                    .catch(onError);
            });
        } catch (e) {
            onError();
        }
    }

    window.submitSeleneInput = submitSeleneInput;
}());
