from pathlib import Path
import re

ROOT = Path(r"D:\openwebui")
MARK = "X97C2_PLAN_SEED_RUNTIME_PROPAGATION"

def read(p):
    return p.read_text(encoding="utf-8", errors="replace")

def write(p, s):
    p.write_text(s, encoding="utf-8", newline="\n")

def patch_x90():
    p = ROOT / "core" / "x90_webui_agent_bridge.py"
    s = read(p)
    if "dispatcher.seed(task, x96_plan=x96_plan)" not in s:
        old = "seed = dispatcher.seed(task)"
        if old not in s:
            raise RuntimeError("x90 seed call not found")
        s = s.replace(old, "seed = dispatcher.seed(task, x96_plan=x96_plan)  # " + MARK, 1)
    write(p, s)

def patch_x86():
    p = ROOT / "core" / "x86_agent_bus.py"
    s = read(p)
    old = '"SCOUT": ["DEBUG", "REPORT"],'
    new = '"SCOUT": ["SCOUT", "DEBUG", "REPORT"],  # X97C2 allows planner seed into SCOUT'
    if new not in s:
        if old not in s:
            if '"SCOUT": ["SCOUT", "DEBUG", "REPORT"]' not in s:
                raise RuntimeError("x86 SCOUT transition line not found")
        else:
            s = s.replace(old, new, 1)
    write(p, s)

def patch_x87():
    p = ROOT / "core" / "x87_worker_dispatcher.py"
    s = read(p)

    if 'roles or ["SCOUT", "DEBUG", "PATCHER", "VERIFY", "REPORT"]' not in s:
        s = s.replace(
            'roles or ["DEBUG", "PATCHER", "VERIFY", "REPORT"]',
            'roles or ["SCOUT", "DEBUG", "PATCHER", "VERIFY", "REPORT"]',
            1
        )

    if 'if to_role == "SCOUT":' not in s and 'elif to_role == "SCOUT":' not in s:
        marker = '        if to_role == "DEBUG":\n'
        scout = """        if to_role == "SCOUT":\n            result["summary"] = "SCOUT worker consumed planner seed and prepared context for DEBUG."\n            result["output_payload"] = {\n                "evidence": payload.get("evidence") or r"D:\\openwebui\\runtime\\temp",\n                "finding": payload.get("finding") or "seeded by X97C2 planner runtime propagation",\n                "source_message": msg.get("id"),\n            }\n        elif to_role == "DEBUG":\n"""
        if marker not in s:
            raise RuntimeError("x87 DEBUG handler marker not found")
        s = s.replace(marker, scout, 1)

    preserve = """\n        # X97C2_PLAN_SEED_RUNTIME_PROPAGATION: preserve planner payload across worker hops.\n        if isinstance(payload.get("x96_plan"), dict) and isinstance(result.get("output_payload"), dict):\n            result["output_payload"].setdefault("x96_plan", payload.get("x96_plan"))\n\n"""
    if "preserve planner payload across worker hops" not in s:
        old = '        next_role = self._x97b2_resolve_next_role(task, to_role, result)\n'
        new = preserve + '        task_context = {"task": task, "payload": payload}\n        next_role = self._x97b2_resolve_next_role(task_context, to_role, result)\n'
        if old not in s:
            raise RuntimeError("x87 next_role resolver call not found")
        s = s.replace(old, new, 1)

    seed_re = re.compile(r'    def seed\(self, task: str\) -> Dict\[str, Any\]:\n.*?\n(?=    def demo\(self, task: str\) -> Dict\[str, Any\]:)', re.S)
    seed_new = """    def seed(self, task: str, x96_plan=None) -> Dict[str, Any]:\n        \"\"\"X97C2_PLAN_SEED_RUNTIME_PROPAGATION: seed planner first role when x96_plan exists; fallback to legacy DEBUG seed.\"\"\"\n        payload = {\n            "finding": "seeded by X97C2 planner runtime propagation",\n            "evidence": r"D:\\openwebui\\runtime\\temp",\n        }\n        seed_from = "SCOUT"\n        seed_to = "DEBUG"\n        first_role = None\n        try:\n            if isinstance(x96_plan, dict):\n                payload["x96_plan"] = x96_plan\n                steps = x96_plan.get("steps")\n                if isinstance(steps, list) and steps:\n                    first_role = self._x97b2_extract_role(steps[0])\n                    if first_role:\n                        seed_to = first_role\n                        seed_from = first_role\n        except Exception as exc:\n            payload["x97c2_seed_plan_error"] = str(exc)\n            seed_from = "SCOUT"\n            seed_to = "DEBUG"\n\n        msg = self.bus.send(seed_from, seed_to, task, payload)\n        return {\n            "ok": True,\n            "seed_message": msg.id,\n            "task": task,\n            "x97c2_seed_from": seed_from,\n            "x97c2_seed_to": seed_to,\n            "x97c2_first_plan_role": first_role,\n            "x96_plan_attached": isinstance(x96_plan, dict),\n        }\n\n"""
    if "def seed(self, task: str, x96_plan=None)" not in s:
        s2, n = seed_re.subn(seed_new, s, count=1)
        if n != 1:
            raise RuntimeError("x87 seed method block not found")
        s = s2

    write(p, s)

patch_x90()
patch_x86()
patch_x87()
print("[[REDACTED]] X97C2 applied: X90 [REDACTED]es x96_plan to X87 seed; X87 seeds planner first role; X86 allows SCOUT self-seed; X87 consumes SCOUT and preserves x96_plan.")
