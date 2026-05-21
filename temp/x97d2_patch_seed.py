from pathlib import Path
import re

ROOT = Path(r"D:\openwebui")
x90 = ROOT / "core" / "x90_webui_agent_bridge.py"
x87 = ROOT / "core" / "x87_worker_dispatcher.py"

def read(p):
    return p.read_text(encoding="utf-8")

def write(p, s):
    p.write_text(s, encoding="utf-8", newline="\n")

t = read(x90)
if "dispatcher.seed(task, x96_plan=x96_plan)" not in t:
    t2 = t.replace("dispatcher.seed(task)", "dispatcher.seed(task, x96_plan=x96_plan)")
    if t2 == t:
        raise RuntimeError("X90 seed call pattern not found")
    t = t2
    print("[PATCH] X90 dispatcher.seed now receives x96_plan")
else:
    print("[OK] X90 dispatcher.seed already receives x96_plan")
if "X97D2_PLANNER_SEED_HOTFIX_X90" not in t:
    t += "\n# X97D2_PLANNER_SEED_HOTFIX_X90\n"
write(x90, t)

t = read(x87)
if "class WorkerDispatcher:" not in t:
    raise RuntimeError("WorkerDispatcher class not found")

seed_re = re.compile(r'(?ms)^    def seed\(self, task[^\n]*\):\n.*?(?=^    def |^def |\Z)')
new_seed = '''    # X97D2_PLANNER_SEED_HOTFIX
    def seed(self, task: str, x96_plan=None) -> Dict[str, Any]:
        """Seed first worker from x96_plan.steps[0].role; fallback remains DEBUG."""
        seed_role = "DEBUG"
        steps_count = 0
        if isinstance(x96_plan, dict):
            steps = x96_plan.get("steps")
            if isinstance(steps, list):
                steps_count = len(steps)
                for step in steps:
                    role = self._x97b2_extract_role(step) if hasattr(self, "_x97b2_extract_role") else None
                    if role:
                        seed_role = role
                        if isinstance(step, dict) and not step.get("status"):
                            step["status"] = "queued"
                        break

        payload = {
            "finding": "seeded by X97D2 planner-aware dispatcher",
            "evidence": str(TEMP_DIR),
            "x97d2_seed_role": seed_role,
        }
        if isinstance(x96_plan, dict):
            payload["x96_plan"] = x96_plan
            payload["x97d2_plan_seed"] = {
                "first_role": seed_role,
                "steps_count": steps_count,
                "source": "x96_plan.steps[0].role",
            }

        msg = self.bus.send("MASTER", seed_role, task, payload)
        return {
            "ok": True,
            "seed_message": msg.id,
            "task": task,
            "seed_role": seed_role,
            "x96_plan_attached": isinstance(x96_plan, dict),
        }

'''

m = seed_re.search(t)
if not m:
    raise RuntimeError("X87 seed function block not found")
t = t[:m.start()] + new_seed + t[m.end():]
print("[PATCH] X87 seed replaced with planner-aware seed")

t2 = t.replace('roles = [r.upper() for r in (roles or ["DEBUG", "PATCHER", "VERIFY", "REPORT"])]',
               'roles = [r.upper() for r in (roles or ["SCOUT", "DEBUG", "PATCHER", "VERIFY", "REPORT"])]')
t2 = t2.replace("roles = [r.upper() for r in (roles or ['DEBUG', 'PATCHER', 'VERIFY', 'REPORT'])]",
                "roles = [r.upper() for r in (roles or ['SCOUT', 'DEBUG', 'PATCHER', 'VERIFY', 'REPORT'])]")
if t2 == t and '["SCOUT", "DEBUG", "PATCHER", "VERIFY", "REPORT"]' not in t:
    raise RuntimeError("X87 cycle default roles pattern not found")
t = t2

t = t.replace('p_cycle.add_argument("--roles", default="DEBUG,PATCHER,VERIFY,REPORT")',
              'p_cycle.add_argument("--roles", default="SCOUT,DEBUG,PATCHER,VERIFY,REPORT")')

if "X97D2_PLANNER_SEED_HOTFIX_APPLIED" not in t:
    t += "\n# X97D2_PLANNER_SEED_HOTFIX_APPLIED\n"
write(x87, t)
print("[[REDACTED]] X97D2 applied: x90 [REDACTED]es plan; x87 seeds first plan role and carries x96_plan in payload")
