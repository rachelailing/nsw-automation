# System Architecture - AI Dispensing Defect Detective

## 1. Architecture Goal

The solution is an evidence-grounded troubleshooting platform for fluid dispensing defects. It combines exact engineering checks with AI reasoning instead of asking a language model to diagnose from general knowledge alone.

The product highlight is its hybrid reasoning model:

1. Deterministic checks compare measured values with approved limits.
2. Expert knowledge describes known defect, cause, and corrective-action relationships.
3. Historical cases show what previously worked on similar equipment and materials.
4. Focused AI subagents rank the evidence and explain the recommended actions.
5. Technician feedback closes the learning loop after a recommendation is tested.

This design keeps numerical decisions testable, AI reasoning explainable, and learned knowledge under engineering control.

## 2. System Context

```text
Operator Console                         Engineer Studio (roadmap)
       |                                          |
       +---------------- API Layer ---------------+
                          |
                Diagnostic Workflow Runtime
                 - conversation state
                 - workflow stages
                 - subagent orchestration
                          |
       +------------------+-------------------+
       |                  |                   |
Threshold Engine     AI Subagents       Evidence Fusion
       |                  |                   |
       +------------- Knowledge Service -----+
                          |
       +------------------+-------------------+
       |                  |                   |
Specifications       Expert Rules       Case Outcomes
                          |
                       Supabase
```

### Current user-facing applications

- **Operator Console:** Next.js chat interface used to report a defect and answer guided questions.
- **Engineer Studio:** planned administration interface for maintaining Knowledge Packs and workflow configurations. It is not part of the current prototype.

## 3. Runtime Components

### 3.1 Next.js frontend

The frontend provides the chat experience, generates a browser session ID, and calls the FastAPI backend. The session ID is stored in browser local storage so a conversation can resume after a refresh.

### 3.2 FastAPI API layer

The backend exposes chat, diagnosis, and report endpoints. It is the trusted boundary for OpenAI calls and Supabase operations. API keys are never sent to the browser.

### 3.3 Diagnostic workflow runtime

The orchestrator is a persisted state machine. The current workflow uses four controlled stages validated by the n8n prototype:

1. Material being dispensed.
2. Observed amount or measured diameter.
3. Frequency and recent parameter changes.
4. One location or multiple locations.

After stage 2, a measured diameter is checked immediately against the reference table. After stage 4, the workflow automatically runs defect identification, cause ranking, action-plan generation, and case-history persistence.

The fixed core stages prevent repeated or irrelevant questions. Future Knowledge Packs may configure wording and optional questions without bypassing required evidence.

### 3.4 Threshold engine

The threshold engine extracts numeric measurements and compares them with values in `reference_thresholds`. It produces one of three deterministic results:

- `below_min`
- `pass`
- `above_max`

The response cites the measured value and exact accepted limit. The LLM receives this result as evidence but does not invent or modify the limit.

### 3.5 AI subagents

The project uses centralized orchestration with focused, stateless subagents:

| Subagent | Responsibility | Evidence supplied |
|---|---|---|
| Text Defect Agent | Classifies the defect and explains the classification | User description, Q&A, threshold result |
| Image Defect Agent | Classifies visible symptoms from an image | Image and limited context; backend exists but upload UI is currently disabled |
| Cause Ranking Agent | Ranks probable causes with confidence and reasoning | Defect result, Q&A, thresholds, similar cases |
| Report Agent | Generates exactly three ordered corrective actions | Diagnosis and ranked causes |

The orchestrator owns state and sequencing. Subagents do not communicate directly or maintain private conversation memory.

### 3.6 Evidence fusion

Cause ranking should distinguish the origin of each claim:

| Evidence class | Example | Trust level |
|---|---|---|
| Specification | `0.95 mm > 0.60 mm maximum` | Deterministic |
| Expert rule | Continuous oversized deposits can indicate excessive pressure | Engineer-approved |
| Historical case | The same adjustment solved similar cases | Observational |
| Model inference | A plausible cause inferred from combined context | Probabilistic |

The roadmap includes displaying these sources beside each recommendation.

## 4. Knowledge Architecture

### 4.1 Knowledge Packs

