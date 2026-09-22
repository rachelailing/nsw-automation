# Differentiation Strategy

## 1. What Every Group Is Likely to Build

The company brief already asks for:

- A troubleshooting chatbot.
- About five diagnostic questions.
- Defect identification.
- Ranked causes and confidence scores.
- Recommended actions.
- A simple report.

These features are necessary, but they are not enough to make the solution stand out.

## 2. Main Differentiator: Governed Knowledge Automation

Our strongest differentiator should be **policy-gated Knowledge Pack approval**.

Most AI troubleshooting systems either use fixed prompts or accept uploaded documents without strong control. Our system turns documents and successful cases into structured draft knowledge, checks that knowledge, assigns a risk level, and decides whether it can be approved automatically or must go to an engineer.

The key message is:

> The AI does not silently teach itself. The platform validates every proposed update, automatically approves only low-risk changes, and keeps engineers in control of process limits and safety.

Demo flow:

```text
Upload document
  -> extract material, defect rules and actions
  -> show source and extracted fields
  -> run validation and conflict checks
  -> show validation score and risk
  -> low risk: approve automatically
  -> high risk: request engineer approval
  -> publish a new version
  -> use that exact version in the next diagnosis
```

This is more credible than fully automatic approval. Thresholds, safety instructions, machine settings, and conflicting rules must always require an engineer.

## 3. Supporting Differentiators

### Evidence-backed recommendations

Each diagnosis should show whether a claim came from an engineering limit, expert rule, similar case, or AI inference. The PDF should carry the same references.

### Deterministic checks plus AI reasoning

The model explains and ranks causes, but code performs numeric pass/fail checks. This prevents the model from inventing accepted limits.

### Closed-loop outcomes

The system records whether a recommendation worked, which action was tried, and the confirmed cause. Successful and unsuccessful cases both improve future ranking after review.

### Reproducible decisions

Every session records its Project and Knowledge Pack version. A team can later explain exactly which limits and rules produced a recommendation.

### MCP-based integration

MCP gives the agents a standard, controlled way to query thresholds, approved rules, similar cases, document provenance, and future factory systems. MCP calls remain scoped, read-only at first, and auditable.

### Engineer-friendly output

The system produces an ordered action plan and downloadable PDF rather than only a chat answer. This makes the result usable for troubleshooting, handover, and training.

## 4. Recommended Focus

### Must demonstrate

1. The company-required five-step diagnosis.
2. Exact threshold comparison from stored data.
3. Ranked causes with clear reasoning.
4. Three ordered actions.
5. Saved outcome and downloadable PDF.

### Best differentiating demo

1. Upload a synthetic knowledge file.
2. Show extracted content and provenance.
3. Show automated validation, conflict checks, and risk level.
4. Automatically approve a harmless alias or wording change.
5. Show that a threshold change is blocked until an engineer approves it.
6. Publish a new Knowledge Pack version.
7. Run a diagnosis and show the new version and evidence references.

### Build only if time remains

- Read-only MCP server and one visible MCP tool trace.
- Version comparison and rollback.
- Overall dispensing quality score.
- Image upload and recognition.
- Drag-and-drop workflow editing.

## 5. Pitch

**AI Dispensing Defect Detective is not only a chatbot. It is a governed troubleshooting platform that combines exact engineering limits, explainable AI, controlled factory-tool access, and safely automated knowledge updates.**
