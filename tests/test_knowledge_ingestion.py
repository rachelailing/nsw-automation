import os
import sys
import unittest
from pathlib import Path

from openai.lib._pydantic import to_strict_json_schema

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from services.knowledge_ingestion import (
    KnowledgeExtraction,
    extract_source_text,
    extract_structured_knowledge,
)


FIXTURES = Path(__file__).parent / "fixtures"


class TestKnowledgeIngestion(unittest.TestCase):
    def test_structured_json_is_validated_without_model_call(self):
        path = FIXTURES / "synthetic_knowledge_pack.json"
        text, source_type = extract_source_text(path.name, path.read_bytes())

        result = extract_structured_knowledge(text, source_type)

        self.assertEqual(source_type, "json")
        self.assertEqual(result["materials"][0]["name"], "Synthetic Silver Epoxy")
        self.assertEqual(result["defect_rules"][0]["defect_type"], "Undersized Dot")
        self.assertEqual(
            result["defect_rules"][0]["conditions"]["frequency"],
            "continuous",
        )
        self.assertTrue(result["troubleshooting_actions"][0]["requires_approval"])

    def test_model_response_schema_contains_no_open_objects(self):
        schema = to_strict_json_schema(KnowledgeExtraction)

        def assert_closed_objects(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False)
                for value in node.values():
                    assert_closed_objects(value)
            elif isinstance(node, list):
                for value in node:
                    assert_closed_objects(value)

        assert_closed_objects(schema)

    def test_markdown_text_is_extracted_for_review(self):
        path = FIXTURES / "synthetic_knowledge_pack.md"

        text, source_type = extract_source_text(path.name, path.read_bytes())

        self.assertEqual(source_type, "md")
        self.assertIn("Synthetic Silver Epoxy", text)
        self.assertIn("Engineer approval is required", text)

    def test_pdf_text_is_extracted_for_review(self):
        path = FIXTURES / "synthetic_knowledge_pack.pdf"

        text, source_type = extract_source_text(path.name, path.read_bytes())

        self.assertEqual(source_type, "pdf")
        self.assertIn("Synthetic Silver Epoxy", text)
        self.assertIn("synthetic process window", text)

    def test_unsupported_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported file type"):
            extract_source_text("source.docx", b"not supported")

    def test_empty_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            extract_source_text("source.md", b"")


if __name__ == "__main__":
    unittest.main()
