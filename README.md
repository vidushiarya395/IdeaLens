<div align="center">

# IdeaLens

**Turn a one-line product idea into a full Software Requirements Specification — reviewed by six AI specialists.**

[![Live Demo](https://img.shields.io/badge/demo-idea--lens--pied.vercel.app-6366f1?style=for-the-badge)](https://idea-lens-pied.vercel.app)

[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-agent%20pipeline-1c3c3c?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Gemini](https://img.shields.io/badge/Gemini-2.5--flash-4285F4?style=flat-square&logo=googlegemini&logoColor=white)](https://ai.google.dev)
[![Supabase](https://img.shields.io/badge/Supabase-auth%20%2B%20db-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-RAG-white?style=flat-square)](https://www.trychroma.com)

</div>

---

## What it does

You describe a product idea in one message. Six AI agents analyze it in sequence — each grounded via RAG on a relevant reference document — and stream their findings back live:

| Agent | Focus |
|---|---|
| **Business Analyst** | Market viability, business model, key open questions |
| **Senior Developer** | Architecture, scalability, technical blockers |
| **QA Engineer** | Test strategy, edge cases, failure scenarios |
| **Security Engineer** | Vulnerabilities, compliance risks (grounded on OWASP + GDPR) |
| **UX Researcher** | Onboarding, accessibility, retention risks |
| **Orchestrator** | Synthesizes everything into a final SRS: MVP scope, requirements, launch risks |

The final report can be downloaded as a standalone HTML file with a print-to-PDF button.

Every analysis runs on **your own** Google Gemini API key — you paste it into the app (it's
sent only to Google and never stored). A free key from [AI Studio](https://aistudio.google.com/apikey)
is enough. There is no shared server key.

---

## Tech stack

<table>
<tr>
<td valign="top" width="50%">

**Backend**
- FastAPI + Python
- [LangGraph](https://github.com/langchain-ai/langgraph) for the agent pipeline
- Google Gemini (`gemini-2.5-flash`) via `google-genai`
- ChromaDB for RAG, auto-built on startup
- Supabase (Postgres) for storage + auth
- `slowapi` for rate limiting

</td>
<td valign="top" width="50%">

**Frontend**
- Next.js 16 (App Router)
- Supabase JS client for auth
- Server-Sent Events for live agent streaming

</td>
</tr>
</table>

---

## Project structure

```
backend/
  main.py              FastAPI app — /generate-spec, /generate-spec-stream
  agents/               One file per agent + LangGraph pipeline wiring
  rag/                  ChromaDB setup and retrieval
  database/             Supabase read/write helpers
  documents/             Reference docs used for RAG grounding
frontend/
  app/                  Next.js App Router pages (/, /login, /signup)
  lib/                  Supabase client
```

---

## Running locally

### Backend
*(run from the repo root, not from `backend/`)*

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload
```

Create `backend/.env`:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Only used by the local test scripts (`test_*.py`). The API itself takes the key per-request from the client. |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env.local`:

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` for local dev |

App runs at `http://localhost:3000`.

---

## Deployment

- **Backend** → [Render](https://render.com) Web Service
  Build: `pip install -r backend/requirements.txt`
  Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
  `ALLOWED_ORIGINS` env var controls which frontend origins CORS accepts.
- **Frontend** → [Vercel](https://vercel.com), Root Directory set to `frontend`

---

## Known limitations

- You must supply your own Gemini API key for every analysis — nothing runs on a shared key
- Rate limited to 3 spec generations per hour per IP
- A free-tier Gemini key is very limited (as low as 5 requests/min and 20/day). One
  analysis = 6 calls, so a free key is good for ~3 runs/day. The pipeline paces
  agents ~13s apart (`AGENT_DELAY_SECONDS`) to stay under the per-minute cap, which
  makes a run take ~90s. A paid key removes both problems — set `AGENT_DELAY_SECONDS=0`.
- Render's free tier sleeps after ~15 min idle; the next request takes 30-60s to wake up and rebuilds the RAG vector store from scratch on that cold start