A Knowledge Pack is the approved context for one machine, production line, product, or process. It can contain:

- Materials and material properties.
- Parameter names, units, targets, and accepted ranges.
- Defect-to-cause rules.
- Approved diagnostic questions.
- Troubleshooting actions and safety constraints.
- Source, revision, owner, approval status, and effective date.

Version-controlled YAML or JSON files may be used to author and seed this knowledge. Supabase is the runtime source so that the application can query, version, approve, and scope records reliably.

### 4.2 Knowledge layers

```text
Layer 1: Approved specifications and safety constraints
Layer 2: Engineer-authored troubleshooting rules and playbooks
Layer 3: Confirmed historical cases and successful outcomes
Layer 4: Session-specific AI inference
```

Higher-numbered layers cannot silently overwrite lower-numbered layers.

### 4.3 Controlled learning

"Learning" means retrieving and weighting confirmed outcomes, not allowing the model to rewrite engineering data automatically.

```text
Recommendation -> technician tests action -> outcome captured
       -> proposed case evidence -> engineer review
       -> approved knowledge version -> future retrieval
```

Thresholds and safety rules require human approval. Unreviewed cases may be stored but must be labeled as unverified evidence.

## 5. Data Architecture

### Implemented tables

| Table | Purpose |
|---|---|
| `sessions` | Persisted workflow stage, Q&A, conversation history, and intermediate results |
| `reference_thresholds` | Deterministic material and process limits |
| `case_history` | Completed diagnoses, ranked causes, reports, and optional outcome |

### Planned tables

| Table | Purpose |
|---|---|
| `projects` | Scope data to a machine, line, or product |
| `knowledge_packs` | Version and approval metadata |
| `materials` | Material properties and handling information |
| `defect_rules` | Expert-authored defect/cause relationships |
| `troubleshooting_actions` | Approved corrective actions and constraints |
| `case_feedback` | Tested action, confirmed cause, outcome, and reviewer |
| `workflow_definitions` | Versioned Engineer Studio workflow configuration |

All retrieval must eventually be filtered by `project_id` or `knowledge_pack_id` to prevent evidence from unrelated machines or materials from being mixed.

## 6. Configurable Agent Workflows

The planned Engineer Studio can expose a controlled visual workflow builder with approved node types:

- Ask Diagnostic Question
- Check Reference Threshold
- Retrieve Similar Cases
- Identify Defect
- Rank Causes
- Generate Action Plan
- Require Engineer Approval
- Save Outcome

Users may configure wording, optional branches, and knowledge sources. The platform must still enforce required stages, valid node connections, threshold approval, workflow versioning, and audit history.

The first implementation should be a form-based workflow editor backed by the same workflow schema. Drag-and-drop is a presentation layer added after the runtime contract is stable.

## 7. Security and Reliability

- Keep OpenAI and privileged Supabase credentials on the backend.
- Use Row Level Security and least-privilege database policies.
- Treat uploaded or user-entered text as untrusted input.
- Record prompt, workflow, model, and Knowledge Pack versions with every completed case.
- Fail safely when threshold data is missing; never fabricate accepted limits.
- Separate AI confidence from deterministic pass/fail results.
- Require human approval before promoted knowledge affects production recommendations.

## 8. Current Status and Roadmap

### Implemented

- Next.js chat interface and FastAPI backend.
- Persisted Supabase sessions.
- Four-stage n8n-compatible diagnostic conversation.
- Immediate diameter threshold validation.
- Text defect classification, cause ranking, and three-step action plan.
- Similar-case retrieval and completed-case persistence.

### Next

1. Capture the answer to "Did this fix the issue?" and the confirmed action/cause.
2. Add Knowledge Pack schema, seed files, versioning, and provenance.
3. Scope sessions, thresholds, and cases by Project.
4. Cite evidence sources in the final diagnosis.
5. Add an Engineer Studio for editing and approving knowledge.
6. Add configurable workflows, followed by a drag-and-drop editor.

## 9. Solution Positioning

The solution is not differentiated merely by using multiple agents. Its key contribution is a closed-loop diagnostic system that combines deterministic engineering limits, approved troubleshooting knowledge, and machine-specific historical outcomes to produce explainable recommendations that improve through validated technician feedback.
