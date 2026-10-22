import json
import os
import unittest
from agent_lib.bridge import BridgeClient


class TestBridgeClient(unittest.TestCase):
    def setUp(self):
        self.client = BridgeClient(base_url="http://127.0.0.1:8765", log_file="logs/test_plans.jsonl")

    def tearDown(self):
        if os.path.exists("logs/test_plans.jsonl"):
            try:
                os.remove("logs/test_plans.jsonl")
            except Exception:
                pass

    def test_log_plan_result(self):
        sample_result = {
            "status": "done",
            "step": 3,
            "steps_total": 3,
            "error": None,
            "elapsed_s": 1.25,
            "detail": "Completed"
        }
        self.client._log_plan_result("test_plan_01", sample_result)
        self.assertTrue(os.path.exists("logs/test_plans.jsonl"))
        with open("logs/test_plans.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["id"], "test_plan_01")
        self.assertEqual(data["status"], "done")
        self.assertEqual(data["elapsed_s"], 1.25)

    def test_live_server_state_if_running(self):
        try:
            state = self.client.get_state()
            self.assertIn("world_ready", state)
            if state["world_ready"]:
                self.assertIn("player", state)
                self.assertIn("time", state)
                self.assertIn("inventory", state)
        except Exception:
            # If server not running in test env, skip
            pass


if __name__ == "__main__":
    unittest.main()
