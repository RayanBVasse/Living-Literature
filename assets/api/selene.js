const SELENE_INTRO = "I'm Selene - a reflective companion grounded in the themes of Urban Monasticism. I'm an AI, not a therapist or counsellor. I don't store what you share with me, and I won't remember this conversation next time. I'm here to extend the reflective life of the book - nothing more, nothing less. If you're going through something hard, please reach out to someone who can genuinely help. What's on your mind?";
const SELENE_MAX_QUESTIONS = 3;

let seleneInteractionCount = 0;
let conversationHistory = [];
let seleneIsSubmitting = false;

function getSeleneElements() {
    return {
        inputEl: document.getElementById("userInput"),
        responseArea: document.getElementById("responseArea"),
        submitBtn: document.querySelector(".demo-form button"),
        formEl: document.querySelector(".demo-form")
    };
}

function ensureSeleneMetaUi() {
    const { formEl, responseArea } = getSeleneElements();
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

function createSeleneTurn(role, text) {
    const turnEl = document.createElement("div");
    turnEl.style.borderTop = "1px solid rgba(0,0,0,0.08)";
    turnEl.style.paddingTop = "0.75rem";
    turnEl.style.marginTop = "0.75rem";

    const whoEl = document.createElement("div");
    whoEl.style.fontWeight = "700";
    whoEl.style.letterSpacing = "0.06em";
    whoEl.style.fontSize = "0.8rem";
    whoEl.style.textTransform = "uppercase";
    whoEl.textContent = role === "user" ? "You" : "Selene";

    const bodyEl = document.createElement("div");
    bodyEl.style.whiteSpace = "pre-wrap";
    bodyEl.style.marginTop = "0.35rem";
    bodyEl.textContent = text;

    turnEl.appendChild(whoEl);
    turnEl.appendChild(bodyEl);
    return turnEl;
}

function renderSeleneConversation() {
    const { responseArea } = getSeleneElements();
    if (!responseArea) return;

    responseArea.innerHTML = "";
    responseArea.appendChild(createSeleneTurn("assistant", SELENE_INTRO));
    conversationHistory.forEach((turn) => {
        responseArea.appendChild(createSeleneTurn(turn.role, turn.content));
    });
    responseArea.scrollTop = responseArea.scrollHeight;
}

function updateSeleneUiState() {
    const { inputEl, submitBtn } = getSeleneElements();
    const counterEl = document.getElementById("llTurnCounter");
    const cueEl = document.getElementById("llContinueCue");
    const remaining = Math.max(SELENE_MAX_QUESTIONS - seleneInteractionCount, 0);

    if (counterEl) {
        if (seleneInteractionCount < SELENE_MAX_QUESTIONS) {
            counterEl.textContent = `Question ${seleneInteractionCount + 1} of ${SELENE_MAX_QUESTIONS}.`;
        } else {
            counterEl.textContent = `Session complete (${SELENE_MAX_QUESTIONS} of ${SELENE_MAX_QUESTIONS}).`;
        }
    }

    if (cueEl) {
        if (seleneIsSubmitting) {
            cueEl.textContent = "Selene is responding...";
        } else if (remaining > 0) {
            cueEl.textContent = `Ask a follow-up question (${remaining} remaining). Press Enter to send.`;
        } else {
            cueEl.textContent = "You are limited to only three questions.";
        }
    }

    if (submitBtn) {
        if (seleneIsSubmitting) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Listening...";
            submitBtn.style.opacity = "0.75";
            submitBtn.style.cursor = "not-allowed";
        } else if (seleneInteractionCount >= SELENE_MAX_QUESTIONS) {
            submitBtn.disabled = true;
            submitBtn.textContent = "Talk to Selene";
            submitBtn.style.opacity = "0.6";
            submitBtn.style.cursor = "not-allowed";
        } else {
            submitBtn.disabled = false;
            submitBtn.textContent = "Talk to Selene";
            submitBtn.style.opacity = "1";
            submitBtn.style.cursor = "pointer";
        }
    }

    if (inputEl) {
        if (seleneInteractionCount >= SELENE_MAX_QUESTIONS) {
            inputEl.value = "you are limited to only three questions";
            inputEl.disabled = true;
        } else if (!seleneIsSubmitting) {
            inputEl.disabled = false;
        }
    }
}

function lockSeleneDemoInput() {
    seleneIsSubmitting = false;
    updateSeleneUiState();
}

function initSeleneDemoUi() {
    const { inputEl } = getSeleneElements();
    ensureSeleneMetaUi();
    renderSeleneConversation();
    updateSeleneUiState();

    if (inputEl && !inputEl.dataset.enterSubmitBound) {
        inputEl.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                submitSeleneInput();
            }
        });
        inputEl.dataset.enterSubmitBound = "1";
    }
}

document.addEventListener("DOMContentLoaded", initSeleneDemoUi);

async function submitSeleneInput() {
    const { responseArea, inputEl } = getSeleneElements();
    if (!responseArea || !inputEl) return;

    if (seleneIsSubmitting) return;
    if (seleneInteractionCount >= SELENE_MAX_QUESTIONS) {
        lockSeleneDemoInput();
        return;
    }

    const userInput = inputEl.value.trim();
    if (!userInput) {
        const cueEl = document.getElementById("llContinueCue");
        if (cueEl) cueEl.textContent = "Share a short reflection to begin.";
        return;
    }

    seleneIsSubmitting = true;
    updateSeleneUiState();

    try {
        const response = await fetch("/api/selene.php", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userInput,
                history: conversationHistory
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);

        const message = data.reply || data.choices?.[0]?.message?.content || "No response from Selene.";
        conversationHistory.push({ role: "user", content: userInput });
        conversationHistory.push({ role: "assistant", content: message });
        seleneInteractionCount++;
        inputEl.value = "";
        renderSeleneConversation();
    } catch (error) {
        conversationHistory.push({ role: "assistant", content: "The demo is temporarily unavailable. Please try again shortly." });
        renderSeleneConversation();
    } finally {
        seleneIsSubmitting = false;
        if (seleneInteractionCount >= SELENE_MAX_QUESTIONS) {
            lockSeleneDemoInput();
        } else {
            updateSeleneUiState();
            inputEl.focus();
        }
    }
}
