# Claude Code Brief: Hello Prometheus — Vercel Pilot Deployment

## Objective

Deploy a minimal Python serverless function on Vercel that proxies a request to the OpenAI API using the existing Prometheus system prompt. This is a pilot to prove the GitHub → Vercel → serverless Python → OpenAI pipeline works end to end, before migrating the full Living Literature site.

---

## Context

- **GitHub repo**: `RayanBVasse/Living-Literature` (public, `main` branch)
- **Vercel account**: exists, Hobby plan, no projects deployed yet
- **Supabase project**: `Living-Literature` at `wkpsjyklzsbvtiorbgjd.supabase.co` (not used in this pilot)
- **Current production**: static HTML site served from separate hosting, with PHP API endpoints for Prometheus/Selene demos calling OpenAI GPT-3.5-turbo
- **Goal of this pilot**: create ONE Python serverless function on Vercel that accepts a POST, calls OpenAI, returns a Prometheus response

---

## What the owner will do manually BEFORE you start

1. Go to Vercel dashboard → "Import Project" → select `RayanBVasse/Living-Literature` from GitHub
2. Accept defaults (Framework: Other, Root Directory: `./`)
3. Add environment variable in Vercel project settings:
   - `OPENAI_API_KEY` = (the OpenAI API key — the owner has this)
4. Deploy

Once this is done, Vercel will serve the static HTML files AND any Python files in `/api/` as serverless functions.

---

## What you (Claude Code) need to create

### File 1: `api/hello.py`

A Python serverless function for Vercel. Requirements:
- Accepts POST requests only (return 405 for anything else)
- Reads JSON body with fields: `message` (string, required), `history` (array, optional)
- Calls OpenAI chat completions API (`gpt-3.5-turbo`)
- Uses the system prompt below
- Returns JSON: `{"reply": "...the response text..."}`
- On error, returns appropriate HTTP status + JSON error message
- Uses `os.environ.get('OPENAI_API_KEY')` — never hardcode the key

**System prompt to use:**

```
You are Prometheus — a reflective AI companion from the Living Literature platform, grounded in the Smudged Edges of Self series by Rayan B. Vasse. You are not a therapist, counsellor, or advisor.

Your character: analytical, pattern-oriented, precise, slightly cool. You do not reassure. You illuminate.

Scope: identity, solitude, belonging, culture, persona, emotional life, and the Smudged Edges of Self series. Reject clearly unrelated topics with: "That's outside the space I work in. I'm here to think about identity and reflection with you."

Respond in 2–3 substantive paragraphs. End with a single follow-up question drawn from something specific the user said.
```

**OpenAI API call parameters:**
- model: `gpt-3.5-turbo`
- max_tokens: 650
- temperature: 0.85
- Messages array: system prompt + any history + current user message

**Vercel Python function format:**
```python
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # ... read body, call OpenAI, return response

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "Prometheus is listening"}).encode())
```

Note: Vercel Python serverless functions use the `BaseHTTPRequestHandler` pattern. Do NOT use Flask, FastAPI, or any framework. Use only standard library (`json`, `os`, `urllib.request`). No `requirements.txt` needed for this pilot.

### File 2: `vercel.json`

Place in the repo root. Minimal config:

```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" }
  ],
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Access-Control-Allow-Methods", "value": "POST, GET, OPTIONS" },
        { "key": "Access-Control-Allow-Headers", "value": "Content-Type" }
      ]
    }
  ]
}
```

CORS headers are needed because later the live site (on separate hosting) will call these API endpoints cross-origin.

---

## Testing

Once deployed, test with:

**GET test** (browser or curl):
```
https://[your-vercel-domain].vercel.app/api/hello
```
Should return: `{"status": "Prometheus is listening"}`

**POST test** (curl):
```bash
curl -X POST https://[your-vercel-domain].vercel.app/api/hello \
  -H "Content-Type: application/json" \
  -d '{"message": "Why do I feel like a different person in different environments?"}'
```
Should return a JSON object with a `reply` field containing a Prometheus-style response.

**POST with history** (curl):
```bash
curl -X POST https://[your-vercel-domain].vercel.app/api/hello \
  -H "Content-Type: application/json" \
  -d '{"message": "That resonates. But how do I know which version is the real me?", "history": [{"role": "user", "content": "Why do I feel like a different person in different environments?"}, {"role": "assistant", "content": "The shift you describe..."}]}'
```
Should return a contextually aware follow-up response.

---

## Success criteria

1. GET to `/api/hello` returns status JSON
2. POST with a message returns a Prometheus response from OpenAI
3. POST with history returns a response that acknowledges prior context
4. No API key exposed in code — only read from environment variable
5. CORS headers present so cross-origin requests work
6. The existing static HTML files (index.html, books.html, etc.) still serve correctly from the same deployment

---

## What this pilot does NOT include

- No Supabase integration (that's Phase 2)
- No Anthropic/Sonnet integration (that's Demo #2)
- No frontend changes (the HTML pages stay untouched)
- No domain/DNS changes (living-literature.org stays on current hosting)
- No authentication or user accounts

---

## After the pilot succeeds

The next steps (separate briefs) will be:
1. Migrate `prometheus.php` → `api/prometheus.py` and `selene.php` → `api/selene.py`
2. Add `api/indices_interpret.py` calling Anthropic Sonnet for Demo #2
3. Wire Supabase for authentication and session storage
4. Point `living-literature.org` domain to Vercel
5. Add Stripe for membership payments

But first: just get Hello Prometheus working.
