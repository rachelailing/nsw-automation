# System Architecture — AI Dispensing Defect Detective

## Correcting the Architecture Choice

A couple of things in the original reasoning need adjusting — the description and the scenario cited don't actually point to the same pattern:

1. **"1 main agent orchestrates subagents, each subagent focuses on its own task"** — this description is actually the **Subagents (Centralized Orchestration)** pattern, not Handoffs. In the Handoffs pattern, there's no main agent sitting above the others — control fully *transfers* from one agent to the next (like a relay baton), and whichever agent is currently active talks to the user directly. There's no central orchestrator collecting results back.

2. **Scenario 3 (Multi-domain query) does NOT favor Handoffs.** The blog's own numbers for that scenario:

   | Pattern | Model calls | Total tokens | Notes |
   |---|---|---|---|
   | Subagents | 5 | ~9K | Parallel, context-isolated |
   | Router | 5 | ~9K | Parallel execution |
   | Skills | 3 | ~15K | Context accumulates |
   | **Handoffs** | **7+** | **~14K+** | **Sequential only — can't parallelize** |

   Handoffs actually performs *worst* on tokens in that scenario, because it must run sequentially and can't fan out work in parallel. The pattern that gives "1 main agent, isolated subagents, optimal token use" is **Subagents** — that's the one worth using, not Handoffs.

**Bottom line:** the reasoning was on the right track (centralized orchestrator + parallel, isolated subtasks = efficient), just pointing at the wrong pattern name. What you described *is* the **Subagents** pattern.

---

## Does This Project Actually Need Multi-Agent at All?

Worth a gut-check before committing to a heavier architecture: the source article's own advice is *"start with a single agent and good prompt engineering... graduate to multi-agent only when you hit clear limits."* Given the 1-week build window, it's fair to ask whether our Engine Flow (Q&A → identify defect → rank causes → action plan → report) needs multiple agents at all, since it's mostly one continuous conversation with one user.

Where multi-agent genuinely earns its place here: **when the text-based diagnosis and the image-based diagnosis (Bonus 1) need to run independently and get combined.** That's a real "multi-domain, parallelizable" situation — which is exactly what the Subagents (or Router) pattern is built for.

**Recommendation: a lightweight Subagents architecture**, kept as simple as possible — one main orchestrator + a small number of focused subagents, not a large sprawling agent farm.

---

## Recommended Architecture: Subagents (Centralized Orchestration)

```
                        ┌──────────────────────────┐
                        │      Main Orchestrator     │
                        │   ("Detective" Agent)       │
                        │  - Runs the conversation     │
                        │  - Decides which subagents   │
                        │    to call, in what order     │
                        │  - Combines their outputs     │
                        │    into one coherent reply     │
                        └────────────┬─────────────┘
                                     │  calls as tools
          ┌───────────────┬─────────┼─────────┬───────────────┐
          ▼               ▼         ▼         ▼               ▼
  ┌───────────────┐ ┌───────────┐ ┌────────────┐ ┌──────────────┐ ┌───────────────┐
  │ Question Agent │ │ Text      │ │ Image      │ │ Cause Ranking │ │ Report/Action │
  │ (Step 1)       │ │ Defect ID │ │ Defect ID  │ │ Agent         │ │ Plan Agent    │
  │                │ │ (Step 2)  │ │ (Bonus 1)  │ │ (Step 3–4)    │ │ (Step 5–7)    │
  └───────────────┘ └───────────┘ └────────────┘ └──────────────┘ └───────────────┘
                                     ▲
                                     │ retrieves similar past cases
                                     ▼
                           ┌───────────────────┐
                           │  Supabase Database  │
                           │  (case history/RAG)  │
                           └───────────────────┘
```

