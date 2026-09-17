# Implementation Plan — AI Dispensing Defect Detective

> Note on ordering: I moved the tech-stack decisions (LLM, Database) before Folder Structure, since the folder structure is easiest to define once the stack is chosen. Flow of Development, GitHub Branches, and Role Division follow after.

**Context that shapes these decisions (from the rules doc):**
- Team size: up to 3 members ✓ (matches your team)
- No specific AI model, language, or platform is compulsory — free choice, but third-party tools/models must be clearly declared
- A **live, functional prototype** is required for the Final Stage (no mockups/slides accepted)
- Submission deadline: 21 September 2026 — a short runway, so the stack should favor speed of development over infrastructure complexity

---

## 1. LLM Choice

**Recommendation: OpenAI, but assign models per-agent rather than one model for everything** — this now maps directly onto the Subagents architecture from system-architecture.md, where the Main Orchestrator calls smaller, focused subagents as tools.

| Agent | Model | Why |
|---|---|---|
| **Main Orchestrator** (runs the conversation, decides what to call next) | **GPT-4o-mini** | Mostly conversation management and routing — doesn't need the most powerful model, keep it cheap since it's called every turn. |
| **Question Agent** (Step 1) | **GPT-4o-mini** | Simple, structured task (ask adaptive follow-ups) — no need for a bigger model. |
| **Text Defect ID Agent** (Step 2) | **GPT-4o-mini** | Classification-style task against a known list of defect types — light reasoning is enough. |
| **Image Defect ID Agent** (Bonus 1) | **GPT-4o** (multimodal) | Only model in the stack that needs vision — only invoked when a photo is actually uploaded, keeping cost contained. |
| **Cause Ranking Agent** (Step 3–4) | **GPT-4o-mini**, or GPT-4o if reasoning quality on test cases isn't strong enough | This is the most reasoning-heavy subagent (ranked causes + confidence scores + *why*) — start cheap, upgrade only this one agent if outputs are weak. |
| **Report/Action Plan Agent** (Step 5–7) | **GPT-4o-mini** | Mostly formatting a structured output into readable text — doesn't need a stronger model. |

**Why this fits better than one model for everything:**
- Matches the Subagents pattern directly — each subagent is a separate, focused call, so each can use the cheapest model that does the job instead of paying premium-model rates for simple steps.
- Keeps the **multimodal, more expensive GPT-4o call isolated to exactly one subagent** (Image Defect ID) — it only fires when a photo is uploaded, not on every turn.
- Easy to selectively upgrade just the weak link (most likely Cause Ranking, since it needs the most reasoning) without paying more everywhere else.
- Still just one provider (OpenAI) to integrate and declare — no added integration complexity from mixing providers.

**Alternative considered — Qwen (or other open-source model):**
- Pros: free/self-hosted, no per-token cost, good for teams wanting to show "we built the AI layer ourselves."
- Cons: needs GPU hosting or a paid inference endpoint (e.g., via Hugging Face/Together AI) to run at usable speed; multimodal variants (Qwen-VL) require separate setup from the text model; more integration time — a real risk with a tight deadline, and running *multiple* subagents on self-hosted infra adds even more setup than a single model would.
- **Verdict:** Reasonable if your team already has infra/ML experience and wants a stronger "technical depth" story for judging criterion #2 (AI Innovation & Technical Implementation). Otherwise, OpenAI is the safer choice to guarantee a working live demo across 5+ subagents.

Either way, **declare the model(s) explicitly** in your submission (per rule 2.c.2) and be ready to explain *why* different agents use different models in the Q&A — it's a good technical-depth talking point.

---

## 2. How to "Train" the LLM

You don't need to train a model from scratch, and full fine-tuning is not realistic (or necessary) in this timeframe. **Note:** OpenAI began winding down self-serve fine-tuning in May 2026 — new organizations can no longer start fine-tuning jobs on models like GPT-4o mini, which rules it out as an option anyway. Use these approaches instead, roughly in order of effort:

1. **Prompt engineering (primary approach — no training required):**
   - Write a detailed system prompt that encodes the domain knowledge from the challenge brief: common defect types, their symptoms, typical causes (material condition, air bubbles, dispensing parameters, nozzle condition, equipment condition), and the required output format (ranked causes + confidence scores + reasoning).
   - This alone can satisfy the core requirement and is what most hackathon-timeline teams should rely on.

