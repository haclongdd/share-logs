from pathlib import Path
import re

path = Path(r"D:\openwebui\core\x87_worker_dispatcher.py")
text = path.read_text(encoding="utf-8")

if "X97D_PLANNER_AWARE_SEED_BUS_PROPAGATION" in text:
    print("[[REDACTED]] X97D already present")
    raise SystemExit(0)

idx = text.find("class WorkerDispatcher:")
if idx < 0:
    raise RuntimeError("WorkerDispatcher class not found")
insert_pos = text.find("\n", idx) + 1

helpers = """
    # X97D_PLANNER_AWARE_SEED_BUS_PROPAGATION
    def _x97d_plan_steps(self, x96_plan):
        if not isinstance(x96_plan, dict):
            return []
        steps = x96_plan.get("steps")
        return steps if isinstance(steps, list) else []

    def _x97d_step_role(self, step):
        if not isinstance(step, dict):
            return None
        role = step.get("role") or step.get("to_role") or step.get("worker_role") or step.get("agent_role")
        if role is None:
            return None
        role = str(role).strip().upper()
        return role or None

    def _x97d_first_role(self, x96_plan):
        for step in self._x97d_plan_steps(x96_plan):
            role = self._x97d_step_role(step)
            if role:
                return role
        return None

    def _x97d_seed_payload(self, x96_plan=None):
        payload = {"evidence": str(TEMP_DIR), "finding": "seeded by X87D planner-aware dispatcher"}
        if isinstance(x96_plan, dict):
            payload["x96_plan"] = x96_plan
            payload["x97d_plan_seed"] = {
                "first_role": self._x97d_first_role(x96_plan),
                "steps_count": len(self._x97d_plan_steps(x96_plan)),
            }
        return payload

"""
text = text[:insert_pos] + helpers + text[insert_pos:]

text2 = re.sub(
    r'def\s+seed\s*\(\s*self\s*,\s*task\s*:\s*str\s*\)\s*:',
    'def seed(self, task: str, x96_plan=None):',
    text,
    count=1,
)
if text2 == text:
    text2 = re.sub(
        r'def\s+seed\s*\(\s*self\s*,\s*task\s*\)\s*:',
        'def seed(self, task, x96_plan=None):',
        text,
        count=1,
    )
text = text2
if "def seed(self, task" not in text or "x96_plan=None" not in text:
    raise RuntimeError("Failed to update seed signature")

m = re.search(r'(?ms)^    def seed\(self, task[^\n]*\):\n(?P<body>.*?)(?=^    def |\Z)', text)
if not m:
    raise RuntimeError("seed function block not found")
body = m.group("body")
orig_body = body

body = re.sub(
    r'payload\s*=\s*\{[^{}]*"finding"\s*:\s*"seeded by X87B dispatcher"[^{}]*\}',
    'payload = self._x97d_seed_payload(x96_plan)',
    body,
    count=1,
    flags=re.S,
)
body = re.sub(
    r'payload\s*=\s*\{[^{}]*"finding"\s*:\s*"seeded by X87 dispatcher"[^{}]*\}',
    'payload = self._x97d_seed_payload(x96_plan)',
    body,
    count=1,
    flags=re.S,
)

if "self._x97d_seed_payload(x96_plan)" not in body:
    body = re.sub(r'(\n)', r'\1        payload = self._x97d_seed_payload(x96_plan)\n', body, count=1)

body = body.replace('self.bus.send("SCOUT", "DEBUG", task, payload)', 'self.bus.send("MASTER", seed_role, task, payload)')
body = body.replace("self.bus.send('SCOUT', 'DEBUG', task, payload)", "self.bus.send('MASTER', seed_role, task, payload)")
body = body.replace('self.bus.send("MASTER", "DEBUG", task, payload)', 'self.bus.send("MASTER", seed_role, task, payload)')
body = body.replace("self.bus.send('MASTER', 'DEBUG', task, payload)", "self.bus.send('MASTER', seed_role, task, payload)")

body = re.sub(r'from_role\s*=\s*["\']SCOUT["\']', 'from_role = "MASTER"', body)
body = re.sub(r'to_role\s*=\s*["\']DEBUG["\']', 'to_role = seed_role', body)

if "seed_role = self._x97d_first_role(x96_plan) or" not in body:
    body = re.sub(r'(\n)', r'\1        seed_role = self._x97d_first_role(x96_plan) or "DEBUG"\n', body, count=1)

if orig_body == body:
    raise RuntimeError("seed block unchanged; refusing blind patch")

text = text[:m.start("body")] + body + text[m.end("body"):]

if "X97D_PLANNER_AWARE_SEED_BUS_PROPAGATION_APPLIED" not in text:
    text += '\n# X97D_PLANNER_AWARE_SEED_BUS_PROPAGATION_APPLIED\n'

path.write_text(text, encoding="utf-8")
print("[[REDACTED]] X97D applied: seed accepts x96_plan, starts at plan first role, and attaches plan to seed payload")
