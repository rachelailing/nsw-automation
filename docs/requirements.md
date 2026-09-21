# Requirements - AI Dispensing Defect Detective

## 1. Product Purpose

Fluid dispensing defects are often triaged through experience held by a small number of engineers. The product helps operators and technicians perform faster, consistent, and explainable preliminary troubleshooting without replacing engineering judgment.

The system must identify dispensing defects, compare measurements with approved limits, rank likely causes, recommend an ordered action plan, and retain validated outcomes for future cases.

## 2. Users

| User | Primary need |
|---|---|
| Operator | Report a defect quickly using simple language and measurements |
| Technician | Receive ranked causes, reasoning, and an actionable checklist |
| Engineer | Maintain specifications, rules, workflows, and approved knowledge |
| QA or training staff | Review reports, recurring defects, and validated solutions |

The Operator Console should remain simple. Advanced configuration belongs in a separate Engineer Studio.

## 3. Product Principles

1. **Evidence before inference:** use exact specifications and approved rules before LLM judgment.
2. **Explainability:** state why a defect or cause was selected and identify supporting evidence.
3. **No fabricated limits:** if no applicable threshold exists, say so.
4. **Controlled learning:** historical outcomes become trusted knowledge only after validation.
5. **Scoped context:** do not mix unrelated machines, materials, or production lines.
6. **Human authority:** engineers retain control over specifications, safety rules, and published workflows.

## 4. Functional Requirements

### 4.1 Guided diagnostic conversation

The current baseline flow must collect:

1. Material being dispensed.
2. Whether the amount or diameter is too large, too small, or otherwise abnormal, including a measured diameter when available.
3. Whether the defect is continuous or intermittent.
4. Whether relevant parameters or equipment recently changed.
5. Whether the defect occurs at one location or multiple locations.

The interface may combine related items in one message. It must not repeatedly ask for information already supplied.

Future Knowledge Packs may add optional questions for a specific process, but required questions must remain governed by the published workflow.

### 4.2 Threshold validation

When the user provides a supported numeric measurement, the system must:

- Retrieve the best applicable threshold for the material and process.
- Compare the measured value deterministically with minimum and maximum values.
- Return `below_min`, `pass`, or `above_max`.
- Cite the measured value and exact reference limit.
- Record the matched threshold row and version in the session.
- Continue without inventing a limit when no matching threshold exists.

Supported or planned parameters include diameter, dispensing volume, pressure, speed or flow rate, dispensing time, nozzle size, and dispensing height. Every value must have an explicit unit.

### 4.3 Defect identification

The system must classify the most likely defect and provide a confidence score and reasoning. Initial defect classes are:

- Missing Dot
- Oversized Dot
- Undersized Dot
- Irregular Shape
- Excessive Spreading

### 4.4 Cause ranking

The system must produce ranked probable causes. Each cause must include:

- Rank.
- Category.
- Confidence score.
- Reasoning linked to observed evidence.
- Evidence source type where available.

Cause categories include material condition, trapped air, dispensing parameters, nozzle condition, and equipment condition.

### 4.5 Action plan and report

The final response must include:

1. Detected defect and confidence score.
2. Most probable root cause and explanation.
3. Exactly three ordered troubleshooting actions.
4. The question, "Did this fix the issue?"

A completed case must be saved once, without duplicate history records if the report is requested again.

### 4.6 Outcome feedback

The next release must process the technician's response after the action plan. It must capture:

- Whether the issue was fixed.
- Which action was attempted.
- Confirmed cause, when known.
- Before and after measurements, when available.
- Technician notes.
- Reviewer and approval status.

Negative outcomes are valuable and must be retained so ineffective recommendations are not repeatedly promoted.

### 4.7 Session persistence

- Every browser session must have a unique session ID.
- Workflow stage, Q&A, intermediate results, and conversation history must persist in Supabase.
- Multiple simultaneous users must not share state.
- A user must be able to start a fresh case without manually clearing browser storage in the production UI.

### 4.8 Knowledge Packs

An engineer must be able to define a versioned Knowledge Pack containing:

