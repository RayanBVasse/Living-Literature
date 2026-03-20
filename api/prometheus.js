const PROMETHEUS_INTRO = "I'm Prometheus - a reflective companion grounded in the themes of The Persona Continuum. I'm an AI, not a therapist or counsellor. I don't retain memory between our conversations, and I don't know you as an individual. What I can do is think with you about the ideas in this book. If anything we discuss brings up something difficult, please consider speaking with someone who can actually support you. Ready when you are.";
const PROMETHEUS_MAX_QUESTIONS = 3;

let prometheusInteractionCount = 0;
let conversationHistory = [];
let prometheusIsSubmitting = false;

function getPrometheusElements() {
    return {
        inputEl: document.getElementById("userInput"),
        responseArea: document.getElementById("responseArea"),
        submitBtn: document.querySelector(".demo-form button"),
        formEl: document.querySelector(".demo-form")
    };
}

function ensurePrometheusMetaUi() {
    const { formEl, responseArea } = getPrometheusElements();
    if (!formEl || !responseArea) return;

    let counterEl = document.getElementById("llTurnCounter");
    if (!counterEl) {
        counterEl = document.createElement("p");
        counterEl.id = "llTurnCounter";
        counterEl.className = "disclaimer";
        counterEl.style.marginTop = "0.6rem";
        formEl.insertAdjacentElement("afterend", counterEl);
    }

    let cueEl = document.getElementById("llContinueCue");
    if (!cueEl) {
        cueEl = document.createElement("p");
        cueEl.id = "llContinueCue";
        cueEl.className = "disclaimer";
        cueEl.style.marginTop = "0.6rem";
        responseArea.insertAdjacentElement("afterend", cueEl);
    }
}

function createPrometheusTurn(role, text) {
    const turnEl = document.createElement("div");
    turnEl.style.borderTop = "1px solid rgba(0,0,0,0.08)";
    turnEl.style.paddingTop = "0.75rem";
    turnEl.style.marginTop = "0.75rem";

    const whoEl = document.createElement("div");
    whoEl.style.fontWeight = "700";
    whoEl.style.letterSpacing = "0.06em";
    whoEl.style.fontSize = "0.8rem";
    whoEl.style.textTransform = "uppercase";
    whoEl.textContent = role === "user" ? "You" : "Prometheus";

    const bodyEl = document.createElement("div");
    bodyEl.style.whiteSpace = "pre-wrap";
    bodyEl.style.marginTop = "0.35rem";
    bodyEl.textContent = text;

    turnEl.appendChild(whoEl);
    turnEl.appendChild(bodyEl);
    return turnEl;
}

function renderPrometheusConversation() {
    const { responseArea } = getPrometheusElements();
    if (!responseArea) return;

    responseArea.innerHTML = "";
    responseArea.appendChild(createPrometheusTurn("assistant", PROMETHEUS_INTRO));
    conversationHistory.forEach((turn) => {
        responseArea.appendChild(createPrometheusTurn(turn.role, turn.content));
    });
    responseArea.scrollTop = responseArea.scrollHeight;
}

function updatePrometheusUiState() {
    const { inputEl, submitBtn } = getPrometheusElements();
    const counterEl = document.getElementById("llTurnCounter");
    const cueEl = document.getElementById("llContinueCue");
    const remaining = Math.max(PROMETHEUS_MAX_QUESTIONS - prometheusInteractionCount, 0);

    if (counterEl) {
        if (prometheusInteractionCount < PROMETHEUS_MAX_QUESTIONS) {
            counterEl.textContent = `Question ${prometheusInteractionCount + 1} of ${PROMETHEUS_MAX_QUESTIONS}.`;
        } else {
            counterEl.textContent = `Session complete (${PROMETHEUS_MAX_QUESTIONS} of ${PROMETHEUS_MAX_QUESTIONS}).`;
        }
    }

    if (cueEl) {
        if (prometheusIsSubmitting) {
            cueEl.textContent = "Prometheus is responding...";
        } else if (remaining > 0) {
            cueEl.textContent = `Ask a follow-up question (${remaining} remaining). Press Enter to send.`;
        } else {
            cueEl.textContent = "You are limited to only three questions.";
        }
    }

    if (submitBtn) {
        if (prometheusIsSubmitting) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Thinking...";
            submitBtn.style.opacity = "0.75";
            submitBtn.style.cursor = "not-allowed";
        } else if (prometheusInteractionCount >= PROMETHEUS_MAX_QUESTIONS) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Talk to Prometheus";
            submitBtn.style.opacity = "0.6";
            submitBtn.style.cursor = "not-allowed";
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = "Talk to Prometheus";
            submitBtn.style.opacity = "1";
            submitBtn.style.cursor = "pointer";
        }
    }

    if (inputEl) {
        if (prometheusInteractionCount >= PROMETHEUS_MAX_QUESTIONS) {
            inputEl.value = "you are limited to only three questions";
            inputEl.disabled = true;
        } else if (!prometheusIsSubmitting) {
            inputEl.disabled = false;
        }
    }
}

function lockPrometheusDemoInput() {
    prometheusIsSubmitting = false;
    updatePrometheusUiState();
}

function initPrometheusDemoUi() {
    const { inputEl } = getPrometheusElements();
    ensurePrometheusMetaUi();
    renderPrometheusConversation();
    updatePrometheusUiState();

    if (inputEl && !inputEl.dataset.enterSubmitBound) {
        inputEl.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                submitPrometheusInput();
            }
        });
        inputEl.dataset.enterSubmitBound = "1";
    }
}

document.addEventListener("DOMContentLoaded", initPrometheusDemoUi);

async function submitPrometheusInput() {
    const { responseArea, inputEl } = getPrometheusElements();
    if (!responseArea || !inputEl) return;

    if (prometheusIsSubmitting) return;
    if (prometheusInteractionCount >= PROMETHEUS_MAX_QUESTIONS) {
        lockPrometheusDemoInput();
        return;
    }

    const userInput = inputEl.value.trim();
    if (!userInput) {
        const cueEl = document.getElementById("llContinueCue");
        if (cueEl) cueEl.textContent = "Share a short reflection to begin.";
        return;
    }

    prometheusIsSubmitting = true;
    updatePrometheusUiState();

    try {
        const response = await fetch("/api/prometheus.php", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userInput,
                history: conversationHistory
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);

        const message = data.reply || data.choices?.[0]?.message?.content || "No response from Prometheus.";
        conversationHistory.push({ role: "user", content: userInput });
        conversationHistory.push({ role: "assistant", content: message });
        prometheusInteractionCount++;
        inputEl.value = "";
        renderPrometheusConversation();
    } catch (error) {
        conversationHistory.push({ role: "assistant", content: "The demo is temporarily unavailable. Please try again shortly." });
        renderPrometheusConversation();
    } finally {
        prometheusIsSubmitting = false;
        if (prometheusInteractionCount >= PROMETHEUS_MAX_QUESTIONS) {
            lockPrometheusDemoInput();
        } else {
            updatePrometheusUiState();
            inputEl.focus();
        }
    }
}
