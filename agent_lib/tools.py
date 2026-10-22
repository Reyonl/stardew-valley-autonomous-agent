"""
LLM Planner Tools
Clean interface exposed to runtime planners. No per-key simulations.
"""

from typing import Any, Dict, List, Optional
from .bridge import BridgeClient

_client = BridgeClient()


def get_live_state() -> Dict[str, Any]:
    """
    Fetches the live ground-truth game state (coordinates, time, energy, inventory, etc.).
    STATE IS TRUTH.
    """
    return _client.get_state()


def get_farm_crops() -> List[Dict[str, Any]]:
    """
    Fetches the tilled soil tiles and crops in the current location.
    Returns: list of dicts with keys: x, y, wet, crop, phase, ready, dead.
    """
    return _client.get_farm()


def get_location_map() -> Dict[str, Any]:
    """
    Fetches the location geometry, walkable tile grid (strings of '.' and '#'), and warps.
    """
    return _client.get_map()


def run_plan(plan_id: str, steps: List[Dict[str, Any]], timeout: int = 60, interrupt: bool = False) -> Dict[str, Any]:
    """
    Submits a batch of skill steps for in-engine execution and long-polls until completion.
    Logs execution to logs/plans.jsonl.
    """
    return _client.execute(plan_id=plan_id, steps=steps, timeout=timeout, interrupt=interrupt)


def cancel_plan() -> Dict[str, Any]:
    """Cancels any currently running plan."""
    return _client.cancel()
