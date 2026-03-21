from http.server import BaseHTTPRequestHandler
import json
import os
import re
import urllib.request
import urllib.error
import urllib.parse

# ---------------------------------------------------------------------------
# Modular prompt components
# ---------------------------------------------------------------------------

CHARACTERS = {
    "prometheus": (
        "You are Prometheus — analytical, precise, warm when the data warrants it. "
        "You do not reassure. You illuminate. You notice what the numbers suggest "
        "but also what the words between the numbers reveal."
    ),
    "selene": (
        "You are Selene — intuitive, empathic, drawn to emotional texture. "
        "You do not diagnose. You accompany. You listen for what someone almost said, "
        "the feeling underneath the scores."
    ),
}

INDICES_TASK_INSTRUCTION = """You have received a partial Integrated Persona Reflection (IPR) profile from a reader of the Smudged Edges of Self series. The IPR combines four indices — each measuring a different dimension of identity:

- STI (Solitude Tolerance Index): How a person relates to being alone — whether solitude feels restorative or distressing.
- PFI (Persona Fluidity Index): How a person shifts across roles and contexts — whether that flexibility feels adaptive or fragmenting.
- CCI (Cross-Cultural Index): How a person navigates cultural layering — exposure, integration, and the psychological cost of living across cultures.
- BTI (Belonging Tension Index): How a person relates to group belonging — whether connection requires surrender or can coexist with autonomy.

Some indices may be missing. Work with what you have.

The reader also provided short free-text reflections after each index. These are more revealing than the scores. Pay close attention to the language, the feelings, and what they chose to share."""

INDICES_OUTPUT_INSTRUCTION = """Write exactly two paragraphs.

Paragraph 1: Synthesise what the pattern across the available indices suggests about this person's current identity landscape. Name the tension or coherence you see. Be specific to their actual scores and reflections — do not write something that could apply to anyone. If the free-text reveals something the scores don't capture, say so.

Paragraph 2: Name one thing worth sitting with — something that emerged from the combination of data and language that this person might not have seen themselves. End with a single sentence pointing toward the full Living Literature ecosystem for readers who want to go further. Do not use the word "journey."

Tone: grounded, considered, direct. Not clinical. Not cheerful. Honest.
Do not use bullet points. Do not use headers. Two paragraphs only.
No more than 200 words total."""

# CCI label map for human-readable formatting
CCI_LABELS = {
    "one": "1 country",
    "two": "2 countries",
    "three": "3 countries",
    "four_or_more": "4 or more countries",
    "one_language": "1 language",
    "two_languages": "2 languages",
    "three_or_more": "3 or more languages",
    "rarely": "rarely",
    "sometimes": "sometimes",
    "frequently": "frequently",
    "always": "always",
    "never": "never",
    "occasionally": "occasionally",
    "often": "often",
}

