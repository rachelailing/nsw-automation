# Team Update - 22 Sept

## Take Note

**The new deadline is 23 Sept (23rd September).**

Please treat the remaining work as final testing and demo preparation. Avoid adding large new features unless they are required for the main workflow.

## Progress

The main troubleshooting flow is working from start to finish:

- The user answers one diagnostic question at a time.
- The system checks measurements against stored limits.
- Repeated or unrelated answers are caught and clarified.
- The system identifies the defect, ranks likely causes, and recommends three actions.
- Sessions are saved, so the backend keeps the conversation state.
- Completed cases and user feedback are saved in Supabase.
- Each session uses the correct Project and approved Knowledge Pack.
- Knowledge Packs now contain materials, defect rules, actions, limits, and source records.
- Users can upload JSON, Markdown, text, and PDF knowledge files.
- Extracted content can be viewed before approval.
- Failed and pending uploads can be deleted. Approved sources are protected.
- A completed diagnosis can be downloaded as a PDF troubleshooting report.

Current checks:

- 43 backend tests pass.
- Frontend lint passes.
- Frontend production build passes.
- The generated PDF has been checked for layout and readability.

## System Architecture

```text
User
  |
  v
Next.js frontend
  |-- Diagnose: chat, results, PDF download
  |-- Knowledge: sources, extracted content, upload and delete
  |
  v
FastAPI backend
  |-- Controls the diagnostic question flow
  |-- Checks reference limits
  |-- Calls the AI agents
  |-- Extracts knowledge from uploaded files
  |-- Generates the PDF report
  |
  +--> OpenAI: defect analysis, cause ranking, report writing, file extraction
  |
  +--> Supabase: sessions, cases, feedback, limits, Knowledge Packs and sources
```

Knowledge file flow:

```text
Upload file -> Extract content -> Pending review -> Approve and publish -> Used in diagnosis
```

The first three steps are working. Approval and publishing are the next part to build. Pending uploads do not change the advice used by the diagnostic agents.

## Next Step

Priority for 23 Sept:

1. Add approve and reject actions for extracted Knowledge Pack content.
2. Publish approved content as a new Knowledge Pack version without changing old versions.
3. Run one complete test: upload, review, publish, diagnose, save feedback, and download PDF.
4. Prepare the demo data and remove failed test uploads that are no longer needed.
5. Confirm environment variables, Supabase tables, and local startup commands on the demo machine.

If time is limited, focus on a stable end-to-end demo. Version comparison, rollback, more file formats, user roles, and the drag-and-drop agent editor can follow after the deadline.
