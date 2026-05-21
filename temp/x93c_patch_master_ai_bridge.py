from pathlib import Path
import re
p=Path(r"D:\openwebui\core\master_ai_bridge.py")
s=p.read_text(encoding="utf-8")
marker="X93C_FORCE_WEBUI_RESPONSE_NORMALIZER_FIX"
helper = "\n\n# X93C_FORCE_WEBUI_RESPONSE_NORMALIZER_FIX_START\n"
helper += "def _x93c_pick_first_text(*values):\n"
helper += "    for v in values:\n"
helper += "        if v is None: continue\n"
helper += "        if isinstance(v, str) and v.strip(): return v.strip()\n"
helper += "        if isinstance(v, (int, float, bool)): return str(v)\n"
helper += "    return None\n\n"
helper += "def _x93c_extract_summary_from_x90(x90_response):\n"
helper += "    if not isinstance(x90_response, dict): return None\n"
helper += "    direct=_x93c_pick_first_text(x90_response.get('summary'),x90_response.get('result_summary'),x90_response.get('message'),x90_response.get('final_report'))\n"
helper += "    if direct: return direct\n"
helper += "    result=x90_response.get('result')\n"
helper += "    if isinstance(result, str) and result.strip(): return result.strip()\n"
helper += "    if isinstance(result, dict):\n"
helper += "        direct=_x93c_pick_first_text(result.get('summary'),result.get('result'),result.get('message'),result.get('final'),result.get('final_report'))\n"
helper += "        if direct: return direct\n"
helper += "        out=[]\n"
helper += "        cycles=result.get('cycles')\n"
helper += "        if isinstance(cycles, list):\n"
helper += "            for c in cycles:\n"
helper += "                processed=c.get('processed') if isinstance(c, dict) else None\n"
helper += "                if not isinstance(processed, list): continue\n"
helper += "                for item in processed:\n"
helper += "                    if isinstance(item, dict):\n"
helper += "                        x=_x93c_pick_first_text(item.get('summary'),item.get('result'),item.get('message'))\n"
helper += "                        if x: out.append(x)\n"
helper += "        if out: return ' | '.join(out[-4:])\n"
helper += "    return None\n\n"
helper += "def _x93c_normalize_add_task_response(obj):\n"
helper += "    if not isinstance(obj, dict): return {'ok':False,'release':'X93C_FORCE_WEBUI_RESPONSE_NORMALIZER_FIX','bridge':'unknown','summary':'Invalid non-dict response.','result':obj,'report_file':None,'debug':{'raw':obj}}\n"
helper += "    raw=dict(obj); x90=raw.get('x90_response') if isinstance(raw.get('x90_response'), dict) else {}\n"
helper += "    summary=_x93c_pick_first_text(raw.get('summary'),raw.get('result_summary'),raw.get('message'),raw.get('final_report'),_x93c_extract_summary_from_x90(x90))\n"
helper += "    result=raw.get('result')\n"
helper += "    if result is None and isinstance(x90, dict): result=x90.get('result')\n"
helper += "    if result is None: result=summary\n"
helper += "    if not summary: summary=result.strip() if isinstance(result, str) and result.strip() else 'Task completed.'\n"
helper += "    out={'ok':bool(raw.get('ok', x90.get('ok', False) if isinstance(x90, dict) else False)),'release':raw.get('release') or 'X91_MASTER_AI_ADDTASK_BRIDGE','bridge':raw.get('bridge') or x90.get('bridge') or 'x90_webui_agent_bridge','summary':summary,'result':result,'report_file':raw.get('report_file') or x90.get('report_file'),'debug':{'normalized_by':'X93C_FORCE_WEBUI_RESPONSE_NORMALIZER_FIX','raw':raw}}\n"
helper += "    for k in ('task','ts','request_id','normalized'):\n"
helper += "        if k in raw: out[k]=raw[k]\n"
helper += "        elif isinstance(x90, dict) and k in x90: out[k]=x90[k]\n"
helper += "    return out\n"
helper += "# X93C_FORCE_WEBUI_RESPONSE_NORMALIZER_FIX_END\n"
if marker not in s:
    m=re.search(r"\n@app\.route\(", s)
    s=s[:m.start()]+helper+"\n"+s[m.start():] if m else s.rstrip()+helper+"\n"
changed=False
for name in ("response","resp","obj"):
    ns=re.sub(r"return\s+jsonify\(("+name+r")\)", r"return jsonify(_x93c_normalize_add_task_response(\1))", s)
    if ns != s:
        changed=True; s=ns
s=s.replace("_x93c_normalize_add_task_response(_x93c_normalize_add_task_response(", "_x93c_normalize_add_task_response(")
if not changed and "X93C_AFTER_REQUEST_NORMALIZER" not in s:
    hook="\n\n# X93C_AFTER_REQUEST_NORMALIZER_START\n"
    hook+="@app.after_request\n"
    hook+="def _x93c_after_request_normalizer(response):\n"
    hook+="    try:\n"
    hook+="        from flask import request, jsonify\n"
    hook+="        if request.path != '/add_task': return response\n"
    hook+="        if not response.is_json: return response\n"
    hook+="        obj=response.get_json(silent=True)\n"
    hook+="        if isinstance(obj, dict) and ('x90_response' in obj or 'summary' not in obj):\n"
    hook+="            nr=jsonify(_x93c_normalize_add_task_response(obj)); nr.status_code=response.status_code; return nr\n"
    hook+="    except Exception: return response\n"
    hook+="    return response\n"
    hook+="# X93C_AFTER_REQUEST_NORMALIZER_END\n"
    m=re.search(r"\nif\s+__name__\s*==\s*['\"]__main__['\"]\s*:", s)
    s=s[:m.start()]+hook+"\n"+s[m.start():] if m else s.rstrip()+hook+"\n"
p.write_text(s, encoding="utf-8", newline="\n")
print("[[REDACTED]] X93C patched master_ai_bridge.py")
