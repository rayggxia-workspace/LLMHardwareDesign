"""Update only the existing task's body and verify exact UTF-8 readback."""
import json
import pathlib
import subprocess
import datetime

root = pathlib.Path(__file__).resolve().parents[1]
repo = "rayggxia-workspace/LLMHardwareDesign"

def api(*args):
    p = subprocess.run(["gh", "api", *args], capture_output=True, encoding="utf-8", timeout=30)
    if p.returncode:
        raise RuntimeError(p.stderr[:500])
    return json.loads(p.stdout)

assert api("user")["login"] == "YUZE-LU"
receipt = {"published_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "backend_accepted": False, "updates": []}
for endpoint, filename in [("pulls/290", "pr-body-current.md"), ("issues/289", "issue-body-current.md")]:
    body = (root / filename).read_text(encoding="utf-8")
    assert "\ufffd" not in body
    target = root / (filename + ".payload.json")
    target.write_text(json.dumps({"body": body}, ensure_ascii=False), encoding="utf-8")
    api("--method", "PATCH", f"repos/{repo}/{endpoint}", "--input", str(target))
    readback = api(f"repos/{repo}/{endpoint}")
    assert readback["body"] == body
    if endpoint.startswith("pulls"):
        assert readback["draft"] and readback["state"] == "open"
    else:
        assert "status:in_progress" in [label["name"] for label in readback["labels"]]
    receipt["updates"].append({"url": readback["html_url"], "exact_body_readback": True})
out = root / "audit/publication-C35-checkpoint.json"
out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
