# Implementation Plan - AI Dispensing Defect Detective

## 1. Current Technical Baseline

The working prototype uses:

| Layer | Technology | Current responsibility |
|---|---|---|
| Frontend | Next.js | Chat UI, session ID, backend requests |
| Backend | FastAPI | API boundary and workflow execution |
| AI | OpenAI structured outputs | Defect classification, cause ranking, action plan |
| Database | Supabase PostgreSQL | Sessions, thresholds, and case history |
| Prototype reference | n8n and Telegram | Validated conversation sequence and expected response style |

The website now reproduces the core n8n workflow:

```text
Material
  -> amount or measured diameter
  -> immediate threshold result
  -> frequency plus recent changes
  -> affected location(s)
  -> defect classification
  -> cause ranking
  -> three-step action plan
  -> save completed case
```

## 2. Implemented Components

### Frontend

- `frontend/src/app/page.js`: main chat screen.
- `frontend/src/hooks/useChat.js`: browser session ID and message state.
- `frontend/src/lib/api.js`: FastAPI client using `NEXT_PUBLIC_BACKEND_URL`.

### Backend API and state

- `backend/main.py`: FastAPI application and CORS configuration.
- `backend/api/chat.py`: persisted chat endpoint.
- `backend/db/sessions.py`: creates, loads, and saves complete workflow state.

### Diagnostic runtime

- `backend/ai/orchestrator.py`: four-stage state machine and subagent orchestration.
- `backend/db/reference_thresholds.py`: numeric extraction, row selection, and deterministic comparisons.
- `backend/ai/subagents/text_defect_agent.py`: defect classification.
- `backend/ai/subagents/cause_ranking_agent.py`: ranked cause generation with similar cases.
- `backend/ai/subagents/report_agent.py`: exactly three corrective actions.
- `backend/db/case_history.py`: similar-case retrieval and completed-case storage.

### Database

- `sessions`: full conversation and orchestrator state.
- `reference_thresholds`: target, minimum, and maximum process values.
- `case_history`: completed diagnoses, causes, report, and outcome field.

## 3. Reasoning Strategy

The implementation must preserve an evidence hierarchy rather than treating all context as equal.

### 3.1 Deterministic threshold checks

The threshold engine owns numerical comparisons. The LLM receives a formatted result such as:

```text
diameter: measured 0.95, acceptable 0.40 to 0.60,
target 0.50, status above_max
```

Rules:

- Values and units come from approved data.
- Boundary behavior is deterministic and unit-tested.
- A missing threshold produces no pass/fail claim.
- The matched threshold record should eventually include Knowledge Pack version and source.

### 3.2 Expert troubleshooting knowledge

Expert relationships should be stored as structured rules, not buried only inside prompts. A rule should include:

```yaml
id: oversized-continuous-pressure
defect_type: Oversized Dot
conditions:
  frequency: continuous
possible_cause: Excessive dispensing pressure
reason: Continuous excessive deposits are consistent with excessive flow.
recommended_action: Verify pressure against the approved recipe.
source: Internal dispensing troubleshooting guide
status: approved
```

Prompts may explain and combine these rules, but the database remains the source of authority.

### 3.3 Historical case evidence

RAG currently retrieves recent cases by defect type. The next version should filter by project, material, machine, and Knowledge Pack before considering semantic similarity.

Historical cases must record whether the proposed fix worked. Unconfirmed reports should not be presented as proven solutions.

### 3.4 AI inference

AI subagents are used for classification, prioritization, and plain-language explanations. Their outputs use structured Pydantic schemas and low temperature. Model confidence must never be presented as equivalent to a deterministic threshold result.

## 4. Knowledge Pack Design

### 4.1 Authoring and runtime model

Use version-controlled YAML or JSON files for reviewable seed content:

```text
knowledge/
├── materials.yaml
├── defect_rules.yaml
├── troubleshooting_actions.yaml
└── demo_cases.json
```

Create an import script that validates these files and inserts a draft Knowledge Pack into Supabase. The application reads approved records from Supabase at runtime.

Do not load all files into every prompt. Retrieve only records applicable to the active project, material, defect, and workflow stage.

### 4.2 Proposed tables

```sql
projects (
  id, name, machine_name, production_line, created_at
)

knowledge_packs (
  id, project_id, name, version, status,
  source, approved_by, approved_at, created_at
)

materials (
  id, knowledge_pack_id, name, viscosity, properties, handling_notes
)

defect_rules (
  id, knowledge_pack_id, defect_type, conditions,
  possible_cause, reasoning, evidence_weight, source
)

troubleshooting_actions (
  id, knowledge_pack_id, cause, action, sequence,
  safety_notes, requires_approval
)

case_feedback (
  id, case_id, fixed, attempted_action, confirmed_cause,
  before_values, after_values, notes, review_status, created_at
)
```

