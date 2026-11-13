"""Restore the exact PR249 executed source, then add only Issue250 X service.

This is a text/SHA preparation step, not a local accelerator simulation.
The historical executed source is authoritative, rather than regenerating it
from a newer (and potentially different) compiler.
"""
import argparse
import hashlib
import json
from pathlib import Path

from followup_report import load_runs


def once(text, old, new):
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


def prepare(root):
    here = Path(__file__).resolve().parent
    repo = here.parents[2]
    index, runs, _ = load_runs(repo / "work/YUZE-LU/248/followup")
    run_name = "issue248-stream-feed-20261110-02"
    files = runs[run_name]
    root.mkdir(parents=True, exist_ok=False)
    source = root / "candidate"
    source.mkdir()
    recovered = {}
    for name, data in files.items():
        if name.startswith("frozen/"):
            relative = name.removeprefix("frozen/")
            (source / relative).write_bytes(data)
            recovered[relative] = hashlib.sha256(data).hexdigest()
    for name in ("micro.trace",):
        (root / name).write_bytes(files[name])
    baseline = json.loads(files["frozen-bank4-Xreg/report.json"])
    (root / "historical-baseline.json").write_text(json.dumps(baseline, indent=2) + "\n")
    (root / "recovery.json").write_text(json.dumps(dict(
        source_commit="85fe7989b11a95725c9b1bc6daee085f74a500b8",
        archive=next(r for r in index["runs"] if r["name"] == run_name),
        recovered_frozen_files_SHA256=recovered), indent=2) + "\n")

    p = source / "model.cpp"
    text = p.read_text()
    text = once(text, '#include "closure_service.inc"',
                '#include "shared_x_service.inc"\n#include "closure_service.inc"')
    text = once(text, 'read(trace);SC_THREAD(run);',
                'read(trace);SC_THREAD(run);SC_THREAD(sx_serve);SC_THREAD(sx_local_serve0);SC_THREAD(sx_local_serve1);SC_THREAD(sx_local_serve2);')
    text = once(text, 'passed=true;', 'sx_check();passed=true;')
    text = once(text, '<<(cfg.cl_mode>=5?4096:0)',
                '<<(cfg.cl_mode>=5&&sx_mode()==0?4096:0)')
    text = once(text, 'std::cout<<"}\\n";', 'sx_emit();std::cout<<"}\\n";')
    p.write_bytes(text.encode())

    p = source / "closure_service.inc"
    text = p.read_text()
    text = once(text, 'U generation,prior;std::vector',
                'U generation,prior;std::shared_ptr<SXRequest> sx;std::vector')
    text = once(text, 'new CLTask{j,bank,b.generation[bank],now(),{}}',
                'new CLTask{j,bank,b.generation[bank],now(),{}, {}}')
    text = once(text, 'U address=tensors[j.weight].base',
                'if(sx_mode()==1&&!j.down)t->sx=sx_request(worker,j.kk);\n     if(sx_mode()>=3&&!j.down)t->sx=sx_local_request(worker,j.kk);\n     U address=tensors[j.weight].base')
    text = once(text, '  auto producer=sc_spawn([&,this]{',
                '  if(sx_mode()==4){sx_local_use_plan[worker].clear();for(const auto& j:jobs)if(!j.down)++sx_local_use_plan[worker][j.kk];}\n  auto producer=sc_spawn([&,this]{')
    text = once(text, '    b.ready.write(nullptr);', '    if(sx_mode()==4)sx_local_close(worker);\n    b.ready.write(nullptr);') if '    b.ready.write(nullptr);' in text else once(text, '   b.ready.write(nullptr);', '   if(sx_mode()==4)sx_local_close(worker);\n   b.ready.write(nullptr);')
    text = once(text, '   const U start=now();U consumed=',
                '   if(sx_mode()>=3&&!t->job.down)sx_local_await(t->sx,worker);\n   const U start=now();U consumed=')
    text = once(text, 'consumed=std::max(consumed,start+8*C);pause_until(consumed+3*C);',
                '''if(!t->job.down&&sx_mode()==1){sx_consume(t->sx,worker);}
    if(!t->job.down&&sx_mode()==2){consumed=std::max(consumed,store[worker].reserve(start,(ceildiv(U(256),U(sx_local_width()))+sx_local_latency())*C));sx_local_reads+=256;}
    consumed=std::max(consumed,start+8*C);pause_until(consumed);if(sx_mode()>=3&&!t->job.down)sx_local_release(t->sx,worker);pause_until(consumed+3*C);''')
    text = text.replace('s_port_duration(cfg,worker,nv_state_bytes())', '(sx_mode()>=3?sx_s_duration(nv_state_bytes()):s_port_duration(cfg,worker,nv_state_bytes()))')
    text = text.replace('s_port_duration(cfg,worker,bytes)', '(sx_mode()>=3?sx_s_duration(bytes):s_port_duration(cfg,worker,bytes))')
    text = text.replace('s_port_duration(cfg,worker,32)', '(sx_mode()>=3?sx_s_duration(32):s_port_duration(cfg,worker,32))')
    text = once(text, 'if(cfg.cl_mode>=5){for(int p=0;p<3;++p){cl_link(p,4096,3,true);}}',
                '''if(cfg.cl_mode>=5){
   if(sx_mode()==1){sx_begin_fill();}
   else if(!sx_early()){for(int p=0;p<3;++p){if(sx_mode()>=2){sx_local_fill(p);}else{cl_link(p,4096,3,true);}}}
   else{sx_early_join();}
  }
  if(sx_mode()>=2){require(cl_peak_s+4096<=16384,"X in existing S capacity");sx_local_begin();}''')
    text = once(text, '   for(U off=0;off<2048;off+=128){read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);}',
                '   if(sx_early())sx_early_begin();\n   for(U off=0;off<2048;off+=128){read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);if(sx_early())sx_early_valid(off/128);}') if '   for(U off=0;' in text else once(text, '  for(U off=0;off<2048;off+=128){read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);}',
                '  if(sx_early())sx_early_begin();\n  for(U off=0;off<2048;off+=128){read_range(gate.in[0],off*4,512);cycles(66);sio(3,256);if(sx_early())sx_early_valid(off/128);}')
    text = once(text, 'matrix_backed.insert(down.out);cl_active=false;',
                'if(sx_mode()==1){sx_release();}\n   matrix_backed.insert(down.out);cl_active=false;')
    p.write_bytes(text.encode())
    for name in ("shared_x_service.inc", "shared_x_driver.py", "shared_x_job.sh", "shared_x_payload_check.py", "shared_x_protocol_job.sh"):
        (root / name).write_bytes((here / name).read_bytes())
    (source / "shared_x_service.inc").write_bytes((here / "shared_x_service.inc").read_bytes())
    manifest = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob("*")) if p.is_file()}
    (root / "source.sha256").write_bytes("".join(f"{sha}  {name}\n" for name, sha in manifest.items()).encode())
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    print(json.dumps(dict(files=len(prepare(args.out)), out=str(args.out))))