**How it works:**
- The **Main Orchestrator** is the only agent the user ever "talks to." It holds the conversation, decides what's needed next, and calls subagents as tools.
- Subagents are **stateless** — they don't remember past turns, they just do one focused job with the input they're given and return a result. This matches the Subagents pattern's core trade: strong context isolation (each subagent's prompt only contains what it needs — e.g., the Image Defect Agent doesn't need the full conversation history) at the cost of one extra call to route results back through the orchestrator.
- When both a text description **and** an uploaded image are available, the **Text Defect ID Agent** and **Image Defect ID Agent** can run **in parallel**, then the orchestrator merges their findings before passing to Cause Ranking — this is where the token/latency savings from the article's Scenario 3 actually apply.
- The **Cause Ranking Agent** is where the RAG lookup happens (querying Supabase for similar historical cases, per implementation.md's "How to Train the LLM" section) to ground its confidence scores in real precedent instead of guessing.

---

## Simplified Build Path (Recommended for the 1-Week Timeline)

Given the timeline, don't build 5 separate literal "agents" (5 separate prompts/API wrappers) — treat most of these as **tool functions called by one orchestrator prompt**, which gets you the same architecture on paper (and the same story for judges) with far less integration overhead:

| "Agent" | Realistic implementation |
|---|---|
| Main Orchestrator | The core chat loop — one LLM call per turn, with function-calling enabled |
| Question Agent | Just part of the orchestrator's system prompt (Step 1 logic) |
| Text Defect ID Agent | A tool function with its own focused prompt, called when enough info is gathered |
| Image Defect ID Agent | A tool function that sends the image to a multimodal call (only invoked if an image was uploaded) |
| Cause Ranking Agent | A tool function that also queries Supabase for similar past cases (RAG) before scoring |
| Report/Action Plan Agent | A tool function that formats the final structured output into the report |

This still satisfies "1 main agent orchestrates subagents with isolated context" architecturally, while staying buildable by 3 people in a week. If time allows later, any of these tool functions can be upgraded into a fully separate agent with its own dedicated prompt/model without changing the overall architecture.

---

## Why Not Handoffs or Router Instead?

- **Handoffs** would fit if different specialized agents needed to *take over talking to the user* at different stages (e.g., an "Intake Agent" handing off to a "Diagnosis Agent" who hands off to a "Report Agent," each owning the conversation for their stage). This adds sequential overhead we don't need — our orchestrator can just call tools instead of literally changing who's "in the driver's seat."
- **Router** is close to Subagents for our use case (also parallel + token-efficient) but is typically **stateless per request** — better suited to one-shot queries like a knowledge base lookup, not an ongoing multi-turn troubleshooting conversation. Since Step 1 needs to remember earlier answers across several turns, a stateful orchestrator (Subagents) fits better than a stateless router.

---

## How Do Subagents Actually Talk to Tools/Data? (Protocol Choice)

There are a few different "standards" floating around for how AI agents connect to things (databases, other agents, etc.) — worth being clear on which ones we're using and why, in plain terms:

- **Plain function calls (what we're using):** our subagents live in the *same codebase*. When the Cause Ranking Agent needs data from Supabase, it just calls a function we wrote ourselves — like calling any other function in your program. No extra moving parts.
- **MCP (Model Context Protocol):** a standard way for an AI to connect to a tool or data source *that isn't part of your own app* — e.g., a ready-made connector someone else built. We don't strictly need this since we're writing all our own tools, but it's an option: Supabase publishes its own MCP server, so we *could* plug into that instead of writing our own database functions, as a shortcut. Not required, just a nice-to-have.
- **A2A (Agent2Agent):** a standard for *independent* agents — often built by different teams/companies, running as separate services — to find each other and hand off work over a network. This solves a problem we don't have: all our subagents belong to us, in one app, called directly. Adding A2A would mean building agent "discovery" and negotiation machinery for agents that are actually just functions in our own code — unnecessary complexity for this timeline.
- **CALM:** this turned out not to be a real Anthropic protocol — it's unrelated tooling for documenting software architecture as code, not something agents use to talk to each other. Not relevant here.

**Bottom line: plain function calls, no added protocol layer.** Simplest, fastest to build, and matches our actual setup (one team, one codebase, one deployment).

---

## Future Consideration: Centralized Gateway Pattern (Not Now)

If this system grew into a real product with **many users and many agents hammering the same shared servers at once**, a common upgrade is a "gateway" — a middle layer that all agents talk to instead of talking to the database/tools directly. It can add rate limiting (stopping one agent from hogging resources), a shared cache, and traffic control.

**We're deliberately not building this**, for two reasons:
1. **We don't have the problem it solves.** We only have a couple of subagents running per session, not many agents fighting over the same resource at scale.
2. **It doesn't remove risk, it moves it.** A gateway becomes a new single point of failure — if it goes down, everything depending on it goes down too. Fixing that requires redundancy/failover setup, which is real infrastructure work, not something worth taking on for a week-long prototype.

Worth mentioning in the pitch as "how we'd scale this for production," but not something we implement now.

---

## Handling Multiple Users at the Same Time

Different users (e.g., two technicians using the tool at once) don't need any special agent coordination — they're just separate, independent sessions that never touch each other's data. This is a normal web-app concern, not an AI-specific one:

- Each session gets its own ID, and its conversation progress (questions asked so far, answers given) is saved in Supabase — **not** kept in the app's memory. This means any number of people can use the tool at the same time without their sessions mixing up.
- Supabase already handles multiple people reading/writing at once — nothing extra needed from us.
- The only shared limit is our OpenAI account's overall rate limit (requests per minute). For a hackathon demo, this is very unlikely to be hit — and if it ever is, the fix is just "wait and retry," not a custom system.

---

## Do We Need a Caching Layer? (No)

Short answer: no, and here's why in plain terms. Caching helps when the *same* request happens repeatedly, so you can skip redoing the work. But every user describes their dispensing problem differently, so there's rarely a repeat request to "cache" — each diagnosis genuinely needs to run fresh.

Our actual latency comes from the AI thinking (the LLM call itself), not from database speed — Supabase queries are already fast. So a caching layer would be solving a problem we don't have. What we're doing instead, which is simpler and actually helps:

- Not querying Supabase twice for the same thing in one session (e.g., if Cause Ranking already fetched similar past cases, don't fetch them again elsewhere).
- Running independent steps in parallel where possible (Text Defect ID + Image Defect ID run at the same time instead of one after another) — this cuts more real waiting time than caching would.
- A simple loading indicator in the UI while the AI works, so it *feels* fast during the demo even while it's genuinely thinking.

---

## Team-Proposed Feature: "Projects" (Scoped Troubleshooting Contexts)

Similar in spirit to Claude's Projects — the user can create a Project representing one machine, production line, or product (e.g., "Line 3 – Solder Paste Dispenser"). Everything that happens inside that Project stays scoped to it.

**Why this improves the architecture, not just the UI:**
- Right now, RAG (see implementation.md Section 2.1) pulls "similar past cases" from *all* history. Without scoping, a solder-paste line's history could get mixed into an adhesive line's cause-ranking — technically working, but noisier and less accurate.
- Adding a `project_id` to `case_history` and filtering every RAG lookup by it means the Cause Ranking Agent only ever compares against genuinely relevant past cases. This is a small change to the data layer with a real accuracy payoff.

**What changes in the flow:** the user picks (or creates) a Project *before* Step 1 of the Engine Flow begins. Every session, case, and RAG lookup after that point is automatically scoped to that Project's `project_id` — no other part of the Engine Flow needs to change.

**Scope check for the timeline:** this is just an extra table plus one filter added to existing queries — not a full permissions/sharing/file-upload system like Claude's Projects has. Keep it to: create a Project, select a Project, and scope history/RAG to it.

---

## Data Flow Summary

0. User selects or creates a **Project** (e.g., "Line 3 – Solder Paste Dispenser") — everything below is scoped to this Project's `project_id`.
1. User (Operator or Technician) opens a session → describes the problem in free text.
2. Orchestrator runs the **Question Agent** logic → asks up to ~5 adaptive follow-ups.
3. Once enough info is collected, Orchestrator calls **Text Defect ID** (and **Image Defect ID** in parallel, if a photo was uploaded).
4. Results merge → Orchestrator calls **Cause Ranking Agent**, which queries Supabase for similar past cases **within the same Project** (RAG) and returns ranked causes + confidence scores + reasoning.
5. Orchestrator calls **Report/Action Plan Agent** → produces the checklist and final report.
6. The completed case (problem, causes, solution, outcome, `project_id`) is written back to Supabase, growing that Project's case-history database for future RAG lookups.

---

## Resources — For Teammates Catching Up

If you want to see where the reasoning in this doc came from, here's what to read, grouped by topic:

**Multi-agent architecture (why we picked Subagents):**
- [Choosing the Right Multi-Agent Architecture — LangChain](https://www.langchain.com/blog/choosing-the-right-multi-agent-architecture) — the article that compares Subagents, Router, Skills, and Handoffs patterns with real token/latency numbers. This is where the "Subagents wins on multi-domain queries" numbers came from.

**MCP, A2A, and why we're not using either as a formal protocol:**
- [Introducing the Model Context Protocol — Anthropic](https://www.anthropic.com/news/model-context-protocol) — Anthropic's own announcement of MCP (connects an AI to tools/data).
- [modelcontextprotocol.io](https://modelcontextprotocol.io) — the official MCP spec/docs site, if you want more technical depth.
- [Implementing MCP in Multi-Agent AI Platforms — ML Journey](https://mljourney.com/implementing-mcp-in-multi-agent-ai-platforms/) — explains the Direct Connection, Centralized Gateway, and Hierarchical Orchestration patterns. This is where the Centralized Gateway trade-offs (and its single-point-of-failure risk) came from.
- [a2a-protocol.org](https://a2a-protocol.org) — official site for Google's Agent2Agent protocol (agent-to-agent, cross-vendor communication — not something we need here).
- **Note on "CALM":** a Medium article claimed Anthropic has a protocol called CALM. That's not accurate — the real CALM (linked below) is an unrelated FINOS/Morgan Stanley tool for documenting software architecture as code, not an agent communication protocol, and it isn't from Anthropic. Flagging this so nobody re-researches a dead end.
  - [calm.finos.org](https://calm.finos.org/introduction/what-is-calm) — the real CALM, for reference only.

**RAG / "learning database" implementation:**
- [Supabase MCP Server docs](https://supabase.com/docs/guides/getting-started/mcp) — if we ever want the optional MCP shortcut for our Supabase queries.
- [Supabase pgvector guide](https://supabase.com/docs/guides/database/extensions/pgvector) — how to set up vector/semantic similarity search (Option B in implementation.md Section 2.1), if we upgrade past keyword matching.

**Why we're not fine-tuning a model:**
- [OpenAI fine-tuning wind-down announcement](https://openai.com/index/introducing-improvements-to-the-fine-tuning-api-and-expanding-our-custom-models-program/) — see the "Update on May 8, 2026" note partway down the page; this is why fine-tuning isn't a realistic option for new projects right now, on top of it not fitting our timeline anyway.