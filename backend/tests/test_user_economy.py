from __future__ import annotations

import os
import shutil
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class UserEconomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"economy_{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)
        self._old_data_dir = os.environ.get("PARAGI_DATA_DIR")
        self._old_prefer_hdf5 = os.environ.get("PARAGI_PREFER_HDF5")
        os.environ["PARAGI_DATA_DIR"] = str(self.case_dir)
        os.environ["PARAGI_PREFER_HDF5"] = "0"

    def tearDown(self) -> None:
        if self._old_data_dir is None:
            os.environ.pop("PARAGI_DATA_DIR", None)
        else:
            os.environ["PARAGI_DATA_DIR"] = self._old_data_dir

        if self._old_prefer_hdf5 is None:
            os.environ.pop("PARAGI_PREFER_HDF5", None)
        else:
            os.environ["PARAGI_PREFER_HDF5"] = self._old_prefer_hdf5

        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_main_vs_personal_graph_and_credit_award(self) -> None:
        with TestClient(app) as client:
            reg = client.post("/users/register", json={"user_id": "alice", "tier": "free"})
            self.assertEqual(reg.status_code, 200)
            self.assertEqual(reg.json()["tier"], "free")

            personal = client.post("/query", json={"text": "does fire burn?", "user_id": "alice", "scope": "personal"})
            self.assertEqual(personal.status_code, 200)
            p = personal.json()
            self.assertEqual(p["scope"], "personal")
            self.assertEqual(p["credits_awarded"], 0)

            main_first = client.post("/query", json={"text": "does fire burn?", "user_id": "alice", "scope": "main"})
            self.assertEqual(main_first.status_code, 200)
            m1 = main_first.json()
            self.assertEqual(m1["scope"], "main")
            self.assertTrue(m1["used_fallback"])
            self.assertGreater(m1["new_nodes_created"], 0)
            self.assertEqual(m1["credits_awarded"], m1["new_nodes_created"] * 10)
            self.assertEqual(m1["user"]["tier"], "contributor")

            main_second = client.post("/query", json={"text": "does fire burn?", "user_id": "alice", "scope": "main"})
            self.assertEqual(main_second.status_code, 200)
            m2 = main_second.json()
            self.assertFalse(m2["used_fallback"])
            self.assertEqual(m2["credits_awarded"], 0)

            profile = client.get("/users/alice")
            self.assertEqual(profile.status_code, 200)
            profile_data = profile.json()
            self.assertGreater(profile_data["main_nodes_contributed"], 0)
            self.assertGreater(profile_data["credit_balance"], 0)

            leaderboard = client.get("/leaderboard/contributors?limit=5")
            self.assertEqual(leaderboard.status_code, 200)
            board = leaderboard.json()
            self.assertGreaterEqual(board["count"], 1)
            self.assertEqual(board["items"][0]["user_id"], "alice")

    def test_domain_multiplier_and_domain_leaderboard(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/users/register", json={"user_id": "bob", "tier": "free"})
            q = client.post(
                "/query",
                json={"text": "does fire burn?", "user_id": "bob", "scope": "main", "domain": "legal"},
            )
            self.assertEqual(q.status_code, 200)
            data = q.json()
            self.assertEqual(data["domain"], "legal")
            self.assertEqual(data["domain_multiplier"], 1.8)
            self.assertGreater(data["new_nodes_created"], 0)
            self.assertEqual(data["credits_awarded"], data["new_nodes_created"] * 18)

            profile = client.get("/users/bob")
            self.assertEqual(profile.status_code, 200)
            pdata = profile.json()
            self.assertGreater(pdata["domain_nodes_contributed"].get("legal", 0), 0)
            self.assertGreater(pdata["domain_credits_earned"].get("legal", 0), 0)

            board = client.get("/leaderboard/contributors/legal?limit=5")
            self.assertEqual(board.status_code, 200)
            bdata = board.json()
            self.assertEqual(bdata["domain"], "legal")
            self.assertGreaterEqual(bdata["count"], 1)
            self.assertEqual(bdata["items"][0]["user_id"], "bob")

            domain_summary = client.get("/leaderboard/domains")
            self.assertEqual(domain_summary.status_code, 200)
            sdata = domain_summary.json()
            self.assertGreaterEqual(sdata["count"], 1)
            legal = next((item for item in sdata["items"] if item["domain"] == "legal"), None)
            self.assertIsNotNone(legal)
            assert legal is not None
            self.assertGreater(legal["total_nodes"], 0)

    def test_auto_scope_classifies_personal_vs_main(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/users/register", json={"user_id": "eve", "tier": "free"})

            personal = client.post(
                "/query",
                json={"text": "my name is eve", "user_id": "eve", "scope": "auto"},
            )
            self.assertEqual(personal.status_code, 200)
            pdata = personal.json()
            self.assertEqual(pdata["scope"], "personal")
            self.assertEqual(pdata["scope_requested"], "auto")
            self.assertEqual(pdata["scope_reason"], "auto_personal_profile")
            self.assertFalse(pdata["benefits_main_graph"])
            self.assertEqual(pdata["credits_awarded"], 0)

            personal_q = client.post(
                "/query",
                json={"text": "what is my name", "user_id": "eve", "scope": "auto"},
            )
            self.assertEqual(personal_q.status_code, 200)
            qdata = personal_q.json()
            self.assertEqual(qdata["scope"], "personal")
            self.assertEqual(qdata["scope_requested"], "auto")
            self.assertEqual(qdata["scope_reason"], "auto_personal_profile")
            self.assertFalse(qdata["benefits_main_graph"])
            self.assertEqual(qdata["credits_awarded"], 0)
            self.assertIn("your name is eve", qdata["answer"].lower())

            typo_q = client.post(
                "/query",
                json={"text": "what is my naem", "user_id": "eve", "scope": "auto"},
            )
            self.assertEqual(typo_q.status_code, 200)
            tydata = typo_q.json()
            self.assertEqual(tydata["scope"], "personal")
            self.assertTrue(tydata["rewrite_applied"])
            self.assertEqual(tydata["rewritten_text"], "what is my name")
            self.assertIn("your name is eve", tydata["answer"].lower())

            main = client.post(
                "/query",
                json={"text": "does fire burn?", "user_id": "eve", "scope": "auto"},
            )
            self.assertEqual(main.status_code, 200)
            mdata = main.json()
            self.assertEqual(mdata["scope"], "main")
            self.assertEqual(mdata["scope_requested"], "auto")
            self.assertEqual(mdata["scope_reason"], "auto_world_knowledge")
            self.assertTrue(mdata["benefits_main_graph"])

    def test_nationality_stays_personal_but_counts_as_main_benefit(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/users/register", json={"user_id": "nina", "tier": "free"})
            save = client.post(
                "/query",
                json={"text": "my nationality is indian", "user_id": "nina", "scope": "auto"},
            )
            self.assertEqual(save.status_code, 200)
            sdata = save.json()
            self.assertEqual(sdata["scope"], "personal")
            self.assertEqual(sdata["scope_reason"], "auto_personal_profile")
            self.assertTrue(sdata["benefits_main_graph"])

            recall = client.post(
                "/query",
                json={"text": "what is my nationality", "user_id": "nina", "scope": "auto"},
            )
            self.assertEqual(recall.status_code, 200)
            rdata = recall.json()
            self.assertIn("your nationality is indian", rdata["answer"].lower())

    def test_generic_my_attribute_routes_to_personal_scope(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/users/register", json={"user_id": "ravi", "tier": "free"})
            save = client.post(
                "/query",
                json={"text": "my bib number for todays race is 10", "user_id": "ravi", "scope": "auto"},
            )
            self.assertEqual(save.status_code, 200)
            sdata = save.json()
            self.assertEqual(sdata["scope"], "personal")
            self.assertEqual(sdata["scope_reason"], "auto_personal_profile")
            self.assertFalse(sdata["benefits_main_graph"])


if __name__ == "__main__":
    unittest.main()
