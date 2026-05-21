from pathlib import Path
import re
import py_compile
import sys

target = Path(r"D:\openwebui\core\x87_worker_dispatcher.py")
text = target.read_text(encoding="utf-8-sig")
changed = []

# 1) If a broken helper was inserted before the shebang, remove the prefix and keep the real file body.
shebang = "#!/usr/bin/env python3"
idx = text.find(shebang)
if idx > 0:
    text = text[idx:]
    changed.append("trimmed_prefix_before_shebang")

# 2) Undo bad broad replacement that corrupted os.environ.get(...).
patterns = [
    (r"os\._busmsg_get\(environ,", "os.environ.get("),
    (r"os\._busmsg_get\(os\.environ,", "os.environ.get("),
]
for pat, repl in patterns:
    new = re.sub(pat, repl, text)
    if new != text:
        changed.append(f"repaired_{pat}")
        text = new

# 3) Remove existing generated helper definitions so we can reinsert one clean copy after imports.
def remove_function(src: str, name: str) -> tuple[str, bool]:
    m = re.search(rf"\ndef {name}\([^\n]*\):\n", src)
    if not m:
        if src.startswith(f"def {name}("):
            m = re.search(rf"def {name}\([^\n]*\):\n", src)
        else:
            return src, False
    start = m.start() if src[m.start()] == "\n" else m.start()
    # Function ends at next top-level def/class or a clear top-level constant/comment section.
    end_match = re.search(r"\n(?=(def |class |[A-Z][A-Z0-9_]*\s*=|# X|if __name__\s*==))", src[m.end():])
    if end_match:
        end = m.end() + end_match.start()
    else:
        end = len(src)
    return src[:start] + src[end:], True

for fname in ["_busmsg_get", "_x97e7_busmessage_to_dict"]:
    text, did = remove_function(text, fname)
    if did:
        changed.append(f"removed_existing_{fname}")

helper = '''\n\n# X97E7D_BUSMESSAGE_SAFE_ACCESS\ndef _busmsg_get(message, [REDACTED], default=None):\n    """Safe getter for dict payloads and BusMessage/dataclass-like objects."""\n    if isinstance(message, dict):\n        return message.get([REDACTED], default)\n    return getattr(message, [REDACTED], default)\n\ndef _x97e7_busmessage_to_dict(msg):\n    """Normalize x86 BusMessage/dataclass objects to dict before dispatcher access."""\n    if isinstance(msg, dict):\n        return msg\n    if hasattr(msg, "__dict__"):\n        return dict(vars(msg))\n    return msg\n'''

# 4) Insert helper after the import block. This preserves shebang, module docstring, and from __future__ placement.
lines = text.splitlines(True)
insert_at = None
last_import = None
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("import ") or stripped.startswith("from "):
        last_import = i
    elif last_import is not None and stripped and not stripped.startswith("#"):
        insert_at = last_import + 1
        break
if insert_at is None:
    insert_at = (last_import + 1) if last_import is not None else 0
lines.insert(insert_at, helper)
text = "".join(lines)
changed.append("inserted_clean_helpers_after_imports")

# 5) Ensure handle_message normalizes msg once at the top.
if "msg = _x97e7_busmessage_to_dict(msg)" not in text:
    text = re.sub(
        r"(def handle_message\(self, msg:[^\n]*\) -> Dict\[str, Any\]:\n)",
        r"\1        # X97E7D: normalize BusMessage/dataclass before safe getter access.\n        msg = _x97e7_busmessage_to_dict(msg)\n",
        text,
        count=1,
    )
    changed.append("inserted_handle_message_normalization")

# 6) Repair known bad state references and method-helper references.
repls = {
    "self._busmsg_get(": "_busmsg_get(",
    "_busmsg_get(state, \"cycles\", 0)": "_busmsg_get(self.state, \"cycles\", 0)",
    "_busmsg_get(state, \"processed_total\", 0)": "_busmsg_get(self.state, \"processed_total\", 0)",
}
for old, new in repls.items():
    if old in text:
        text = text.replace(old, new)
        changed.append(f"replaced_{old}")

# 7) Convert remaining obvious msg.get calls in x87 only to safe getter without touching os.environ.get.
text2 = re.sub(r"\bmsg\.get\(", "_busmsg_get(msg, ", text)
if text2 != text:
    text = text2
    changed.append("converted_msg_dot_get")

# 8) Write then compile before success.
target.write_text(text, encoding="utf-8")
try:
    py_compile.compile(str(target), doraise=True)
except Exception as exc:
    print("COMPILE_FAIL", repr(exc))
    raise
print("OK")
for c in changed:
    print(c)