Add `project_id` and `knowledge_pack_id` foreign keys to sessions, thresholds, and case history.

### 4.3 Approval lifecycle

```text
Draft -> In Review -> Approved -> Superseded -> Archived
```

Only one approved version should be active for a project and process at a time. Publishing a new version must not mutate the historical version referenced by completed cases.

## 5. Closed-Loop Learning

The immediate next implementation should handle the user's response to "Did this fix the issue?"

### Backend behavior

1. Replace the current `done` placeholder with a feedback stage.
2. Interpret yes/no without relying only on exact string matching.
3. Ask which action was attempted when ambiguous.
4. Store the outcome in `case_feedback` and mirror the summary in `case_history.outcome`.
5. Mark evidence as unreviewed until an engineer confirms it.

### Retrieval behavior

- Favor approved successful cases from the same Project and Knowledge Pack.
- Keep unsuccessful cases as negative evidence.
- Do not change threshold values based on case frequency.
- Generate proposed rule updates for review instead of publishing automatically.

### Useful learning metrics

- Fix success rate by recommended action.
- First-action resolution rate.
- Cases escalated to an engineer.
- Average diagnostic turns.
- Threshold-match coverage.
- Technician acceptance and override rate.

## 6. Engineer Studio

### Phase 1: form-based administration

Build CRUD screens for:

- Projects and machines.
- Materials and thresholds.
- Defect rules.
- Troubleshooting actions.
- Knowledge Pack review and publishing.
- Case feedback review.

This phase establishes authorization, validation, and versioning before visual workflow editing.

### Phase 2: configurable workflows

Store workflows as validated structured data:

```json
{
  "version": 1,
  "start": "material",
  "nodes": [
    {"id": "material", "type": "question", "required": true},
    {"id": "diameter", "type": "threshold_check", "parameter": "diameter"},
    {"id": "rank", "type": "cause_ranking"},
    {"id": "plan", "type": "action_plan", "steps": 3}
  ],
  "edges": [
    {"from": "material", "to": "diameter"},
    {"from": "diameter", "to": "rank"},
    {"from": "rank", "to": "plan"}
  ]
}
```

Validate node types, required stages, cycles, unreachable nodes, and permissions before publishing.

### Phase 3: drag-and-drop editor

Render the same workflow definition visually. The canvas is an editor for the structured workflow, not a separate execution engine. Include test mode, version comparison, publishing, and rollback.

## 7. Evidence in the Final Response

Extend cause output with evidence references:

```json
{
  "cause": "Excessive dispensing pressure",
  "confidence": 0.82,
  "reasoning": "The defect is continuous across multiple locations.",
  "evidence": [
    {"type": "threshold", "reference_id": 12},
    {"type": "expert_rule", "reference_id": 41},
    {"type": "historical_case", "reference_id": 103}
  ]
}
```

The UI can label evidence as Specification, Expert Rule, Similar Case, or AI Inference.

## 8. Testing Strategy

### Unit tests

- Numeric extraction and units.
- Minimum and maximum boundaries.
- Threshold row selection by material and available parameter.
- Workflow stage transitions.
- Duplicate case-save prevention.
- Knowledge Pack validation and publication rules.

### Integration tests

- Chat API with mocked model responses and a test database.
- Project-scoped threshold and case retrieval.
- Outcome feedback persistence.
- RLS behavior for each role.

### Evaluation set

Maintain a versioned set of expert-reviewed scenarios containing expected threshold status, defect, acceptable causes, forbidden claims, and required actions. Report accuracy by component rather than using one vague chatbot score.

## 9. Delivery Roadmap

### Milestone 1 - close the current loop

- Add a New Case control in the UI.
- Process fix feedback.
- Save successful and unsuccessful outcomes.
- Add one complete end-to-end integration test.

### Milestone 2 - establish governed knowledge

- Add Projects and Knowledge Pack tables.
- Import initial expert rules and actions.
- Add provenance and approval status.
- Scope all retrieval operations.
- Cite evidence in reports.

### Milestone 3 - provide engineer controls

- Build the form-based Engineer Studio.
- Add publishing, versioning, and rollback.
- Add case-review and proposed-rule workflows.

### Milestone 4 - workflow platform

- Introduce structured workflow definitions.
- Add preview and simulation.
- Add drag-and-drop editing after runtime validation is stable.

## 10. Definition of Done for the Next Release

The next release is complete when:

- A user can start a fresh case from the UI.
- The four-stage diagnosis remains stable.
- The final question accepts and stores a real outcome.
- Successful and unsuccessful actions are distinguishable.
- A completed case records its evidence and configuration versions.
- All current tests and the end-to-end acceptance scenario pass.
