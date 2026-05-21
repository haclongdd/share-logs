from x93_response_normalizer import normalize_add_task_response
sample = {
    "ok": True,
    "release": "X91_MASTER_AI_ADDTASK_BRIDGE",
    "bridge": "x90_webui_agent_bridge",
    "report_file": "/app/runtime/reports/sample.json",
    "x90_response": {
        "ok": True,
        "release": "X90_WEBUI_AGENT_BRIDGE",
        "bridge": "x90_webui_bridge",
        "request_id": "x90req_test",
        "report_file": "/app/runtime/reports/x90.json",
        "task": "x93 unit"
    }
}
out = normalize_add_task_response(sample)
assert out["ok"] is True
assert out["release"] == "X91_MASTER_AI_ADDTASK_BRIDGE"
assert out["bridge"] == "x90_webui_agent_bridge"
assert out["task"] == "x93 unit"
assert out["report_file"] == "/app/runtime/reports/sample.json"
assert "summary" in out and "report=" in out["summary"]
assert "debug" in out and "raw" in out["debug"]
print("[[REDACTED]] X93 unit normalization contract ok")