2. **Few-shot examples:** Include 2–3 worked examples in the prompt (problem → questions → identified defect → ranked causes with reasoning → action plan), mirroring the examples in the challenge document. This steers the model's output format and reasoning style without any training step.

3. **Retrieval-Augmented Generation (RAG) — powers the "Learning Database" bonus:**
   - Store past troubleshooting cases in Supabase (problem, causes, solution, outcome).
   - Before generating a response, query Supabase for similar past cases and inject them into the prompt as extra context (e.g., "Similar problems occurred 12 times previously; in 8 cases the cause was air trapped in the syringe").
   - This is what the spec calls the AI "learning" from data — it's retrieval, not retraining, and is realistic to build in the time available.
   - **See Section 2.1 below for how to actually build this, step by step.**

### 2.1 How to Implement RAG, Step by Step

In plain terms: RAG just means "look up similar past cases first, then hand them to the AI as extra context before it answers" — instead of the AI guessing from scratch every time.

**Step 1 — Store cases in a table.**
Create a `case_history` table in Supabase with columns like: `id`, `project_id`, `problem_description`, `defect_type`, `causes` (JSON), `solution`, `outcome`, `created_at`. Every finished session gets saved here — this table is your "memory" that grows over time.

**Team-proposed addition — scope everything to a "Project":** add a `projects` table (`id`, `name`, `machine_or_line`, `created_by`, `created_at`) representing one machine/line/product a user is troubleshooting for — similar in spirit to Claude's Projects. Add a `project_id` column to `case_history` (and to your session-tracking table). This keeps retrieval relevant — e.g., a solder-paste line's history won't get mixed into an adhesive line's cause-ranking lookups.

**Step 2 — Choose how to find "similar" cases.** Two options, pick based on time available. Either way, **always filter by `project_id` first**, then apply whichever matching method below within that Project's cases:

- **Option A — Keyword/tag matching (recommended given the timeline):** tag each case with its `defect_type` and a couple of keywords. To find similar cases, just query `WHERE project_id = 'Y' AND defect_type = 'X' ORDER BY created_at DESC LIMIT 5`. No extra setup — works with plain SQL you already know, and can be built in under an hour.
- **Option B — Semantic/vector search (better quality, more setup):** convert each problem description into an "embedding" — a list of numbers that represents its *meaning*, generated by calling OpenAI's `text-embedding-3-small` model (very cheap — about $0.02 per million tokens, effectively pennies for a hackathon's worth of data). Store these embeddings in Supabase using its `pgvector` extension, then search for the closest matches (again, filtered to the same `project_id`) to a new problem's embedding. This finds similar cases even when the wording is completely different (e.g., "dots too small" vs. "not enough glue coming out" would match, where keyword search might miss it).

**Step 3 — Retrieve at runtime.**
When a new problem comes in and the Cause Ranking Agent is about to run:
1. Look up the top 3–5 similar past cases (using Option A or B above).
2. Format them into a short block of text, e.g.: *"Similar past cases: (1) small dots, cause = air bubble, fixed by re-priming syringe. (2) small dots, cause = clogged nozzle..."*
3. Insert that block into the prompt sent to the Cause Ranking Agent, before asking it to rank causes.
4. The AI's answer should now reference this context directly ("this matches 2 past cases where the cause was...") instead of reasoning from nothing.

**Step 4 — Write back after each session.**
Once a session finishes (defect identified, causes ranked, action plan given), save it as a new row in `case_history` — problem, causes, and the outcome if known. This is what makes the database actually "learn" over time: each session slightly improves future retrieval, even though no model weights are touched.

**Recommendation:** start with Option A (keyword/tag matching) to get something working fast, and only move to Option B (vector search) if there's spare time and the keyword-based matches feel too shallow for the demo.

4. **Fine-tuning (not recommended given the timeline/wind-down):** Only worth mentioning to judges as a *future enhancement* ("with more data and time, the model could be fine-tuned on our accumulated case history") rather than something you attempt to implement now.

**For the image-recognition bonus:** don't train a custom vision model — pass uploaded images directly to a multimodal model (e.g., GPT-4o) with a prompt describing the defect categories to classify against (Missing Dot, Oversized Dot, Undersized Dot, Irregular Shape, Excessive Spreading). This avoids needing a labeled image dataset or a training pipeline entirely.

---

## 3. Database

**Recommendation: Supabase (Postgres + Storage + Auth)**

