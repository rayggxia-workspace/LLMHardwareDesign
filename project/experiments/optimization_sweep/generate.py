"""Add separately accounted timing sensitivities over the frozen shared32 model."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('source anchor count ' + repr(before))
    return text.replace(before, after)


def generate(repo, out, r1, r2, r4):
    repo, out = Path(repo), Path(out)
    frozen = load(repo / 'project/experiments/shared_pool_study/generate_shared_pool.py', 'sweep_frozen_generator')
    receipt = frozen.generate(repo, out, r1, r2, r4)
    s = (out / 'model.cpp').read_text(encoding='utf8')
    s = once(s, '#include "detail.hpp"', '#include "optimization.hpp"\n#include "detail.hpp"')
    s = once(s, 'Study s("study",c,argv[1]);',
             'if(!optimization::configure()){std::cerr<<"invalid optimization case\\n";return 2;}\n'
             'c.vector_lanes=int(optimization::lanes);c.bandwidth=optimization::bandwidth;\n'
             'Study s("study",c,argv[1]);')
    s = once(s, 'U cost=cfg.vecpipe?(ceildiv(n,cfg.vector_lanes)+5)*micro:ceildiv(n,4)*cfg.ewise*micro;',
             'U cost=optimization::vector_cost(cfg.vecpipe?(ceildiv(n,4)+5)*micro:ceildiv(n,4)*cfg.ewise*micro,'
             'cfg.vecpipe?(ceildiv(n,cfg.vector_lanes)+5)*micro:ceildiv(n,4)*cfg.ewise*micro);')
    s = once(s, 'U packets=ceildiv(n,4),cost=cfg.vecpipe?ceildiv(n,cfg.vector_lanes)+5:packets*cfg.ewise;',
             'U packets=ceildiv(n,4),cost=optimization::vector_cost(cfg.vecpipe?packets+5:packets*cfg.ewise,'
             'cfg.vecpipe?ceildiv(n,cfg.vector_lanes)+5:packets*cfg.ewise);')
    s = once(s, 'e_work+=nexp_extra*C;cycles(nexp_extra);',
             'const U nexp_actual=optimization::nexp_cost(o.elements,nexp_qualified,nexp_extra);'
             'e_work+=nexp_actual*C;cycles(nexp_actual);')
    s = once(s, 'if(bytes)pause_until(port.reserve(now(),s_port_duration(cfg,group,bytes)));',
             'if(bytes)pause_until(port.reserve(now(),optimization::write_cost(bytes)));')
    s = once(s, 'emit_hardware();shared_pool::pool.emit(std::cout);',
             'emit_hardware();optimization::emit(std::cout);shared_pool::pool.emit(std::cout);')
    (out / 'model.cpp').write_bytes(s.encode())
    for name in ('matrix.inc', 'context_worker.inc'):
        s = (out / name).read_text(encoding='utf8')
        s = once(s, 'U adapt=std::max(ceildiv(p->abytes,32),ceildiv(p->bbytes,64));',
                 'U adapt=optimization::adapt(p->abytes,p->bbytes);')
        s = once(s, 'U compute=U(p->r)*ceildiv(p->k,8);', '')
        anchor = 'U tail=4+(p->ki==0?14:0)+(p->last?8+ceildiv(U(p->r)*p->n,4)*2:0);'
        s = once(s, anchor, anchor+'\n   U compute=optimization::compute(p->r,p->k,tail);')
        (out / name).write_bytes(s.encode())
    p = out / 'shared_pool.hpp'
    s = p.read_text(encoding='utf8')
    s = once(s, 'offset+=32){const U n=std::min<U>(32,take-offset);',
             'offset+=optimization::a_bytes){const U n=std::min<U>(optimization::a_bytes,take-offset);')
    s = once(s, 'ceildiv((count-shared_k)*element_bytes,32)*C',
             'ceildiv((count-shared_k)*element_bytes,optimization::a_bytes)*C')
    s = once(s, r'\"A_feeder_bytes_per_cycle\":32"', r'\"A_feeder_bytes_per_cycle\":"<<optimization::a_bytes')
    p.write_bytes(s.encode())
    (out / 'optimization.hpp').write_bytes((HERE / 'optimization.hpp').read_bytes())
    actual = {p.name: sha(p) for p in out.iterdir() if p.suffix in ('.cpp', '.hpp', '.inc')}
    changed = sorted(n for n in actual if actual[n] != receipt['generated_sha256'].get(n))
    if changed != ['context_worker.inc', 'matrix.inc', 'model.cpp', 'optimization.hpp', 'shared_pool.hpp']:
        raise ValueError('unexpected generated closure ' + repr(changed))
    result = dict(frozen=receipt, generated_sha256=actual, changed_files=changed,
                  scope='conditional timing only; frozen profiles retained as reference ledgers')
    (out / 'sweep-generation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    return result
