import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from db.case_history import get_similar_cases
from db.knowledge_packs import get_active_knowledge_pack
from db.knowledge_content import get_knowledge_content, format_knowledge_context
from db.reference_thresholds import get_best_threshold_row
from db.sessions import default_session_state
from api.knowledge import delete_knowledge_source


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.filters = []
        self.operation = "select"

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeClient:
    def __init__(self, table_data):
        self.table_data = table_data
        self.queries = {}

    def table(self, name):
        query = FakeQuery(self.table_data.get(name, []))
        self.queries[name] = query
        return query


class TestKnowledgePackScoping(unittest.IsolatedAsyncioTestCase):
    @patch("db.knowledge_packs.get_client")
    async def test_active_pack_uses_default_project_and_approved_status(self, mock_get_client):
        client = FakeClient(
            {
                "projects": [{"id": 10, "name": "Demo Dispensing Project"}],
                "knowledge_packs": [
                    {
                        "id": 20,
                        "project_id": 10,
                        "name": "Standard Dispensing Knowledge",
                        "version": 1,
                        "status": "approved",
                    }
                ],
            }
        )
        mock_get_client.return_value = client

        result = await get_active_knowledge_pack()

        self.assertEqual(result["id"], 20)
        self.assertIn(("name", "Demo Dispensing Project"), client.queries["projects"].filters)
        self.assertIn(("project_id", 10), client.queries["knowledge_packs"].filters)
        self.assertIn(("status", "approved"), client.queries["knowledge_packs"].filters)

    @patch("db.case_history.get_client")
    async def test_similar_cases_are_scoped_to_project_and_pack(self, mock_get_client):
        client = FakeClient({"case_history": []})
        mock_get_client.return_value = client

        await get_similar_cases(
            "Oversized Dot",
            project_id=10,
            knowledge_pack_id=20,
        )

        filters = client.queries["case_history"].filters
        self.assertIn(("defect_type", "Oversized Dot"), filters)
        self.assertIn(("project_id", 10), filters)
        self.assertIn(("knowledge_pack_id", 20), filters)

    @patch("db.supabase_client.get_client")
    async def test_thresholds_are_scoped_to_project_and_pack(self, mock_get_client):
        client = FakeClient({"reference_thresholds": []})
        mock_get_client.return_value = client

        await get_best_threshold_row(
            problem_description="Oversized solder paste dot",
            qa_pairs=[],
            project_id=10,
            knowledge_pack_id=20,
        )

        filters = client.queries["reference_thresholds"].filters
        self.assertIn(("project_id", 10), filters)
        self.assertIn(("knowledge_pack_id", 20), filters)

    def test_default_session_state_keeps_scope(self):
        state = default_session_state(project_id=10, knowledge_pack_id=20)

        self.assertEqual(state["project_id"], 10)
        self.assertEqual(state["knowledge_pack_id"], 20)

    @patch("db.knowledge_content.get_client")
    async def test_structured_content_is_scoped_to_pack_and_defect(self, mock_get_client):
        client = FakeClient(
            {
                "materials": [{"id": 1, "name": "Solder Paste"}],
                "defect_rules": [
                    {
                        "id": 2,
                        "defect_type": "Oversized Dot",
                        "possible_cause": "Pressure is too high",
                    }
                ],
                "troubleshooting_actions": [
                    {
                        "id": 3,
                        "defect_type": "Oversized Dot",
                        "action": "Verify pressure.",
                    }
                ],
            }
        )
        mock_get_client.return_value = client

        result = await get_knowledge_content(20, defect_type="Oversized Dot")

        self.assertEqual(len(result["materials"]), 1)
        for table in ("materials", "defect_rules", "troubleshooting_actions"):
            self.assertIn(("knowledge_pack_id", 20), client.queries[table].filters)
        self.assertIn(
            ("defect_type", "Oversized Dot"),
            client.queries["defect_rules"].filters,
        )
        self.assertIn(
            ("defect_type", "Oversized Dot"),
            client.queries["troubleshooting_actions"].filters,
        )

    def test_knowledge_context_includes_evidence_ids_and_safety(self):
        context = format_knowledge_context(
            {
                "materials": [],
                "defect_rules": [
                    {
                        "id": 2,
                        "source_id": 7,
                        "defect_type": "Oversized Dot",
                        "possible_cause": "Pressure is too high",
                        "category": "Dispensing Parameters",
                        "reasoning": "Excess flow increases dot size.",
                        "evidence_weight": 0.9,
                    }
                ],
                "troubleshooting_actions": [
                    {
                        "id": 3,
                        "source_id": 7,
                        "sequence": 1,
                        "cause": "Pressure is too high",
                        "action": "Verify pressure.",
                        "requires_approval": True,
                        "safety_notes": "Stay inside the qualified window.",
                    }
                ],
            }
        )

        self.assertIn("[rule:2; source:7]", context)
        self.assertIn("[action:3; source:7]", context)
        self.assertIn("engineer approval required", context)
        self.assertIn("Stay inside the qualified window", context)

    @patch("api.knowledge.get_active_knowledge_pack", new_callable=AsyncMock)
    @patch("api.knowledge.get_client")
    async def test_pending_source_can_be_deleted(
        self,
        mock_get_client,
        mock_get_active_pack,
    ):
        mock_get_active_pack.return_value = {"id": 20}
        client = FakeClient(
            {
                "knowledge_sources": [
                    {
                        "id": 7,
                        "review_status": "pending_review",
                        "original_filename": "failed.md",
                    }
                ]
            }
        )
        mock_get_client.return_value = client

        result = await delete_knowledge_source(7)

        self.assertTrue(result["deleted"])
        self.assertEqual(result["source_id"], 7)
        self.assertEqual(client.queries["knowledge_sources"].operation, "delete")

    @patch("api.knowledge.get_active_knowledge_pack", new_callable=AsyncMock)
    @patch("api.knowledge.get_client")
    async def test_approved_source_cannot_be_deleted(
        self,
        mock_get_client,
        mock_get_active_pack,
    ):
        mock_get_active_pack.return_value = {"id": 20}
        mock_get_client.return_value = FakeClient(
            {
                "knowledge_sources": [
                    {
                        "id": 1,
                        "review_status": "approved",
                        "source_name": "Approved source",
                    }
                ]
            }
        )

        with self.assertRaises(HTTPException) as raised:
            await delete_knowledge_source(1)

        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
