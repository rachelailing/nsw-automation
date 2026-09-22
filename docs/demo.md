# Demo and Presentation Guide

## 1. Presentation Goal

The presentation should show that AI Dispensing Defect Detective is more than a chatbot. It is a troubleshooting system that:

1. Understands the problem through guided questions.
2. Checks measurements against approved limits.
3. Explains and ranks likely causes.
4. Recommends what to do first and produces a report.
5. Learns from confirmed outcomes without changing engineering knowledge carelessly.

Target duration: **8 minutes**.

- Minimum version: 6 minutes.
- Recommended version: 8 minutes.
- Maximum version: 10 minutes.

## 2. Main Story

Use one sentence throughout the presentation:

> From defect report to verified action plan, with every recommendation grounded in approved knowledge and real outcomes.

Do not present the product as a general-purpose AI chatbot. Position it as an engineering troubleshooting workflow.

## 3. Layered Solution Positioning

Present the solution one layer at a time. Each layer answers one clear question.

### Layer 1 - Understand

**Question:** What is happening on the production line?

- Ask approximately five short diagnostic questions.
- Capture the material, measurement, frequency, recent changes, and affected location.
- Ask one question at a time.
- Detect repeated or unrelated answers.

**Presentation line:**

> We first turn an unclear operator complaint into structured evidence that the system can use.

### Layer 2 - Verify

**Question:** Is the result actually outside the approved process range?

- Compare measurements with stored engineering limits.
- Show the measured value and exact minimum or maximum.
- Keep numerical checks separate from AI confidence.
- Never invent a missing limit.

**Presentation line:**

> AI explains the problem, but code performs the pass-or-fail engineering check.

### Layer 3 - Diagnose

**Question:** What most likely caused the defect?

- Identify the defect and confidence score.
- Rank material, air, parameter, nozzle, and equipment causes.
- Use approved rules, similar cases, user answers, and threshold results.
- Explain why the top cause ranks highest.

**Presentation line:**

> The system does not give one generic answer. It ranks possible causes and shows the evidence behind the ranking.

### Layer 4 - Resolve

**Question:** What should the technician check first?

- Generate exactly three ordered actions.
- Prefer quick and safe checks before invasive work.
- Ask whether the recommended action fixed the issue.
- Generate a downloadable PDF troubleshooting report.

**Presentation line:**

> The output is an action sequence a technician can follow, not just a paragraph of AI advice.

### Layer 5 - Improve Safely

**Question:** How does the system improve without learning unsafe information?

- Save successful and unsuccessful outcomes.
- Keep knowledge separated by Project and Knowledge Pack version.
- Import documents as pending-review knowledge.
- Show extracted materials, rules, actions, source, and review status.
- Protect approved sources from deletion.

Planned differentiator:

- Automatically validate structure, units, sources, duplicates, conflicts, and regression tests.
- Automatically approve only low-risk changes.
- Require an engineer for thresholds, safety instructions, equipment settings, and conflicting rules.
- Publish an immutable new Knowledge Pack version with rollback.

**Presentation line:**

> The AI does not silently teach itself. Every proposed update is validated, risk-scored, and either safely approved or sent to an engineer.

## 4. Recommended 8-Minute Run of Show

| Time | Section | What the audience should understand |
|---|---|---|
| 0:00-0:35 | Hook | Dispensing troubleshooting depends too heavily on experienced engineers |
| 0:35-1:10 | Problem | Operators need faster, consistent preliminary troubleshooting |
| 1:10-1:50 | Layered solution | The product moves from understanding to safe improvement |
| 1:50-4:40 | Live diagnosis demo | The required company workflow works from start to report |
| 4:40-5:45 | Knowledge Pack demo | Knowledge is visible, sourced, scoped, and reviewable |
| 5:45-6:45 | Architecture | Deterministic checks, AI agents, database, and planned MCP have clear roles |
| 6:45-7:35 | Differentiation | Policy-gated knowledge approval is the main advantage |
| 7:35-8:00 | Close | State the value and final message |

## 5. Slide Plan

Use 7 to 8 slides. Keep the left side visual and the right side focused on one layer, similar to the inspiration images. Avoid dense architecture diagrams during the live demo.

### Slide 1 - Title and Hook

**Title:** AI Dispensing Defect Detective

**Subtitle:** From defect report to verified action plan

**On screen:**

- One strong screenshot of the Diagnose tab.
- Three short signals: `5 guided questions`, `Exact limit checks`, `3 ordered actions`.

