from pathlib import Path
import re
import sys

TARGET = Path(r"D:\openwebui\core\x87_worker_dispatcher.py")
text = TARGET.read_text(encoding="utf-8")

MARK = "X97B2_PLANNER_DRIVEN_RUNTIME_DISPATCH"
if MARK in text:
    print("[INFO] X97B2 already applied; no rewrite needed")
    sys.exit(0)

required = [
    "ROUTE_NEXT",
    "next_role = ROUTE_NEXT.get(to_role)",
    "if result[\"ok\"] and next_role:",
]
missing = [s for s in required if s not in text]
if missing:
    raise SystemExit("[FAIL] Required X87 injection markers missing: " + repr(missing))

class_match = re.search(r"^class\s+\w+.*?:\s*$", text, flags=re.M)
if not class_match:
    raise SystemExit("[FAIL] No class block found in x87_worker_dispatcher.py")

helper = r'''

    # X97B2_PLANNER_DRIVEN_RUNTIME_DISPATCH
    def _x97b2_get_x96_plan(self, task_obj):
        """Return x96_plan dict from common task/message shapes without breaking fallback."""
        if not isinstance(task_obj, dict):
            return None
        direct = task_obj.get("x96_plan")
        if isinstance(direct, dict):
            return direct
        payload = task_obj.get("payload")
        if isinstance(payload, dict):
            nested = payload.get("x96_plan")
            if isinstance(nested, dict):
                return nested
        meta = task_obj.get("metadata")
        if isinstance(meta, dict):
            nested = meta.get("x96_plan")
            if isinstance(nested, dict):
                return nested
        return None

    def _x97b2_extract_role(self, step):
        """Accept role fields used by planner variants."""
        if not isinstance(step, dict):
            return None
        for [REDACTED] in ("role", "to_role", "worker_role", "agent_role", "name"):
            val = step.get([REDACTED])
            if isinstance(val, str) and val.strip():
                return val.strip().upper()
        return None

    def _x97b2_resolve_next_role(self, task_obj, current_role, result):
        """Plan-first next-role resolver; ROUTE_NEXT remains safety fallback."""
        fallback = ROUTE_NEXT.get(current_role)
        try:
            plan = self._x97b2_get_x96_plan(task_obj)
            if not isinstance(plan, dict):
                return fallback
            steps = plan.get("steps")
            if not isinstance(steps, list) or not steps:
                return fallback

            cur = current_role.upper() if isinstance(current_role, str) else current_role
            current_index = None
            for idx, step in enumerate(steps):
                role = self._x97b2_extract_role(step)
                if role == cur:
                    current_index = idx
                    if isinstance(step, dict):
                        step["status"] = "done" if isinstance(result, dict) and result.get("ok") else "failed"
                        step["last_result_ok"] = bool(isinstance(result, dict) and result.get("ok"))
                        step["retries"] = int(step.get("retries") or 0)
                    break

            if current_index is None:
                return fallback

            for next_step in steps[current_index + 1:]:
                next_role = self._x97b2_extract_role(next_step)
                if next_role:
                    if isinstance(next_step, dict) and not next_step.get("status"):
                        next_step["status"] = "queued"
                    plan["x97b2_runtime_dispatch"] = "planner_driven"
                    return next_role

            plan["x97b2_runtime_dispatch"] = "planner_complete"
            return None
        except Exception as exc:
            try:
                if isinstance(task_obj, dict):
                    task_obj.setdefault("x97b2_dispatch_error", str(exc))
            except Exception:
                [REDACTED]
            return fallback
'''

insert_at = class_match.end()
text = text[:insert_at] + helper + text[insert_at:]
text = text.replace("next_role = ROUTE_NEXT.get(to_role)", "next_role = self._x97b2_resolve_next_role(task, to_role, result)", 1)

TARGET.write_text(text, encoding="utf-8", newline="")
print("[[REDACTED]] X97B2 applied: X87 next_role now resolves from x96_plan.steps[] with ROUTE_NEXT fallback")
