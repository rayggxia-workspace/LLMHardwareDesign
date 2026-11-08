"""Create an isolated, hash-recorded Qwen2 overlay of the frozen openTPU source.

Preserves native formats, kernels and schedules, adds real Q/K/V biases at
all native projection call sites, including tiled prefill. No peer PR/source
is mutated. This is not itself evidence of full-model quality or performance.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil


def replace_once(text,old,new):
    if text.count(old)!=1:
        raise ValueError('peer source differs at '+old[:100])
    return text.replace(old,new)


class Projections(ast.NodeTransformer):
    def __init__(self): self.changed=0
    def visit_Call(self,node):
        self.generic_visit(node)
        if not (isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name)
                and node.func.value.id=='ol' and node.func.attr=='dot' and len(node.args)>=2):
            return node
        weight=node.args[1]
        base=weight.value if isinstance(weight,ast.Subscript) else weight
        if not (isinstance(base,ast.Attribute) and isinstance(base.value,ast.Name)
                and base.value.id=='lw' and base.attr in ('wq','wk','wv')):
            return node
        selection=ast.Constant(None)
        if isinstance(weight,ast.Subscript):
            if not isinstance(weight.slice,ast.Tuple) or len(weight.slice.elts)!=2:
                raise ValueError('unexpected QKV matrix slice')
            row=weight.slice.elts[0]
            if isinstance(row,ast.Slice):
                selection=ast.Call(func=ast.Name(id='slice',ctx=ast.Load()),args=[
                    row.lower or ast.Constant(None),row.upper or ast.Constant(None),row.step or ast.Constant(None)],keywords=[])
            else: selection=row
        bias=ast.Call(func=ast.Name(id='_projection_bias',ctx=ast.Load()),
            args=[ast.Name(id='lw',ctx=ast.Load()),ast.Constant(base.attr[-1]),selection],keywords=[])
        node.func=ast.Name(id='_qkv_dot',ctx=ast.Load())
        node.args.insert(2,bias)
        self.changed+=1
        return node


HELPERS = """
def _projection_bias(lw, kind, selection=None):
    bias = getattr(lw, 'b' + kind, None)
    return bias[selection] if bias is not None and selection is not None else bias


def _qkv_dot(xs, weight, bias, **kwargs):
    if bias is None:
        return ol.dot(xs, weight, **kwargs)
    out = kwargs.pop('out', None)
    result = ol.dot(xs, weight, **kwargs) + ol.load(bias)[None, :]
    if out is not None:
        out.set(result)
        return out
    return result