**Say:**

> When dispensing quality changes, experienced engineers may know what to check immediately. New operators may not. Our system turns that experience into a repeatable troubleshooting workflow without replacing engineering judgment.

### Slide 2 - The Industry Problem

**Title:** One Defect, Too Much Guesswork

**On screen:**

- Oversized, undersized, inconsistent, missing, and spreading defects.
- A simple flow: defect occurs -> operator investigates -> engineer is called -> production waits.

**Say:**

> The challenge is not only identifying a defect. Teams must understand what caused it, what to check first, and whether the fix worked. Today, that process often depends on who is available and how much experience they have.

Do not add statistics unless the team has a reliable source.

### Slide 3 - Five Layers of the Solution

**Title:** A Troubleshooting System, Layer by Layer

**On screen:**

```text
Layer 1: Understand the problem
Layer 2: Verify against approved limits
Layer 3: Diagnose and rank causes
Layer 4: Resolve with ordered actions
Layer 5: Improve safely from outcomes and knowledge
```

**Say:**

> Each layer removes a different type of uncertainty. Together they move the user from an unclear complaint to an evidence-backed action plan.

### Slide 4 - Live Demo

**Title:** From 0.95 mm to a Clear Action Plan

Use the live website for this section. Keep the slide visible only before and after the live interaction.

Show these facts beside the product:

- Material: Solder paste
- Measured diameter: `0.95 mm`
- Approved maximum: `0.60 mm`
- Result: Oversized Dot

### Slide 5 - Knowledge That Can Be Trusted

**Title:** Knowledge Is Sourced, Reviewed, and Versioned

**On screen:**

- Screenshot of the Knowledge tab.
- Show source status: Completed, Pending review, Approved.
- Show extracted material, rule, and action.

**Say:**

> Instead of hiding all knowledge inside a prompt, we store it as structured records with a source and review status. Pending content cannot influence production diagnosis as approved evidence.

### Slide 6 - Architecture

**Title:** Clear Roles for Code, AI, and Engineering Knowledge

**On screen:**

```text
Next.js interface
       |
FastAPI workflow controller
       |
       +-- Exact threshold checks
       +-- Focused AI agents
       +-- Knowledge and case retrieval
       +-- PDF report generation
       +-- MCP tool access [roadmap]
       |
Supabase: sessions, versions, sources, cases and outcomes
```

**Say:**

> Code owns exact checks and workflow rules. AI owns classification, ranking, and explanation. Supabase stores the evidence and versions. MCP is our planned controlled connection to approved knowledge tools and future factory systems.

Do not present MCP as implemented. Describe it as the next integration layer.

### Slide 7 - What Makes Us Different

**Title:** Faster Knowledge Updates Without Losing Control

**On screen:**

```text
Upload -> Extract -> Validate -> Risk score -> Approve -> Publish
                                  |
                       Engineer gate when required
```

Show two examples:

| Change | Decision |
|---|---|
| Add a harmless material alias | May be approved automatically after checks |
| Change a pressure limit or safety action | Engineer approval required |

**Say:**

> Our differentiator is not uncontrolled self-learning. It is governed automation. The system handles repeatable validation and low-risk updates, while engineers keep authority over process limits and safety.

### Slide 8 - Closing

**Title:** Faster Troubleshooting. Safer Learning.

**On screen:**

- Faster preliminary diagnosis.
- Consistent evidence-based actions.
- Reusable troubleshooting knowledge.
- Engineers remain in control.

**Close with:**

> AI Dispensing Defect Detective helps teams move from defect report to verified action plan, then turns confirmed outcomes into safer and more useful knowledge for the next case.

## 6. Exact Live Demo Script

### Demo preparation

Before recording or presenting:

1. Start the frontend and backend.
2. Confirm Supabase and OpenAI connections.
3. Open a fresh browser session.
4. Keep the Knowledge tab preloaded with one successful synthetic source.
5. Remove failed test sources that distract from the story.
6. Confirm the PDF download works.
7. Keep a generated PDF open in another tab as a fallback.
8. Increase browser zoom so text is readable on a projector.

### Diagnosis inputs

Use this exact case for a stable demo:

| Question | Answer |
|---|---|
| Material | `Solder paste` |
| Amount or measurement | `The dot is too large, around 0.95 mm.` |
| Frequency | `It happens continuously on every part.` |
| Recent changes | `No parameters changed, but this is a new machine.` |
| Location | `Across multiple locations.` |

