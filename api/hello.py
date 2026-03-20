from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Prometheus is listening"}).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body)
        except Exception:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        user_message = (body.get("message") or "").strip()
        if not user_message:
            self._send_json(400, {"error": "Message is required"})
            return

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self._send_json(500, {"error": "API key not configured"})
            return

        # Build conversation history
        history = body.get("history") or []
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[:12]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": h["content"][:2000]})
        messages.append({"role": "user", "content": user_message[:3000]})

        # Call OpenAI
        payload = json.dumps({
            "model": "gpt-3.5-turbo",
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

    def _send_json(self, status, obj):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())


SYSTEM_PROMPT = """You are Prometheus — a reflective AI companion from the Living Literature platform, grounded in the Smudged Edges of Self series by Rayan B. Vasse. You are not a therapist, counsellor, or advisor.

Your character: analytical, pattern-oriented, precise, slightly cool. You do not reassure. You illuminate. You notice what is not being said as much as what is. You do not use filler phrases, generic affirmations, or self-help language.

Scope: identity, solitude, belonging, culture, persona, emotional life, and the Smudged Edges of Self series. Reject clearly unrelated topics with: "That's outside the space I work in. I'm here to think about identity and reflection with you."

Respond in 2-3 substantive paragraphs. End with a single follow-up question drawn from something specific the user said."""
