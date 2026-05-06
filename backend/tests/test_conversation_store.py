from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from app.conversation_store import ConversationStore

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class ConversationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"conv_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.case_dir / "query_history.jsonl"

    def tearDown(self) -> None:
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_legacy_record_id_is_stable_and_lookup_works(self) -> None:
        legacy_row = {
            "raw_text": "[guest|main] does steam burn?",
            "node_path": ["steam", "heat", "burn"],
            "frozen_snapshot": "Based on graph memory: steam is a heat; heat causes burn.",
            "used_fallback": False,
            "confidence": 0.9,
            "timestamp": 1777990500.0,
        }
        self.history_path.write_text(json.dumps(legacy_row, ensure_ascii=True) + "\n", encoding="utf-8")
        store = ConversationStore(self.history_path)

        first = store.recent(limit=1)
        second = store.recent(limit=1)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0].id, second[0].id)
        self.assertEqual(first[0].raw_text, "does steam burn?")
        self.assertEqual(first[0].user_id, "guest")
        self.assertEqual(first[0].scope, "main")

        replay = store.get_by_id(first[0].id)
        self.assertIsNotNone(replay)
        self.assertEqual(replay.raw_text, "does steam burn?")


if __name__ == "__main__":
    unittest.main()
