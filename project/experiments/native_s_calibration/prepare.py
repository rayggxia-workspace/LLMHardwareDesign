"""Reconstruct one frozen service model, then apply explicit port sensitivity.

This is a diagnostic, not a calibrated full-hardware performance claim.
The historical source and historical result archives are never modified.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "work/YUZE-LU/250/performance/run-08.tar.gz.b64"
EXPECTED = "605c93c"  # full digest is checked against the versioned recovery receipt


def prepare(destination):
    raw = base64.b64decode(b"".join(PACKAGE.read_bytes().split()), validate=True)
    receipt = json.loads(PACKAGE.with_name("recovery-08.json").read_text())
    digest = hashlib.sha256(raw).hexdigest()
    assert digest.startswith(EXPECTED) and digest == receipt["archive_SHA256"]
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        files = {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}
    assert {p: hashlib.sha256(v).hexdigest() for p, v in files.items()} == receipt["members_SHA256"]
    destination.mkdir(exist_ok=False)
    generated = {}
    for name, data in files.items():
        if name.startswith("candidate/") or name == "micro.trace":
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            generated[name] = hashlib.sha256(data).hexdigest()
    path = destination / "candidate/model.cpp"
    text = path.read_text()
    old = "U s_port_duration(const Config& cfg,int group,U bytes){\n"
    new = old + """ // NS_PORT_SCOPE: 0 historical, 1 P only, 2 P and U.
 // Changes every common sio()/DMA S call, not just the X/Down special paths.
 // Response is a per-reservation sensitivity; not a measured request pipeline.
 const int scope=nv_int("NS_PORT_SCOPE",0);
 if(scope==2||(scope==1&&group<cfg.mcount)){
  return (ceildiv(bytes,U(16))*U(nv_int("NS_WORD_CYCLES",1))+
          U(nv_int("NS_RESPONSE_CYCLES",0)))*C;
 }
"""
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), newline="\n")
    from calibrated import apply
    apply(destination)
    for changed in destination.joinpath('candidate').iterdir():
        if changed.is_file():
            generated[changed.relative_to(destination).as_posix()] = hashlib.sha256(changed.read_bytes()).hexdigest()
    generated["candidate/model.cpp"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination / "generation.json").write_text(json.dumps(dict(
        source_archive_sha256=digest, source_members=receipt["members_SHA256"],
        generated=generated, qualification="port-width sensitivity only; not RTL calibrated"), indent=2) + "\n")


if __name__ == "__main__":
    import sys
    prepare(Path(sys.argv[1]))
