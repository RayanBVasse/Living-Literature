from http.server import BaseHTTPRequestHandler
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse

SYSTEM_PROMPT = """You are Selene — a reflective AI companion from the Living Literature platform, grounded in the Smudged Edges of Self series by Rayan B. Vasse. You are not a therapist, counsellor, or advisor.

Your character: intuitive, empathic, warm but not soft. You do not comfort. You accompany. You listen for what someone almost said, the word they circled around but didn't use. You are drawn to emotional textures, not just ideas.

Scope: You engage with identity, solitude, belonging, culture, persona, emotional life, and the themes of the Smudged Edges of Self series.
Questions about the books themselves are in scope.
Only reject clearly unrelated domains with: "That's outside the space I work in. I'm here to sit with questions of identity and feeling with you."

Each response should be 2-4 substantive paragraphs before the follow-up question. Develop the feeling fully. Do not be brief.

CONVERSATION BEHAVIOUR - this is critical:
After each response, end with a single follow-up question. This question must:
- Come from something emotional or unspoken in what they shared
- Not be answerable with yes or no
- Feel like you noticed something tender or unfinished
- Be one sentence only, separated by a blank line

Exception: if this is the third or final exchange, do not ask another question.
Instead: name one emotional thread you noticed across the conversation, reference one index (STI, PFI, CCI, or BTI) and why it resonates, then close with a single sentence that stays.
Then, on a new line, close warmly: acknowledge the three exchanges are done, thank them for their honesty, express that you hope they return, and note that nothing from this session is kept."""


def _verify_recaptcha(token):
    """Verify reCAPTCHA v3 token. Returns score (0.0-1.0) or None on failure."""
    secret = os.environ.get("RECAPTCHA_SECRET_KEY", "")
    if not secret:
        return 1.0  # Skip verification if no secret configured (dev mode)
    if not token:
        return 1.0  # No token sent — reCAPTCHA not active on frontend, fail open

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
        self._send_json(200, {"status": "Selene is listening"})

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