"""


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.output.exists():raise ValueError('fresh overlay required')
    source_hash={str(x.relative_to(a.source)):hashlib.sha256(x.read_bytes()).hexdigest()
                 for x in sorted(a.source.rglob('*.py'))}
    shutil.copytree(a.source,a.output,ignore=shutil.ignore_patterns('__pycache__','.git'))
    q=a.output/'opentpu/llm/qwen3.py'; text=q.read_text()
    text=replace_once(text,'    qk_norm: bool = True','    qkv_bias: bool = False\n    qk_norm: bool = True')
    text=replace_once(text,'(self.n_q // self.n_kv <= cfg.MCOLS,',
                      '(self.n_q // self.n_kv <= cfg.MCOLS or self.qkv_bias,')
    text=replace_once(text,'        S, D = cfg.S, cfg.D\n        need =',
                      "        S, D = cfg.S, cfg.D\n        if self.qkv_bias and S != 1:\n            raise ValueError('Qwen2 overlay currently qualifies the native one-slice board only')\n        need =")
    for kind,heads in [('q','n_q'),('k','n_kv'),('v','n_kv')]:
        line=f'        {kind} = (h @ W[p + "self_attn.{kind}_proj.weight"].T).reshape(T, spec.{heads}, d)'
        text=replace_once(text,line,line+f'\n        if spec.qkv_bias: {kind} = {kind} + W[p + "self_attn.{kind}_proj.bias"].reshape(1, spec.{heads}, d)')
        line=f'            {kind} = (w(p + "self_attn.{kind}_proj.weight") @ h).reshape(spec.{heads}, d)'
        text=replace_once(text,line,line+f'\n            if spec.qkv_bias: {kind} = {kind} + W[p + "self_attn.{kind}_proj.bias"].reshape(spec.{heads}, d)')
    text=replace_once(text,'            if spec.qk_norm:\n                L.update',
        '            if spec.qkv_bias:\n                for kind in ("q", "k", "v"):\n                    L["b" + kind] = lb.alloc(4 * self.mats["w" + kind][0])\n            if spec.qk_norm:\n                L.update')
    text=replace_once(text,'                if spec.qk_norm:\n                    put(s, Lo["qn"], f32(qk[0]))',
        '                if spec.qkv_bias:\n                    for kind in ("q", "k", "v"):\n                        put(s, Lo["b" + kind], f32(W[p + "self_attn." + kind + "_proj.bias"]))\n                if spec.qk_norm:\n                    put(s, Lo["qn"], f32(qk[0]))')
    text=replace_once(text,'            for name, (n, k) in self.mats.items():\n                da, sa = lofs[name]',
        '            for kind in ("q", "k", "v"):\n                setattr(ns, "b" + kind, Tensor(off + lofs["b" + kind], (self.mats["w" + kind][0],), (1,)) if spec.qkv_bias else None)\n            for name, (n, k) in self.mats.items():\n                da, sa = lofs[name]')
    edits={}
    for path,body in [(q,text),(a.output/'opentpu/llm/tiled.py',(a.output/'opentpu/llm/tiled.py').read_text())]:
        tree=ast.parse(body); visitor=Projections(); tree=visitor.visit(tree);ast.fix_missing_locations(tree)
        if not visitor.changed: raise ValueError('QKV native sites disappeared')
        body=ast.unparse(tree)+'\n'
        body+=HELPERS if path==q else '\nfrom .qwen3 import _projection_bias, _qkv_dot\n'
        ast.parse(body);path.write_text(body)
        edits[str(path.relative_to(a.output))]={'projection_calls_wrapped':visitor.changed,
                                               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    init=a.output/'opentpu/llm/__init__.py'
    init.write_text(replace_once(init.read_text(),'    if t == "qwen3":',
        '    if t == "qwen2":\n        from .qwen2_overlay import spec_from_hf\n        return spec_from_hf(path)\n    if t == "qwen3":'))
    adapter=a.output/'opentpu/llm/qwen2_overlay.py'
    adapter.write_text("""import json
from pathlib import Path
from .qwen3 import Spec
from . import rope_parameters

def spec_from_hf(path):
    c=json.loads((Path(path)/'config.json').read_text())
    if c['model_type']!='qwen2' or c.get('use_sliding_window') or c.get('rope_scaling'):
        raise ValueError('overlay supports dense Qwen2 without scaled/sliding RoPE only')
    rp=rope_parameters(c,path)
    eos=c.get('eos_token_id')
    return Spec(hidden=c['hidden_size'],layers=c['num_hidden_layers'],n_q=c['num_attention_heads'],
        n_kv=c['num_key_value_heads'],head_dim=c.get('head_dim') or c['hidden_size']//c['num_attention_heads'],
        ffn=c['intermediate_size'],vocab=c['vocab_size'],eps=c['rms_norm_eps'],
        theta=rp.get('rope_theta',c.get('rope_theta',10000.)),tied=c.get('tie_word_embeddings',False),
        bos=c.get('bos_token_id'),eos=tuple(eos) if isinstance(eos,list) else (eos,),
        qk_norm=False,qkv_bias=True,embed='int8')
""")
    receipt={'frozen_peer_commit':'91df41092f612361c5bc22f83b31d23382ffabb0',
        'original_python_sha256':source_hash,'projection_edits':edits,
        'adapter_sha256':hashlib.sha256(adapter.read_bytes()).hexdigest(),
        'loader_sha256':hashlib.sha256(init.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'numeric_qualified':False,'performance_qualified':False,
        'boundary':'QKV bias adapter and existing split-GQA kernels; no hardware/format downgrade; qualification pending'}
    (a.output/'qwen2-overlay.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'projection_edits':edits,'numeric_qualified':False}))

if __name__=='__main__':main()
