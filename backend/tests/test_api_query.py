from __future__ import annotations
from typing import Any

import os
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.server import app

TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class QueryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case_dir = TEST_TMP_ROOT / f"api_{uuid.uuid4().hex}"
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

    def test_query_endpoint_learns_and_history_is_stored(self) -> None:
        with TestClient(app) as client:
            first = client.post("/query", json={"text": "does steam burn?"})
            self.assertEqual(first.status_code, 200)
            first_data = first.json()
            self.assertIn("llm_backend", first_data)
            self.assertIn("llm_used", first_data)
            self.assertIn("llm_mode", first_data)
            self.assertIn("llm_policy", first_data)
            self.assertIn("query_mode", first_data)
            self.assertTrue(first_data["used_fallback"])
            self.assertGreaterEqual(first_data["created_edges"], 1)
            self.assertIn("history_record_id", first_data)

            second = client.post("/query", json={"text": "does steam burn?"})
            self.assertEqual(second.status_code, 200)
            second_data = second.json()
            self.assertFalse(second_data["used_fallback"], msg=f"Full data: {second_data}")

            history = client.get("/query/history", params={"limit": 5})
            self.assertEqual(history.status_code, 200)
            history_data = history.json()
            self.assertGreaterEqual(history_data["count"], 2)
            self.assertIn("id", history_data["items"][0])
            self.assertIn("frozen_snapshot", history_data["items"][0])
            self.assertIn("intent", history_data["items"][0])
            self.assertIn("new_nodes_created", history_data["items"][0])

    def test_query_endpoint_supports_describe_concept_prompt(self) -> None:
        with TestClient(app) as client:
            _ = client.post(
                "/edges",
                json={"source": "photosynthesis", "target": "plants", "type": "CORRELATES", "strength": 0.82},
            )
            resp = client.post("/query", json={"text": "describe photosynthesis", "user_id": "alice", "scope": "main"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("plants", data["answer"].lower())
            self.assertEqual(data["scope"], "main")
            self.assertFalse(data["used_fallback"])
            self.assertIn("intent:concept", data["steps"])

    def test_query_endpoint_handles_generic_personal_fact(self) -> None:
        with TestClient(app) as client:
            save = client.post(
                "/query",
                json={"text": "my bib number for todays race is 10", "user_id": "alice", "scope": "auto"},
            )
            self.assertEqual(save.status_code, 200)
            sdata = save.json()
            self.assertEqual(sdata["scope"], "personal")
            self.assertIn("remember your bib number for todays race", sdata["answer"].lower())
            self.assertEqual(sdata["rewritten_text"], "my bib number for todays race is 10")
            self.assertFalse(sdata["rewrite_applied"])

            read = client.post(
                "/query",
                json={"text": "what is my bib number for todays race", "user_id": "alice", "scope": "auto"},
            )
            self.assertEqual(read.status_code, 200)
            rdata = read.json()
            self.assertEqual(rdata["scope"], "personal")
            self.assertIn("your bib number for todays race is 10", rdata["answer"].lower())

    def test_llm_mode_stays_skip_when_llm_backend_disabled(self) -> None:
        with TestClient(app) as client:
            resp = client.post("/query", json={"text": "tell me something interesting", "user_id": "alice", "scope": "main"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["llm_backend"], "none")
            self.assertEqual(data["llm_mode"], "skip")
            self.assertFalse(data["llm_used"])
            self.assertIsNone(data["llm_error"])

    def test_unknown_troubleshooting_query_uses_local_fallback_answer(self) -> None:
        with TestClient(app) as client:
            resp = client.post(
                "/query",
                json={"text": "i have an hydration error on js how to solve it", "user_id": "alice", "scope": "auto"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["scope"], "main")
            self.assertEqual(data["query_mode"], "standard")
            self.assertEqual(data["llm_mode"], "web")
            self.assertEqual(data["llm_backend"], "web")
            self.assertEqual(data["llm_model"], "troubleshooting_nextjs_hydration")
            self.assertIn("hydration error usually means", data["answer"].lower())

    def test_ui_and_expansion_endpoints(self) -> None:
        with TestClient(app) as client:
            ui = client.get("/")
            self.assertEqual(ui.status_code, 200)
            ui_data = ui.json()
            self.assertTrue(ui_data["ok"])
            self.assertIn("localhost:3000", ui_data["ui"])

            llm = client.get("/llm/status")
            self.assertEqual(llm.status_code, 200)
            ldata = llm.json()
            self.assertIn("backend", ldata)
            self.assertIn("enabled", ldata)

            _ = client.post("/query", json={"text": "does quartz melt?"})
            exp = client.get("/expansion/nodes", params={"limit": 5})
            self.assertEqual(exp.status_code, 200)
            exp_data = exp.json()
            self.assertGreaterEqual(exp_data["count"], 1)
            self.assertIn("status", exp_data["items"][0])

            resolved = client.post("/expansion/resolve", params={"max_items": 2})
            self.assertEqual(resolved.status_code, 200)
            self.assertIn("resolved", resolved.json())

            domains = client.get("/domains")
            self.assertEqual(domains.status_code, 200)
            d = domains.json()
            self.assertGreaterEqual(d["count"], 1)
            self.assertIn("credit_multiplier", d["domains"][0])

    def test_hub_and_analogy_endpoints(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/edges", json={"source": "fire", "target": "heat", "type": "CAUSES", "strength": 0.9})
            _ = client.post("/edges", json={"source": "steam", "target": "heat", "type": "IS_A", "strength": 0.8})
            _ = client.post("/edges", json={"source": "heat", "target": "burn", "type": "CAUSES", "strength": 0.9})
            _ = client.post("/edges", json={"source": "sun", "target": "heat", "type": "CAUSES", "strength": 0.7})

            hubs = client.get("/graph/hubs", params={"limit": 5, "min_total_degree": 2})
            self.assertEqual(hubs.status_code, 200)
            h = hubs.json()
            self.assertGreaterEqual(h["count"], 1)
            self.assertIn("label", h["items"][0])
            self.assertIn("hub_score", h["items"][0])

            _ = client.post("/edges", json={"source": "bird", "target": "fly", "type": "CAUSES", "strength": 0.8})
            _ = client.post("/edges", json={"source": "bird", "target": "wing", "type": "IS_A", "strength": 0.7})
            _ = client.post("/edges", json={"source": "plane", "target": "fly", "type": "CAUSES", "strength": 0.8})
            _ = client.post("/edges", json={"source": "plane", "target": "wing", "type": "IS_A", "strength": 0.7})

            analogies = client.get("/reasoning/analogies/bird", params={"limit": 5, "min_shared_neighbors": 2})
            self.assertEqual(analogies.status_code, 200)
            a = analogies.json()
            self.assertGreaterEqual(a["count"], 1)
            self.assertIn("candidate", a["items"][0])
            self.assertIn("shared_neighbors", a["items"][0])

            summary = client.get("/graph/summary", params={"scope": "main", "user_id": "alice", "node_limit": 20, "edge_limit": 30})
            self.assertEqual(summary.status_code, 200)
            s = summary.json()
            self.assertEqual(s["scope"], "main")
            self.assertIn("stats", s)
            self.assertIn("nodes", s)
            self.assertIn("edges", s)
            if s["nodes"]:
                self.assertIn("description", s["nodes"][0])
            if s["edges"]:
                self.assertIn("description", s["edges"][0])
                self.assertIn("relation_text", s["edges"][0])

    def test_history_evolution_endpoint_replays_without_storing(self) -> None:
        with TestClient(app) as client:
            first = client.post("/query", json={"text": "does steam burn?", "user_id": "alice", "scope": "main"})
            self.assertEqual(first.status_code, 200)
            first_data = first.json()
            record_id = first_data["history_record_id"]

            before = client.get("/query/history", params={"limit": 50}).json()["count"]
            evolution = client.get(f"/query/history/{record_id}/evolution")
            self.assertEqual(evolution.status_code, 200)
            evo_data = evolution.json()

            self.assertEqual(evo_data["record_id"], record_id)
            self.assertEqual(evo_data["scope"], "main")
            self.assertEqual(evo_data["user_id"], "alice")
            self.assertIn("updated_answer", evo_data)
            self.assertIn("steps_now", evo_data)

            after = client.get("/query/history", params={"limit": 50}).json()["count"]
            self.assertEqual(before, after)

    def test_encoder_training_endpoints(self) -> None:
        with TestClient(app) as client:
            q = client.post("/query", json={"text": "does fire burn?", "user_id": "alice", "scope": "auto"})
            self.assertEqual(q.status_code, 200)
            self.assertIn("decoder_backend", q.json())

            recent = client.get("/encoder/training/recent", params={"limit": 5})
            self.assertEqual(recent.status_code, 200)
            rdata = recent.json()
            self.assertGreaterEqual(rdata["count"], 1)
            self.assertIn("raw_text", rdata["items"][0])
            self.assertIn("answer", rdata["items"][0])
            self.assertIn("backend", rdata["items"][0])

            train = client.post(
                "/encoder/train",
                json={"max_records": 500, "min_confidence": 0.0, "min_token_occurrences": 1},
            )
            self.assertEqual(train.status_code, 200)
            tdata = train.json()
            self.assertTrue(tdata["ok"])
            self.assertIn("summary", tdata)

    def test_decoder_training_endpoint(self) -> None:
        with TestClient(app) as client:
            q = client.post("/query", json={"text": "does steam burn?", "user_id": "alice", "scope": "auto"})
            self.assertEqual(q.status_code, 200)

            train = client.post(
                "/decoder/train",
                json={"max_records": 500, "min_confidence": 0.0, "min_samples": 1},
            )
            self.assertEqual(train.status_code, 200)
            data = train.json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["decoder_backend"], "own")
            self.assertIn("summary", data)

    def test_realtime_mode_disables_graph_learning(self) -> None:
        with TestClient(app) as client:
            q = client.post("/query", json={"text": "who is narendra modi?", "user_id": "alice", "scope": "auto"})
            self.assertEqual(q.status_code, 200)
            data = q.json()
            self.assertEqual(data["query_mode"], "realtime")
            self.assertFalse(data["benefits_main_graph"])
            self.assertEqual(data["new_nodes_created"], 0)
            self.assertEqual(data["created_edges"], 0)
            self.assertEqual(data["credits_awarded"], 0)

    def test_realtime_mode_uses_web_lookup_even_when_llm_disabled(self) -> None:
        with patch("api.server.fetch_realtime_answer", return_value=("Narendra Modi is Prime Minister of India.", "wikipedia_summary")):
            with TestClient(app) as client:
                q = client.post("/query", json={"text": "who is narendra modi?", "user_id": "alice", "scope": "auto"})
                self.assertEqual(q.status_code, 200)
                data = q.json()
                self.assertEqual(data["query_mode"], "realtime")
                self.assertEqual(data["llm_mode"], "web")
                self.assertEqual(data["llm_backend"], "web")
                self.assertEqual(data["llm_model"], "wikipedia_summary")
                self.assertIn("narendra modi", data["answer"].lower())

    def test_user_impact_endpoint(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/query", json={"text": "my name is alice", "user_id": "alice", "scope": "auto"})
            _ = client.post("/query", json={"text": "does fire burn?", "user_id": "alice", "scope": "auto"})

            impact = client.get("/users/alice/impact", params={"limit": 10})
            self.assertEqual(impact.status_code, 200)
            data = impact.json()
            self.assertEqual(data["user_id"], "alice")
            self.assertIn("summary", data)
            self.assertIn("personal_memory", data)
            self.assertIn("main_graph_impact", data)

    def test_query_history_by_user_endpoint(self) -> None:
        with TestClient(app) as client:
            _ = client.post("/query", json={"text": "my name is alice", "user_id": "alice", "scope": "auto"})
            _ = client.post("/query", json={"text": "does fire burn?", "user_id": "alice", "scope": "auto"})
            _ = client.post("/query", json={"text": "does steam burn?", "user_id": "bob", "scope": "auto"})

            alice = client.get("/query/history/user/alice", params={"limit": 20})
            self.assertEqual(alice.status_code, 200)
            adata = alice.json()
            self.assertEqual(adata["user_id"], "alice")
            self.assertGreaterEqual(adata["count"], 2)
            self.assertTrue(all(item["user_id"] == "alice" for item in adata["items"]))

            alice_personal = client.get("/query/history/user/alice", params={"limit": 20, "scope": "personal"})
            self.assertEqual(alice_personal.status_code, 200)
            pdata = alice_personal.json()
            self.assertEqual(pdata["scope"], "personal")
            self.assertTrue(all(item["scope"] == "personal" for item in pdata["items"]))

    def test_auth_register_login_session_logout(self) -> None:
        with TestClient(app) as client:
            reg = client.post("/auth/register", json={"user_id": "auth_alice", "password": "pass1234"})
            self.assertEqual(reg.status_code, 200)
            rdata = reg.json()
            self.assertEqual(rdata["user_id"], "auth_alice")
            self.assertIn("token", rdata)

            login = client.post("/auth/login", json={"user_id": "auth_alice", "password": "pass1234"})
            self.assertEqual(login.status_code, 200)
            ldata = login.json()
            token = ldata["token"]

            session = client.get("/auth/session", params={"token": token})
            self.assertEqual(session.status_code, 200)
            sdata = session.json()
            self.assertEqual(sdata["user_id"], "auth_alice")

            bad_login = client.post("/auth/login", json={"user_id": "auth_alice", "password": "badpass"})
            self.assertEqual(bad_login.status_code, 401)

            logout = client.post("/auth/logout", json={"token": token})
            self.assertEqual(logout.status_code, 200)
            self.assertTrue(logout.json()["ok"])

    def test_crawl_endpoint_contributor_only(self) -> None:
        with TestClient(app) as client:
            # Register a contributor
            reg = client.post("/auth/register", json={"user_id": "contributor_user", "password": "pass", "tier": "contributor"})
            token = reg.json()["token"]

            # Register a free user
            reg_free = client.post("/auth/register", json={"user_id": "free_user", "password": "pass", "tier": "free"})
            token_free = reg_free.json()["token"]

            # Test contributor access
            resp = client.post("/crawl", json={"url": "test query"}, headers={"token": token})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["ok"])

            # Test free user denied
            resp_free = client.post("/crawl", json={"url": "test query"}, headers={"token": token_free})
            self.assertEqual(resp_free.status_code, 403)

            # Test status
            status = client.get("/crawl/status")
            self.assertEqual(status.status_code, 200)
            self.assertIn("queue_size", status.json())
            self.assertIn("pages_crawled", status.json())

if __name__ == "__main__":
    unittest.main()
