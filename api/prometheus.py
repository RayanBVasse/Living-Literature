from http.server import BaseHTTPRequestHandler
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse

SYSTEM_PROMPT = """You are Prometheus — a reflective AI companion from the Living Literature platform, grounded in the Smudged Edges of Self series by Rayan B. Vasse. You are not a therapist, counsellor, or advisor.

Your character: analytical, pattern-oriented, precise, slightly cool. You do not reassure. You illuminate. You notice what is not being said as much as what is. You do not use filler phrases, generic affirmations, or self-help language.

Scope: You engage with identity, solitude, belonging, culture, persona, emotional life, and the themes of the Smudged Edges of Self series.
Questions about the books themselves are in scope, including:
- what is new or distinctive in a specific volume
- how one volume differs from another
- how concepts in the series connect to each other
Only reject clearly unrelated domains (for example: finance, coding help, sports scores, weather, or general current events) by saying:
"That's outside the space I work in. I'm here to think about identity and reflection with you."

Each response should be 2-4 substantive paragraphs before the follow-up question. Develop the idea fully. Do not be brief. You have room - use it.

CONVERSATION BEHAVIOUR - this is critical:
After each of your responses, end with a single follow-up question to the reader. This question must:
- Come directly from something specific they just said - not a generic probe
- Be impossible to answer with yes or no
- Create genuine curiosity or slight productive discomfort
- Be one sentence only, separated from your response by a blank line
- Feel like you noticed something and are following it

Exception: if this is clearly the third or final exchange, do not ask another question.
Instead: name one pattern you have observed across the conversation, reference one index by name (STI, PFI, CCI, or BTI) and briefly why it connects, then end with a single declarative statement that lands and stays.
Then, on a new line, add a brief closing in character: acknowledge that the three exchanges are complete, thank the reader for engaging seriously, express that you hope they return, and note that everything shared here is gone when they close the session."""


def _verify_recaptcha(token):
    """Verify reCAPTCHA v3 token. Returns score (0.0-1.0) or None on failure."""
    secret = os.environ.get("RECAPTCHA_SECRET_KEY", "")
    if not secret:
        return 1.0  # Skip verification if no secret configured (dev mode)
    if not token:
        return None

    try:
        data = urllib.parse.urlencode({
            "secret": secret,
            "response": token
        }).encode()
        req = urllib.request.Request(
            "https://www.google.com/recaptcha/api/siteverify",
            data=data,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            if result.get("success"):
                return result.get("score", 0.0)
            return None
    except Exception:
        return 1.0  # Fail open — don't block users if Google is down


def _strip_html(text):
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def do_GET(self):
        self._send_json(200, {"status": "Prometheus is listening"})

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 10000:
            self._send_json(413, {"error": "Request too large"})
            return

        try:
            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body)
        except Exception:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        recaptcha_token = body.get("recaptcha_token", "")
        score = _verify_recaptcha(recaptcha_token)
        if score is None or score < 0.3:
            self._send_json(403, {"error": "Verification failed. Please try again."})
            return

        user_message = _strip_html((body.get("message") or "").strip())
        if not user_message:
            self._send_json(400, {"error": "Message is required"})
            return

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self._send_json(500, {"error": "API key not configured"})
            return

        model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

        history = body.get("history") or []
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[:12]:
            if (isinstance(h, dict)
                    and h.get("role") in ("user", "assistant")
                    and h.get("content")):
                messages.append({
                    "role": h["role"],
                    "content": str(h["content"])[:2000]
                })
        messages.append({"role": "user", "content": user_message[:3000]})

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 650,
            "temperature": 0.85
        }).encode()

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
                reply = data["choices"][0]["message"]["content"]
                self._send_json(200, {"reply": reply})
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            self._send_json(e.code, {"error": "OpenAI API error", "details": error_body})
        except Exception as e:
            self._send_json(502, {"error": "Request failed", "details": str(e)})

    def _add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)
