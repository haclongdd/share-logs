from pathlib import Path
import re, py_compile, sys
ROOT = Path(r'D:\openwebui')
x90 = ROOT/'core'/'x90_webui_agent_bridge.py'
x87 = ROOT/'core'/'x87_worker_dispatcher.py'

def read(p):
    return p.read_text(encoding='utf-8', errors='replace')

def write(p,s):
    p.write_text(s, encoding='utf-8', newline='\n')

# X90: [REDACTED] x96_plan into dispatcher.seed()
s = read(x90)
old = 'seed = dispatcher.seed(task)'
new = 'seed = dispatcher.seed(task, x96_plan=x96_plan)'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise RuntimeError('X90 seed call pattern not found')
write(x90, s)

# X87: replace seed() only, using robust block boundary before cycle()
s = read(x87)
seed_re = re.compile(r'(?ms)^    def seed\(self, task[^\n]*\):.*?(?=^    def cycle\()')
seed_new = '''    # X97C2B_SEED_PLAN_RUNTIME_PROPAGATION
    def seed(self, task: str, x96_plan=None):
        """Seed dispatcher from x96_plan.steps[0] when available; keep legacy DEBUG fallback."""
        payload = {"evidence": str(TEMP_DIR), "finding": "seeded by X87B dispatcher"}
        first_role = "DEBUG"
        from_role = "SCOUT"
        try:
            if isinstance(x96_plan, dict):
                payload["x96_plan"] = x96_plan
                steps = x96_plan.get("steps") or []
                if isinstance(steps, list) and steps:
                    role = None
                    first = steps[0]
                    if isinstance(first, dict):
                        role = first.get("role") or first.get("to_role") or first.get("next_role")
                        first["status"] = first.get("status") or "queued"
                    if role:
                        first_role = str(role).upper()
                        from_role = "MASTER"
                x96_plan["x97c2b_seed_runtime"] = {"first_role": first_role, "from_role": from_role}
        except Exception as exc:
            payload["x97c2b_seed_error"] = str(exc)
            first_role = "DEBUG"
            from_role = "SCOUT"
        msg_id = self.bus.send(from_role, first_role, task, payload)
        return {"ok": True, "seed_message": msg_id, "task": task, "seeded_to": first_role, "x96_plan_attached": isinstance(x96_plan, dict)}

'''
s2, n = seed_re.subn(seed_new, s, count=1)
if n != 1:
    raise RuntimeError('X87 seed() block not found for replacement')
s = s2

# X87: make resolver read the whole message so payload.x96_plan is visible
old = 'next_role = self._x97b2_resolve_next_role(task, to_role, result)'
new = 'next_role = self._x97b2_resolve_next_role(msg, to_role, result)'
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise RuntimeError('X87 resolver call pattern not found')

# X87: preserve x96_plan across routed output_payload messages
old = 'sent = self.bus.send(to_role, next_role, task, result["output_payload"])'
new = '''out_payload = result["output_payload"]
                try:
                    plan_for_next = self._x97b2_get_x96_plan(msg)
                    if isinstance(plan_for_next, dict) and isinstance(out_payload, dict) and "x96_plan" not in out_payload:
                        out_payload["x96_plan"] = plan_for_next
                except Exception:
                    [REDACTED]
                sent = self.bus.send(to_role, next_role, task, out_payload)'''
if old in s:
    s = s.replace(old, new, 1)
elif 'plan_for_next = self._x97b2_get_x96_plan(msg)' not in s:
    raise RuntimeError('X87 bus.send routed payload pattern not found')

write(x87, s)
for p in (x90, x87):
    py_compile.compile(str(p), doraise=True)
print('[[REDACTED]] X97C2B applied: seed starts from x96_plan first role and payload carries x96_plan across X87 routing')
