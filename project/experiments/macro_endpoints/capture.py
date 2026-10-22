"""Read only three declared ordinary LEFs using the member's existing SSH key."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
from common import (CONFIG, ROOT, check_config, check_observation, clean_provenance, file_index,
                    git, json_bytes, load_snapshot, sha, utc_now)


def collector_script(cfg):
    # No shell fragments from repository data. Remote command is fixed and the
    # Python program is passed on stdin; the validated request is a JSON literal.
    request = {"root": cfg["allowed_root"], "files": cfg["files"], "max_bytes": cfg["limits"]["max_bytes_per_lef"]}
    return "REQUEST = " + repr(request) + "\n" + r'''
import base64, datetime, getpass, hashlib, json, os, pathlib, socket, stat, sys
root = pathlib.Path(REQUEST['root']).resolve(strict=True)
records = []
for item in REQUEST['files']:
    requested = root / item['relative_path']
    resolved = requested.resolve(strict=True)
    if root not in resolved.parents:
        raise RuntimeError('source path leaves the declared project attempt')
    with resolved.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > REQUEST['max_bytes']:
            raise RuntimeError('source is not a bounded ordinary file')
        data = stream.read(REQUEST['max_bytes'] + 1)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if stamp(before) != stamp(after) or len(data) != before.st_size:
        raise RuntimeError('source changed during read')
    records.append({'id': item['id'], 'requested_path': str(requested),
        'resolved_path': str(resolved), 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'stat_before': list(stamp(before)), 'stat_after': list(stamp(after)),
        'base64': base64.b64encode(data).decode('ascii')})
print(json.dumps({'remote_hostname': socket.gethostname(), 'remote_user': getpass.getuser(),
    'remote_python': sys.version, 'captured_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'observations': records}))
'''


def ssh_argv(ssh, identity, known_hosts, host):
    return [str(ssh), "-F", "NUL" if os.name == "nt" else "/dev/null", "-T",
            "-i", str(identity), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "PreferredAuthentications=publickey", "-o", "ConnectTimeout=8",
            "-o", "ConnectionAttempts=1", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", "UserKnownHostsFile=" + str(known_hosts),
            "-p", "22", host, "python3 -B -"]


def validate_response(cfg, response):
    records = response["observations"]
    expected = {x["id"]: x for x in cfg["files"]}
    if len(records) != 3 or {r["id"] for r in records} != set(expected):
        raise AssertionError("remote response does not contain exactly the requested sources")
    files, observations = {}, []
    for row in records:
        item = expected[row["id"]]
        data = base64.b64decode(row["base64"], validate=True)
        if len(data) != row["bytes"] or sha(data) != row["sha256"] or len(data) > cfg["limits"]["max_bytes_per_lef"]:
            raise AssertionError("transferred bytes do not match remote measurement")
        check_observation(cfg, item, row, {"bytes": len(data), "sha256": sha(data)})
        files[row["id"] + ".lef"] = data
        observations.append({k: v for k, v in row.items() if k != "base64"})
    return files, observations


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--identity", type=Path, required=True, help="existing member key, never copied or printed")
    p.add_argument("--known-hosts", type=Path, required=True)
    p.add_argument("--ssh", default="ssh")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or a.out.resolve().is_relative_to(ROOT):
        raise SystemExit("Choose a NEW task temporary directory outside the project for source downloads")
    cfg_bytes = CONFIG.read_bytes()
    cfg = check_config(json.loads(cfg_bytes))
    provenance = clean_provenance(["common.py", "capture.py", "inputs.json"])
    script = collector_script(cfg)
    started = utc_now()
    result = subprocess.run(ssh_argv(a.ssh, a.identity, a.known_hosts, cfg["ssh_host"]),
                            input=script.encode(), capture_output=True, timeout=90, check=True)
    if result.stderr:
        # Strict host-key checking/public-key-only auth never auto accepts keys.
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
    response = json.loads(result.stdout)
    if response["remote_user"] != "yuzelu":
        raise AssertionError("unexpected remote login identity")
    files, observations = validate_response(cfg, response)
    if git("status", "--porcelain") or git("rev-parse", "HEAD") != provenance["source_commit"]:
        raise AssertionError("source changed during capture")
    a.out.mkdir(parents=True)
    for name, data in files.items():
        (a.out / name).write_bytes(data)
    (a.out / "inputs.json").write_bytes(cfg_bytes)
    manifest = {"schema": 1, "input_version": cfg["input_version"], "started_utc": started,
                "finished_utc": utc_now(), "provenance": provenance, "config_sha256": sha(cfg_bytes),
                "collector_script_sha256": sha(script.encode()),
                "ssh_host": cfg["ssh_host"], "authentication": "existing member dedicated public-key authentication",
                "remote_hostname": response["remote_hostname"], "remote_user": response["remote_user"],
                "remote_python": response["remote_python"], "remote_captured_utc": response["captured_utc"],
                "upstream": cfg["upstream"], "observations": observations, "files": file_index(a.out),
                "upstream_hash_comparison": "not available: pinned records omit per-file SHA-256; hashes measured in this capture"}
    (a.out / "capture.json").write_bytes(json_bytes(manifest))
    load_snapshot(a.out)
    print(json.dumps({"status": "PASS", "source_commit": provenance["source_commit"],
                      "files": [{"id": r["id"], "bytes": r["bytes"], "sha256": r["sha256"]} for r in observations]}, indent=2))


if __name__ == "__main__":
    main()
