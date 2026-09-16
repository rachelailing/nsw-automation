# Requirements — AI Dispensing Defect Detective
**Source:** AI Horizon Solution Challenge 2026 — NSW Automation
**Tagline:** "Helping Manufacturers Identify Dispensing Problems Faster with AI"

---

## 1. Background

Fluid dispensing is widely used in electronics and semiconductor manufacturing to apply materials such as adhesives, solder paste, epoxy, sealants, and other industrial fluids. Dispensing defects can occur during production, including:

- Too little material dispensed
- Too much material dispensed
- Inconsistent dispensing size
- Missing dispensing dots
- Material spreading beyond the required area
- Air bubbles or abnormal dispensing shapes

When defects occur, engineers and operators need to identify what went wrong, what might have caused it, and what to check first. Experienced engineers can diagnose these problems quickly, but new technicians and operators need more time and experience — creating an opportunity for an AI-based assistant.

**Vision:** Design and develop an AI-powered troubleshooting assistant that analyses common fluid dispensing problems, identifies and ranks possible causes, explains its reasoning, and recommends a logical troubleshooting sequence. The goal is not to replace engineers, but to help engineers and technicians perform faster preliminary troubleshooting.

---

## 2. Problem Statements

- New technicians/operators lack the experience to quickly diagnose dispensing defects.
- Root-cause identification currently relies heavily on experienced engineers, creating a bottleneck.
- There is no fast, structured, explainable way to triage a dispensing problem before an engineer gets involved.
- Existing troubleshooting knowledge is not systematically captured or reused across similar past cases.

---

## 3. Users

*Clarified by NSW Automation admin:*
- **Operators** — focus on daily machine operation and production monitoring. They're the ones most likely to *first notice* a defect while running the equipment, but troubleshooting isn't their core job.
- **Technicians** — focus on troubleshooting, maintenance, calibration, and technical support. They're the primary users of the diagnostic/cause-ranking output.

Other users:
- **Experienced engineers** — may use the tool for faster preliminary triage and to validate AI reasoning.
- (Implied) **Training/QA staff** — could use generated reports as a training tool.

*Design implication:* the tool likely needs to support two slightly different use patterns — Operators reporting *"something looks wrong"* (simple, fast input), and Technicians actively working through the diagnosis (deeper Q&A, checklist, action plan).

---

## 4. Dataset & Sources

*Clarified by NSW Automation admin:* No dataset will be provided — **participants must source their own suitable public dataset(s)**, including open-source or synthetic datasets where appropriate.

Implied/likely inputs based on the described functionality:

- User-described problem text (free text describing the defect)
- User-uploaded images of dispensing results (Bonus Challenge 1) — will need a public or synthetic image dataset of dispensing defects (or a visually similar proxy, e.g., adhesive/solder dispensing defect images, if an exact match isn't available)
- A troubleshooting knowledge base / historical case database (Bonus Challenge 3), storing:
  - Dispensing Problem
  - Possible Causes
  - Recommended Solutions
  - Successful Solution
- **Action item:** search for public datasets (e.g., Kaggle, Roboflow Universe, academic manufacturing-defect datasets) covering dispensing/adhesive/solder-paste defects, or PCB/SMT defect datasets as a proxy. If nothing suitable is found, generate a small synthetic dataset (e.g., simulated case entries, or AI-generated/labelled defect images) — just be ready to explain the sourcing/generation method to judges, since it affects credibility of the demo.

---

## 5. AI Model

*Not explicitly specified in the source document.* Requirements implied by the described behavior:

- Must support conversational/question-driven interaction (asks ~5 diagnostic questions, with dynamic follow-ups based on answers — Bonus Challenge).
- Must classify/identify the most likely defect type from user input.
- Must generate and rank multiple possible causes with an explainable confidence/likelihood score (e.g., percentage or star rating).
- Must produce natural-language reasoning/justification for each ranked cause (not generic answers).
- **Bonus:** Image recognition model to classify dispensing defects from uploaded photos (e.g., Missing Dot, Oversized Dot, Undersized Dot, Irregular Shape, Excessive Spreading).
- **Bonus:** Learning capability — reference/learn from historical cases stored in a database to inform future recommendations.
- **Note:** No specific model architecture, provider, or training approach is mandated — left to the team to choose based on the "Suggested Technology Level" below.

---

## 6. Engine Flow

**Step 1 — Dispensing Problem Discovery**
AI asks ~5 smart diagnostic questions, e.g.:
- What material is being dispensed?
- Is the dispensing amount too large or too small?
- Is the defect happening continuously or occasionally?
- Has the material, nozzle, or process setting recently changed?
- Is the defect happening at one location or across multiple locations?
- *(Bonus)* Dynamically ask additional follow-up questions based on user answers.

**Step 2 — Identify the Dispensing Defect**
AI analyses input and identifies the most likely defect, with a confidence level and possible symptoms.

**Step 3 — AI Cause Analysis**
AI generates a list of possible causes (e.g., material condition, air bubbles, dispensing parameters, nozzle condition, equipment condition).

**Step 4 — Generate an AI Troubleshooting Score**
AI produces a probability/confidence score per possible cause, with an explanation of *why* each cause is ranked as it is (logical reasoning, not generic output).

**Step 5 — Generate a Troubleshooting Action Plan**
AI recommends an ordered sequence of checks/actions for the user to perform.

**Step 6/7 — Report Generation**
Engine compiles the above into a simple troubleshooting report.

Full engine sequence: Define problem → AI asks questions → Analyse symptoms → Compare possible causes → Rank possible causes → Recommend troubleshooting sequence → Generate report.

---

## 7. Additional Requirements (may have been missed)

### 7.1 Functional Requirements
- Accept free-text problem descriptions from the user as input.
- Support multi-turn, adaptive Q&A (not a fixed static form).
- Output must include: identified defect, ranked causes with confidence scores, reasoning/explanation, and a recommended action sequence.

### 7.2 Bonus / Stretch Features
- **Image Recognition:** Upload and analyze a photo of the dispensing result to detect defect type.
- **AI Dispensing Quality Score:** Generate a quality assessment (e.g., Shape Consistency, Size Consistency, Dispensing Position, Defect Risk, Overall Score out of 100).
- **AI Learning Database:** Store past cases and reference historical frequency/outcomes (e.g., "Similar problems occurred 12 times previously; in 8 cases the cause was X").
- **PDF Troubleshooting Report Generation:** Auto-generate a report containing Problem Description, Dispensing Defect, AI Analysis, Possible Causes, Confidence Score, Recommended Troubleshooting Actions, and Engineer Notes.

### 7.3 Non-Functional / Design Requirements
- Reasoning must be explainable — every ranked cause needs a logical justification, not a generic/black-box answer.
- System should be usable by both novice technicians and experienced engineers (adaptive to user knowledge level).
- Should support multiple people using the tool at the same time (e.g., during live judging), with each person's session kept fully separate — see system-architecture.md for how this is handled.

### 7.4 Suggested Technology Levels (project scoping tiers)
| Level | Requirement |
|---|---|
| Basic | AI chatbot + troubleshooting questions |
| Intermediate | AI diagnosis + cause ranking + recommendations |
| Advanced | Image analysis + troubleshooting database + report generation |

### 7.5 Open Items / Not Specified in Source (to clarify with stakeholders)
- Target AI model/framework (LLM, CV model, etc.)
- Deployment environment (web app, desktop, embedded on shop floor, etc.)
- Success/evaluation metrics for the competition submission
- UI/UX requirements beyond the conversational flow
