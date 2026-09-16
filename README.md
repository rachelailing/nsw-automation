# AI Dispensing Defect Detective

An AI-powered troubleshooting engine for semiconductor dispensing defects. Uses a multi-agent architecture (Subagents pattern) to diagnose defects, rank probable causes, and generate actionable reports.

## Tech Stack

- **Frontend:** Next.js (App Router) + React
- **Backend:** Python + FastAPI
- **AI:** OpenAI GPT-4o-mini (text agents) + GPT-4o (image agent)
- **Database:** Supabase (PostgreSQL + Storage)

## Project Structure

```
├── frontend/          # Next.js UI: chat flow, image upload, report view
├── backend/           # FastAPI: API routes + AI orchestration
│   ├── api/           # HTTP endpoints
│   ├── ai/            # Orchestrator + subagents + prompts
│   ├── db/            # Supabase client + queries
│   └── report/        # PDF generation (Bonus 4)
├── database/          # SQL schema + seed data
├── docs/              # Project documentation
└── tests/             # Test files
```

## Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- A Supabase project ([supabase.com](https://supabase.com))
- An OpenAI API key ([platform.openai.com](https://platform.openai.com))

### 1. Clone and configure environment
```bash
cp .env.example .env
# Fill in your OPENAI_API_KEY, SUPABASE_URL, and SUPABASE_ANON_KEY
```

### 2. Set up the database
- Go to your Supabase project → SQL Editor
- Run the contents of `database/schema.sql`

### 3. Start the backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and the backend on `http://localhost:8000`.

## Architecture

See [docs/system-architecture.md](docs/system-architecture.md) for the full Subagents architecture diagram and rationale.

## Team

| Role | Scope |
|---|---|
| AI / Prompt Engineer | Orchestrator, subagents, prompts |
| Backend / Data Engineer | API routes, Supabase, sessions, RAG |
| Frontend / Product | UI, reports, demo video |

## License

This project was created for the NSW Hackathon 2026.
