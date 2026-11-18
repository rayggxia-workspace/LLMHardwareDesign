"""Legacy per-file transfer of the frozen six-model closure over verified SSH.

The destination password is read interactively and is never persisted. Run with
the optional local Paramiko dependency directory on PYTHONPATH. Final files are
fully checked by the compute-node preflight; incomplete files have a
.transfer-part suffix. Prefer stage_remote_energy_archives.py and native scp -3
when the gateway stalls this per-file SFTP path.
"""
import argparse
from datetime import datetime, timezone
import getpass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shlex
import stat
import time

import paramiko


OLD = "/public/home/yuzelu"
RUNS = OLD + "/Melodydt/runs/issue-274"
DEST = "/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01/six-model-energy-01"
MODELS = ("llama", "granite", "phi", "gemma", "qwen35", "falcon")


def stages(model):
    variant = "kv64" if model in ("llama", "granite") else "cache"
    root = RUNS + ("/three-p-gemma-q12-02" if model == "gemma" else "/three-p-full-01")
    return root, {mode: root + ("/run-116000" if model == "gemma" else
                 "/run-{}-{}".format(115618 if mode == "prefill" else 115619, model)) +
                 "/{}-w4-{}-pr272-combined".format("prefill" if mode == "prefill" else "decode-live", variant)
                 for mode in ("prefill", "decode")}


def connect(host, user, known, **kwargs):
    client = paramiko.SSHClient()
    client.load_host_keys(str(known))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(host, username=user, timeout=30, auth_timeout=45,
                   look_for_keys=False, allow_agent=False, **kwargs)
    client.get_transport().set_keepalive(30)
    return client


def execute(client, command):
    _, stdout, stderr = client.exec_command(command)
    result = stdout.read().decode()
    error = stderr.read().decode()
    if stdout.channel.recv_exit_status():
        raise RuntimeError(error + result)
    return result


def walk(sftp, root):
    for item in sorted(sftp.listdir_attr(root), key=lambda x: x.filename):
        path = root + "/" + item.filename
        if stat.S_ISDIR(item.st_mode):
            yield from walk(sftp, path)
        elif stat.S_ISREG(item.st_mode):
            yield path, item.st_size
        else:
            raise ValueError("nonregular artifact: " + path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    p.add_argument("--submit", action="store_true", help="submit the reviewed remote run script after each model")
    p.add_argument("--log", type=Path, required=True)
    args = p.parse_args()
    workspace = Path(__file__).resolve().parents[3]
    args.log.parent.mkdir(parents=True, exist_ok=True)
    log = args.log.open("a", encoding="utf-8", buffering=1)

    def report(**row):
        row["utc"] = datetime.now(timezone.utc).isoformat()
        text = json.dumps(row, ensure_ascii=False)
        print(text, flush=True)
        log.write(text + "\n")

    password = getpass.getpass("BSCC-T6 password: ")
    old = connect("10.129.166.172", "yuzelu", workspace / "tmp/energy-054-ddr-host.pub",
                  key_filename="C:/Users/Administrator/.ssh/id_ed25519_server_ops_20261030")
    new = connect("ssh.cn-zhongwei-1.paracloud.com", "t6s011227@BSCC-T6",
                  workspace / "tmp/issue280-bscc-t6/macro-views-20261117/bscc-gateway-known_hosts",
                  password=password, compress=True)
    del password
    source = paramiko.SFTPClient.from_transport(old.get_transport(), window_size=64*1024*1024)
    target = paramiko.SFTPClient.from_transport(new.get_transport(), window_size=64*1024*1024)
    source.get_channel().settimeout(90)
    target.get_channel().settimeout(90)
    made = set()

    def mkdir(path):
        if path in made:
            return
        try:
            target.stat(path)
        except FileNotFoundError:
            mkdir(str(PurePosixPath(path).parent))
            target.mkdir(path)
        made.add(path)

    for model in args.models:
        root, baseline = stages(model)
        files, expected = {}, {}
        for entry in source.listdir_attr(root):
            if stat.S_ISREG(entry.st_mode) and entry.filename.endswith((".py", ".cpp", ".sha256", ".sbatch", ".txt")):
                files[root + "/" + entry.filename] = entry.st_size
        for mode, stage in baseline.items():
            files.update(walk(source, stage))
            with source.open(stage + "/assets/plan.json") as f:
                plan_raw = f.read()
            with source.open(stage + "/result.json") as f:
                result = json.load(f)
            if sha256(plan_raw).hexdigest() != result["plan_sha256"]:
                raise ValueError("frozen plan receipt mismatch: " + stage)
            for image in json.loads(plan_raw)["images"]:
                path = image["path"]
                if not path.startswith(RUNS + "/") or ".." in PurePosixPath(path).parts:
                    raise ValueError("artifact outside authorized task: " + path)
                files[path] = source.stat(path).st_size
                expected[path] = image["sha256"]
        report(model=model, phase="transfer_start", files=len(files), bytes=sum(files.values()))
        manifest = []
        total, last_report = 0, time.monotonic()
        for path, size in sorted(files.items()):
            dest = DEST + "/sourcefs/" + path[len(OLD) + 1:]
            mkdir(str(PurePosixPath(dest).parent))
            # Already copied shared sources are cheap to verify and reuse.
            exists = False
            try:
                exists = target.stat(dest).st_size == size
            except FileNotFoundError:
                pass
            if exists:
                source_hash = expected.get(path)
                if source_hash is None:
                    with source.open(path) as f:
                        source_hash = sha256(f.read()).hexdigest()
                # The compute-node preflight must hash every destination before
                # replay. Reuse here does not declare the transfer accepted.
                manifest.append({"source": path, "bytes": size, "sha256": source_hash})
                total += size
                continue
            digest = sha256()
            with target.open(dest + ".transfer-part", "wb") as output:
                output.set_pipelined(True)

                class Sink:
                    def write(self, data):
                        nonlocal last_report
                        digest.update(data)
                        output.write(data)
                        if time.monotonic() - last_report > 30:
                            report(model=model, phase="transfer", bytes_done=total+output.tell(), bytes_total=sum(files.values()))
                            last_report = time.monotonic()
                source.getfo(path, Sink(), prefetch=True, max_concurrent_prefetch_requests=32)
            actual = digest.hexdigest()
            if path in expected and actual != expected[path]:
                raise ValueError("transmitted artifact disagrees with frozen plan: " + path)
            target.posix_rename(dest + ".transfer-part", dest)
            manifest.append({"source": path, "bytes": size, "sha256": actual})
            total += size
            if time.monotonic() - last_report > 30:
                report(model=model, phase="transfer", bytes_done=total, bytes_total=sum(files.values()))
                last_report = time.monotonic()
        receipt = {"model": model, "baseline": baseline, "source_root": root,
                   "baseline_commit": "fbff1bd0e455739f28d9b7dd00b97216fe7bb847", "files": manifest}
        with target.open(DEST + "/" + model + "-transfer.json", "w") as f:
            f.write(json.dumps(receipt, indent=2) + "\n")
        report(model=model, phase="transfer_complete", files=len(manifest), bytes=total)
        if args.submit:
            command = "cd " + shlex.quote(DEST) + " && sbatch --parsable --time=0 --job-name=mdt-280e-" + model + " run_six_model_energy.sbatch " + model
            job = execute(new, command).strip()
            report(model=model, phase="submitted", command=command, job=job)
    source.close()
    target.close()
    old.close()
    new.close()


if __name__ == "__main__":
    main()
