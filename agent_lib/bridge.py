"""
AgentBridge Python Client
High-speed HTTP client interface to the AgentBridge SMAPI mod running on 127.0.0.1:8765.
"""

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class BridgeClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8765", log_file: str = "logs/plans.jsonl"):
        self.base_url = base_url.rstrip("/")
        self.log_file = log_file
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _get(self, endpoint: str, timeout: int = 10) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers={"User-Agent": "AgentBridge-Python/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AgentBridge-Python/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_state(self) -> Dict[str, Any]:
        """Returns the live cached snapshot of game state (~10 Hz)."""
        return self._get("/state")

    def get_map(self) -> Dict[str, Any]:
        """Returns current location map: width, height, walkable ASCII rows, and warps."""
        return self._get("/map")

    def get_farm(self) -> List[Dict[str, Any]]:
        """Returns list of tilled tiles + crops in the current location."""
        return self._get("/farm")

    def load_save(self, save_name: str = "LauS_426336281") -> Dict[str, Any]:
        """Programmatically loads a save file from the title screen."""
        return self._post("/load", {"save": save_name})

    def run_plan(self, plan_id: str, steps: List[Dict[str, Any]], interrupt: bool = False) -> Dict[str, Any]:
        """Submits a multi-step plan to the game engine for loop execution."""
        payload = {"id": plan_id, "steps": steps, "interrupt": interrupt}
        return self._post("/run", payload)

    def wait(self, plan_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Long-polls until the plan finishes, fails, or times out."""
        endpoint = f"/wait?id={urllib.parse.quote(plan_id)}&timeout={timeout}"
        res = self._get(endpoint, timeout=timeout + 5)
        self._log_plan_result(plan_id, res)
        return res

    def cancel(self) -> Dict[str, Any]:
        """Cancels the currently executing plan."""
        return self._post("/cancel", {})

    def execute(self, plan_id: str, steps: List[Dict[str, Any]], timeout: int = 60, interrupt: bool = False) -> Dict[str, Any]:
        """Helper to run a plan and wait for its completion."""
        self.run_plan(plan_id, steps, interrupt=interrupt)
        return self.wait(plan_id, timeout=timeout)

    def _log_plan_result(self, plan_id: str, result: Dict[str, Any]):
        """Logs plan execution metadata to logs/plans.jsonl."""
        entry = {
            "timestamp": time.time(),
            "id": plan_id,
            "status": result.get("status"),
            "step": result.get("step"),
            "steps_total": result.get("stepsTotal") or result.get("steps_total"),
            "error": result.get("error"),
            "elapsed_s": result.get("elapsedS") or result.get("elapsed_s"),
            "detail": result.get("detail", ""),
        }
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