### What to point out

1. After `0.95 mm`, pause and highlight the exact `0.60 mm` maximum.
2. Explain that this is a database comparison, not an AI guess.
3. Continue the remaining questions without adding extra conversation.
4. At the result, point to the defect confidence, top cause, reasoning, and three actions.
5. Select **Download PDF** and briefly show the generated report.
6. Answer the feedback flow:
   - `Yes`
   - `I reduced the dispensing pressure to the approved setting.`
   - `The dispensing pressure was too high.`
7. State that the outcome is saved for future troubleshooting evidence.

### Knowledge Pack demonstration

1. Open the **Knowledge** tab.
2. Select `synthetic_knowledge_pack.md` or the prepared successful source.
3. Show its extraction status and pending-review status.
4. Show the extracted material, defect rule, conditions, evidence weight, action, and safety note.
5. State clearly that pending content is visible but does not become approved production advice automatically.
6. Use Slide 7 to explain the planned validation and approval gate.

Avoid uploading a PDF live unless it has already been tested on the presentation machine. A live model extraction can introduce unnecessary delay.

## 7. Six-Minute Cut

If only 6 minutes are available:

- Problem and hook: 40 seconds.
- Five-layer overview: 40 seconds.
- Diagnosis demo: 2 minutes 40 seconds.
- Knowledge Pack and differentiation: 1 minute.
- Architecture and close: 1 minute.

Remove:

- Detailed MCP explanation.
- Full feedback conversation.
- Multiple Knowledge Pack records.
- Version rollback discussion.

## 8. Ten-Minute Expanded Version

If 10 minutes are available, add:

- The confirmed feedback flow.
- A closer look at evidence classes.
- The PDF report sections.
- A Knowledge Pack extraction preview.
- Automatic approval versus mandatory engineer review examples.
- One architecture slide explaining MCP and future factory integrations.

Do not add a second diagnosis case. It weakens the main story and increases demo risk.

## 9. Visual Style

Follow the useful parts of the inspiration:

- One clear layer or promise per slide.
- Product screenshot on one side and the story on the other.
- Use one large number or comparison only when it is real, such as `0.95 mm > 0.60 mm`.
- Use short step labels instead of paragraphs.
- Highlight one sentence in a contrasting color.
- Keep screenshots large enough to read from the back of a room.
- Use the same five layer names throughout the deck and demo.

Avoid:

- Unverified market statistics.
- Long paragraphs on slides.
- Showing source code during the main demo.
- Claiming planned MCP or automatic approval features are complete.
- Presenting AI confidence as an engineering pass-or-fail result.

## 10. Recording Guidance

For a recorded video:

1. Record the live demo separately from the spoken presentation.
2. Remove loading pauses in editing, but do not hide errors or change results.
3. Use a visible pointer or subtle zoom when highlighting the threshold and final actions.
4. Keep the browser and slide text at a readable size.
5. Add short chapter labels: Understand, Verify, Diagnose, Resolve, Improve Safely.
6. End on the closing slide, not on the browser or code editor.

## 11. Demo Failure Plan

Prepare these backups:

- A screenshot of the threshold result.
- A screenshot of the final diagnosis.
- A completed PDF report.
- A screenshot of the Knowledge extraction preview.
- One slide showing the full workflow.

If the live API fails, say:

> We have a recorded run of the same test case. I will use it to show the expected workflow while keeping the session evidence and output unchanged.

Do not troubleshoot environment variables or database connections in front of judges.

## 12. Likely Questions

### Is this replacing engineers?

No. It speeds up preliminary troubleshooting and keeps engineers in control of specifications, safety, and high-risk knowledge changes.

### Why not use one chatbot prompt?

Exact limits, source records, versions, and confirmed outcomes need structured storage and deterministic checks. A prompt alone cannot provide the same control or traceability.

### How does it learn?

It saves whether an action worked and retrieves reviewed outcomes for similar cases. It does not rewrite engineering limits automatically.

### What is MCP doing?

MCP is the planned standard tool layer for reading approved thresholds, rules, cases, and future factory systems through controlled, audited calls.

### Can uploaded documents immediately change recommendations?

No. They are extracted as pending-review content. The planned policy engine will validate and risk-score changes, with mandatory engineer approval for thresholds and safety.

### What is the main differentiator?

Governed knowledge automation: fast document-to-knowledge processing, automatic checks, low-risk approval where safe, and an engineer gate where it matters.