| Consideration | Why it fits |
|---|---|
| Structured troubleshooting data | The engine flow needs relational data — problems, causes, confidence scores, recommended steps, and (Bonus 3) historical cases linked to outcomes. Postgres's relational model fits this naturally (vs. a pure NoSQL store). |
| Image storage (Bonus 1) | Supabase Storage handles uploaded dispensing-result images directly, alongside the same project as your database — no separate service needed. |
| Learning database (Bonus 3) | Easy to query "similar problems occurred N times, cause X in Y cases" with SQL aggregation once cases are logged. |
| Speed of setup | Free tier, instant hosted Postgres, auto-generated REST/JS client, minimal backend boilerplate — good fit for a short build window. |
| Team collaboration | Web dashboard lets non-backend teammates view/edit data without needing direct DB access. |

**Alternative considered — Firebase (Firestore):**
- Pros: also fast to set up, good realtime sync.
- Cons: NoSQL structure is a worse fit for the relational querying needed for cause-history stats and report generation; SQL is generally easier to justify/explain to judges as "proper" data modeling.

**One design rule worth following:** keep each user's in-progress conversation (questions asked so far, answers given) stored in Supabase too, not just held in the app's memory while it runs. In plain terms — this is what lets multiple people use the tool at the same time without their sessions getting mixed up, since nothing about one person's progress is sitting only inside the server's temporary memory. See system-architecture.md's "Handling Multiple Users at the Same Time" section for the full reasoning.

---

## 4. Cost Estimate

For a hackathon prototype, this stack should cost close to **$0–$20 total**, well within what a student team can cover:

**LLM (OpenAI API)** — current pricing (Sept 2026):
| Model | Input | Output |
|---|---|---|
| GPT-4o-mini | $0.15 / 1M tokens | $0.60 / 1M tokens |
| GPT-4o (multimodal, for image bonus) | $2.50 / 1M tokens | $10.00 / 1M tokens |

- A single troubleshooting session (questions + cause analysis + report) likely uses a few thousand tokens — well under $0.01 per session on GPT-4o-mini.
- Even with heavy testing (hundreds of runs during development) plus image-analysis calls for the bonus feature, total spend for the whole project should realistically land in the **$5–$15** range. New OpenAI accounts also typically receive a small free credit that may cover most or all of this.
- To control cost: default to GPT-4o-mini for the text Q&A/reasoning flow, and only call the pricier multimodal GPT-4o when an image is actually uploaded.
- With the per-agent model split in Section 1, GPT-4o is isolated to just the Image Defect ID subagent — every other subagent (orchestrator, questions, text defect ID, cause ranking, report) runs on GPT-4o-mini, keeping the estimate above realistic even with 5+ subagent calls per session.

**Database (Supabase)** — free tier is sufficient for this project:
- Free tier includes 500 MB database, 1 GB file storage, 5 GB bandwidth/month, and 2 projects — comfortably enough for a hackathon prototype's session data, case history, and uploaded images. (Note: this "2 projects" limit is Supabase's own hosting concept — one Supabase project can still hold many of *our app's* "Projects" feature as rows in the `projects` table; no naming conflict in practice.)
- **Caveat:** free-tier projects auto-pause after 7 days of inactivity — if you go quiet for a stretch, ping the project (or log in) before your demo/video recording to make sure it's not paused.
- No paid tier should be needed for this project's scope.