- Applicable project, machine, line, product, or material.
- Material properties.
- Numeric thresholds and units.
- Defect and cause rules.
- Diagnostic questions.
- Approved troubleshooting actions.
- Safety constraints.
- Source references and revision metadata.
- Draft, approved, superseded, or archived status.

Only approved versions may influence production recommendations as authoritative evidence.

### 4.9 Projects and scoping

The planned Projects feature must scope sessions, thresholds, Knowledge Packs, and case-history retrieval to a machine, production line, or product. Global fallback knowledge must be explicitly labeled.

### 4.10 Engineer Studio and workflow customization

The planned Engineer Studio should allow authorized users to:

- Edit and publish Knowledge Packs.
- Configure approved workflow nodes and branches.
- Preview and test a workflow before publishing.
- Review proposed knowledge derived from cases.
- Roll back to an earlier version.
- Inspect an audit history.

Drag-and-drop is a desired interaction, not the workflow storage format. Workflow definitions must be stored as validated, versioned structured data.

## 5. Data Requirements

### Authoritative data

- Engineering specifications and accepted ranges.
- Material and machine applicability.
- Source, owner, revision, and approval status.

### Operational data

- Session and conversation state.
- Extracted measurements and units.
- Agent outputs and evidence references.
- Completed reports and recommended actions.

### Learning data

- Historical cases.
- Actions attempted.
- Successful and unsuccessful outcomes.
- Confirmed causes.
- Human review status.

Synthetic demonstration data must be labeled as synthetic. It must not be presented as production evidence.

## 6. Non-Functional Requirements

### Accuracy and safety

- Deterministic threshold comparisons must pass all boundary tests.
- The system must distinguish deterministic results from AI confidence.
- Missing evidence must reduce confidence rather than trigger fabrication.
- Safety-critical actions may require engineer approval.

### Explainability and traceability

- Every final cause must be traceable to specifications, expert rules, historical cases, or model inference.
- Completed cases should record model, prompt, workflow, and Knowledge Pack versions.
- Changes to approved knowledge must be auditable.

### Security

- Secret keys must remain on the backend.
- Supabase Row Level Security must be enabled with least-privilege policies.
- Roles must separate operators, technicians, and knowledge administrators.
- User input and uploaded content must be treated as untrusted.

### Reliability and usability

- Session state must survive page refresh and backend restart.
- Database or model failures must return a clear recoverable error.
- The core workflow must work on desktop and mobile layouts.
- Operators should not need agent or prompt-engineering knowledge.

### Performance

- Deterministic checks should return within the normal API round trip.
- Independent model tasks may run in parallel where applicable.
- The UI must display a stable loading state during multi-agent processing.

## 7. Current Scope Status

| Capability | Status |
|---|---|
| Web chat and API | Implemented |
| Five-stage, one-question-at-a-time diagnostic flow | Implemented |
| Session persistence | Implemented |
| Diameter threshold comparison | Implemented |
| Defect identification | Implemented |
| Cause ranking and similar-case lookup | Implemented |
| Three-step action plan | Implemented |
| Downloadable PDF troubleshooting report | Implemented |
| Completed-case persistence | Implemented |
| Outcome feedback processing | Implemented |
| Knowledge Pack schema, versioning, and structured content | Backend implemented |
| Knowledge source import and extraction preview | Implemented |
| Knowledge Pack inspection and import UI | Implemented |
| Knowledge Pack approval and publication UI | Planned |
| Project-scoped retrieval | Backend implemented; project selection UI planned |
| Evidence citations in UI | Planned |
| Engineer Studio | Planned |
| Drag-and-drop workflow builder | Future |
| Image upload UI | Deferred; backend analysis code exists |

## 8. Acceptance Scenario

Given a Solder Paste Knowledge Pack with a diameter range of `0.40-0.60 mm`:

1. User reports solder paste with a measured diameter of `0.95 mm`.
2. System states that `0.95 mm` is above the `0.60 mm` maximum.
3. System asks separately for frequency, recent changes, and location.
4. User reports a continuous issue across multiple locations on a new machine.
5. System returns an oversized defect with confidence, an evidence-based probable cause, exactly three actions, and asks whether the issue was fixed.
6. The completed case is saved once.

The scenario passes only if no extra unrelated questions are asked and the threshold values come from stored reference data.