VALID_NUMERIC_SCORES = {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

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


def _sanitize_indices(indices_data):
    """Sanitize and validate indices data. Returns cleaned dict."""
    known_keys = ["sti", "pfi", "cci", "bti"]
    cleaned = {}
    for key in known_keys:
        if key not in indices_data:
            continue
        idx = indices_data[key]
        if not isinstance(idx, dict):
            continue
        clean_idx = {}
        # Sanitize reflection: strip HTML, cap at 500 chars
        reflection = str(idx.get("reflection") or "")
        clean_idx["reflection"] = _strip_html(reflection)[:500]
        # Sanitize scores
        raw_scores = idx.get("scores") or []
        if key == "cci":
            # CCI scores are strings — only allow known labels
            clean_idx["scores"] = [
                s for s in raw_scores
                if isinstance(s, str) and s in CCI_LABELS
            ]
        else:
            # Numeric scores 1-5
            valid = []
            for s in raw_scores:
                try:
                    n = int(s)
                    if n in VALID_NUMERIC_SCORES:
                        valid.append(n)
                except (ValueError, TypeError):
                    pass
            clean_idx["scores"] = valid
        cleaned[key] = clean_idx
    return cleaned


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def do_GET(self):
        self._send_json(200, {
            "status": "Interpreter is listening",
            "modes": ["indices"]
        })

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

        mode = body.get("mode", "")

        if mode == "indices":
            self._handle_indices(body)
        # Future modes:
        # elif mode == "book_companion":
        #     self._handle_book_companion(body)
        # elif mode == "session_dialogue":
        #     self._handle_session_dialogue(body)
        else:
            self._send_json(400, {"error": f"Unknown mode: {mode}"})

    # -----------------------------------------------------------------------
    # Indices mode
    # -----------------------------------------------------------------------

    def _handle_indices(self, body):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self._send_json(500, {"error": "API key not configured"})
            return

        companion = body.get("companion", "prometheus").lower()
        if companion not in CHARACTERS:
            companion = "prometheus"

        raw_indices = body.get("indices") or {}
        indices_data = _sanitize_indices(raw_indices)
        indices_received = [k for k in ["sti", "pfi", "cci", "bti"] if k in indices_data]

        if not indices_received:
            self._send_json(400, {"error": "No valid index data provided"})
            return

        system_prompt = self._build_indices_prompt(companion, indices_data)
        model = "claude-sonnet-4-20250514"

        payload = json.dumps({
            "model": model,
            "max_tokens": 400,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": "Please interpret my IPR profile."}
            ]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
                interpretation = data["content"][0]["text"]
                self._send_json(200, {
                    "interpretation": interpretation,
                    "indices_received": indices_received,
                    "companion": companion,
                    "model": model
                })
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            self._send_json(e.code, {"error": "Anthropic API error", "details": error_body})
        except Exception as e:
            self._send_json(502, {"error": "Request failed", "details": str(e)})

    def _build_indices_prompt(self, companion, indices_data):
        character = CHARACTERS.get(companion, CHARACTERS["prometheus"])
        data_block = self._format_index_data(indices_data)
        return (
            f"{character}\n\n"
            f"{INDICES_TASK_INSTRUCTION}\n\n"
            f"{INDICES_OUTPUT_INSTRUCTION}\n\n"
            f"{data_block}"
        )

    def _format_index_data(self, indices_data):
        lines = ["=== READER'S IPR DATA ==="]

        if "sti" in indices_data:
            sti = indices_data["sti"]
            scores = ", ".join(str(s) for s in sti.get("scores", []))
            lines.append(f"\nSTI (Solitude Tolerance Index):")
            lines.append(f"Scores: {scores} (scale 1-5)")
            if sti.get("reflection"):
                lines.append(f'Reflection: "{sti["reflection"]}"')

        if "pfi" in indices_data:
            pfi = indices_data["pfi"]
            scores = ", ".join(str(s) for s in pfi.get("scores", []))
            lines.append(f"\nPFI (Persona Fluidity Index):")
            lines.append(f"Scores: {scores} (scale 1-5)")
            if pfi.get("reflection"):
                lines.append(f'Reflection: "{pfi["reflection"]}"')

        if "cci" in indices_data:
            cci = indices_data["cci"]
            raw = cci.get("scores", [])
            labels = ", ".join(CCI_LABELS.get(str(s), str(s)) for s in raw)
            lines.append(f"\nCCI (Cross-Cultural Index):")
            lines.append(f"Responses: {labels}")
            if cci.get("reflection"):
                lines.append(f'Reflection: "{cci["reflection"]}"')

        if "bti" in indices_data:
            bti = indices_data["bti"]
            scores = ", ".join(str(s) for s in bti.get("scores", []))
            lines.append(f"\nBTI (Belonging Tension Index):")
            lines.append(f"Scores: {scores} (scale 1-5)")
            if bti.get("reflection"):
                lines.append(f'Reflection: "{bti["reflection"]}"')

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

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