**Total estimated cost: under $20**, most realistically closer to $5–$10, all from LLM API usage — a cost worth noting in your submission since judges may ask about feasibility/scalability (judging criterion #3).

---

## 5. Folder Structure

Suggested structure assuming a web app (frontend + backend API + AI logic), now aligned to the Subagents architecture in system-architecture.md — one orchestrator plus a `subagents/` folder of focused, single-purpose agents:

```
ai-dispensing-defect-detective/
├── frontend/                   # UI: chat/Q&A flow, image upload, report view
│   ├── src/
│   │   ├── components/
│   │   ├── pages/               # or app/ if using Next.js App Router — incl. project selector/creation screen
│   │   ├── hooks/
│   │   └── lib/                 # Supabase client, API helpers
│   └── public/
├── backend/                    # API layer / AI orchestration
│   ├── api/                    # routes: /projects, /chat, /diagnose, /upload-image, /report
│   ├── ai/
│   │   ├── orchestrator.py      # Main Orchestrator — runs the conversation, calls subagents as tools
│   │   ├── subagents/
│   │   │   ├── question_agent.py       # Step 1: dynamic questioning (skips questions already answered by an uploaded photo)
│   │   │   ├── text_defect_agent.py    # Step 2: text-based defect identification
│   │   │   ├── image_defect_agent.py   # Bonus 1: multimodal image defect identification
│   │   │   ├── cause_ranking_agent.py  # Step 3–4: cause generation + scoring (+ RAG lookup, scoped to project_id)
│   │   │   └── report_agent.py         # Step 5–7: action plan + report formatting
│   │   └── prompts/              # prompt templates, one per agent above
│   ├── db/                     # Supabase queries/schema helpers, incl. case-history retrieval for RAG
│   └── report/                  # Bonus 4: PDF report generation helpers
├── database/
│   └── schema.sql               # Supabase table definitions + seed data (incl. projects + case_history.project_id)
├── docs/
│   ├── requirements.md
│   ├── implementation.md
│   ├── solution.md
│   └── system-architecture.md
├── tests/
└── README.md
```

Each file under `subagents/` should stay a **single focused function/prompt** — this keeps the "isolated context per subagent" property that makes the architecture token-efficient (per system-architecture.md). Adjust folder names to match your actual framework choice (e.g., Next.js API routes vs. a separate FastAPI service) — the structure above is a starting point, not a fixed requirement.

---

## 6. Flow of Development

Given the short runway to 21 September, a suggested build order that always keeps something demoable working:

1. **Setup (Day 1):** Repo, Supabase project + schema, LLM API keys, basic frontend shell.
2. **Core loop first (Day 2–3):** Step 1–2 — user describes problem → AI asks ~5 questions → AI identifies likely defect. Get this *end-to-end and demoable* before adding depth.
3. **Cause analysis + scoring (Day 3–4):** Step 3–4 — generate ranked causes with confidence scores and reasoning.
4. **Action plan + report (Day 4–5):** Step 5 — recommended troubleshooting sequence, plus basic report output.
5. **Bonus features, if time allows (Day 5–6):** image recognition, learning database, PDF report polish — in priority order based on team strengths.
6. **Testing + refinement (Day 6):** run through realistic test cases, check reasoning quality, fix edge cases.
7. **Demo prep (final days):** record the 6–10 min prototype video, rehearse the live-demo flow, prepare for Q&A on technical choices.

Build the *core troubleshooting loop* fully before touching bonus features — a working basic flow beats an unfinished advanced one, since a live functional prototype is mandatory.

---

## 7. GitHub Branches

Suggested lightweight branching model for a 3-person, short-timeline team:

- `main` — always stable/demoable; only merge tested, working code here.
- `dev` — integration branch where features come together before promoting to `main`.
- `feature/<name>` — one branch per feature, e.g.:
  - `feature/question-engine`
  - `feature/cause-ranking`
  - `feature/report-generation`
  - `feature/image-recognition`
  - `feature/frontend-ui`

Workflow: branch off `dev` → open a PR back into `dev` when ready → merge to `main` only at stable checkpoints (e.g., before recording the demo video). Keep PRs small and review each other's code briefly, even informally, to avoid all three of you touching the same files at once.

---

## 8. Role Division (3 members)

Split along the engine's natural layers so each person owns an end-to-end slice rather than overlapping constantly:

| Role | Owns | Maps to | Folders in charge |
|---|---|---|---|
| **AI / Prompt Engineer** | LLM integration, prompt design for questioning, defect ID, cause ranking, and reasoning explanations | Engine Steps 1–4 | `backend/ai/orchestrator.py`, `backend/ai/subagents/`, `backend/ai/prompts/` |
| **Backend / Data Engineer** | Supabase schema, API routes, session/state management, image upload storage, learning database (Bonus 3) | Data layer + Bonus 1 & 3 | `backend/api/`, `backend/db/`, `database/` |
| **Frontend / Product & Reporting** | UI/UX for the chat flow and image upload, report generation/formatting (Bonus 4), demo video production | Engine Step 5–7 + presentation | `frontend/` (all), `backend/report/` |

Shared/no single owner: `docs/`, `tests/`, `README.md` — keep these updated collaboratively as the project evolves.

Since the team is small, expect some overlap — e.g., the AI engineer may need backend help wiring the LLM into API routes, and everyone should be involved in testing and the final demo rehearsal. Rotate who leads the demo video prep so at least two people are comfortable presenting for the Q&A session at the Final Stage.