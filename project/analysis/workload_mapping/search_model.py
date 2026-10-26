"""Shape-derived transformer DAGs for communication optimization, not inference.

Immutable values have durable external copies. Every compute result is written
through (charged). Local copies may be evicted without another write. This
deliberately conservative, common policy isolates task order/placement effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Value:
    id: str
    shape: tuple
    bits: int = 8
    role: str = "activation"
    producer: int = -1

    @property
    def size(self):
        return math.prod(self.shape)*self.bits//8


@dataclass(frozen=True)
class Task:
    id: str
    op: str
    reads: tuple
    output: str
    dependencies: tuple
    workspace: int
    macs: int
    pool: str
    phase: str


class Workload:
    def __init__(self, name, config):
        self.name, self.config = name, config
        self.values, self.tasks = {}, []

    def initial(self, name, shape, role="activation", bits=8):
        if name not in self.values:
            self.values[name] = Value(name, tuple(shape), bits, role)
        assert self.values[name].shape == tuple(shape)
        return name

    def add(self, name, op, reads, shape, *, workspace=0, macs=0,
            pool="vector", phase="prefill", after=()):
        reads = tuple(dict.fromkeys(reads))
        deps = {self.values[v].producer for v in reads if self.values[v].producer >= 0}
        deps.update(after)
        i = len(self.tasks)
        assert all(0 <= d < i for d in deps)
        out = "v_"+name
        assert out not in self.values
        self.values[out] = Value(out, tuple(shape), 8, "activation", i)
        self.tasks.append(Task(name, op, reads, out, tuple(sorted(deps)), workspace,
                               macs, pool, phase))
        return out

    def freeze(self):
        self.deps = [sum(1 << d for d in t.dependencies) for t in self.tasks]
        self.users = {v: [] for v in self.values}
        self.successors = [set() for _ in self.tasks]
        for i, t in enumerate(self.tasks):
            for v in t.reads:
                self.users[v].append(i)
            for d in t.dependencies:
                self.successors[d].add(i)
        self.user_masks = {v: sum(1 << i for i in ids) for v, ids in self.users.items()}
        return self

    def document(self):
        return dict(schema="workload-search-dag/1", name=self.name, config=self.config,
                    values=[asdict(v) for v in self.values.values()],
                    tasks=[asdict(t) for t in self.tasks])

    def digest(self):
        return hashlib.sha256(json.dumps(self.document(), sort_keys=True).encode()).hexdigest()


def transformer(prefill=128, decode=16, layers=1, rows=32, columns=128, tiny=False):
    """Selected layers; shape/operation workload, NOT Qwen numerical execution.

    Dimensions come from the pinned existing Qwen config. INT8 formats,
    fused GEMM-complete/RQ kernels, attention workspace and hardware pools are
    synthetic declarations. No intermediate K partial is independently RQ'd.
    KV is immutable append-only tile history, never reset between decode steps.
    """
    for x in (prefill, layers, rows, columns):
        if type(x) is not int or x <= 0:
            raise ValueError("positive integer dimensions required")
    if type(decode) is not int or decode < 0:
        raise ValueError("nonnegative decode required")
    h, inter, nq, nkv, hd = (8, 16, 2, 1, 4) if tiny else (1024, 3072, 16, 8, 128)
    if hd % columns or h % columns or inter % columns:
        raise ValueError("column tile must divide hidden, FFN and head dimensions")
    source = Path(__file__).parent.parent/"llm_resources/examples/qwen3_06b.json"
    config = dict(prefill=prefill, decode=decode, layers=layers, row_tile=rows,
                  column_tile=columns, hidden=h, intermediate=inter, q_heads=nq,
                  kv_heads=nkv, head_dim=hd, tiny=tiny,
                  config_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  source_commit="b06d85a801a87c07f9745ccae6950dc7e4cbd0d2",
                  evidence="config-derived shapes; synthetic quantization/kernels/resources; no real trace")
    w = Workload(f"p{prefill}-d{decode}-l{layers}-r{rows}-c{columns}", config)
    kv = [[] for _ in range(layers)]
    previous_decode = ()
    prefill_outputs = []
    batches = [(start, min(rows, prefill-start), "prefill") for start in range(0, prefill, rows)]
    batches += [(prefill+i, 1, "decode") for i in range(decode)]
    for position, count, phase in batches:
        if phase == "decode" and not previous_decode:
            previous_decode = tuple(prefill_outputs)
        tag = f"s{position}"
        x = [w.initial(f"input_{tag}_{j}", (count, columns)) for j in range(h//columns)]
        for layer in range(layers):
            stem = f"{tag}_L{layer}"
            after = previous_decode if phase == "decode" else ()

            def point(name, op, inputs, width, workspace=0):
                return w.add(stem+"_"+name, op, inputs, (count, width),
                             workspace=workspace, phase=phase, after=after)

            def linear(name, inputs, ins, outs):
                result = []
                for col in range(outs//columns):
                    weight = w.initial(f"W_L{layer}_{name}_{col}", (ins, columns), "weight")
                    scale = w.initial(f"scale_L{layer}_{name}_{col}", (columns,), "scale", 32)
                    result.append(w.add(stem+f"_{name}_{col}", "gemm_complete_rq", inputs+[weight,scale],
                        (count, columns), workspace=4*count*columns, macs=count*ins*columns,
                        pool="matrix", phase=phase, after=after))
                return result

            norm = point("norm1", "norm", x, h, 4*count*h)
            q = linear("q", [norm], h, nq*hd)
            k = linear("k", [norm], h, nkv*hd)
            v = linear("v", [norm], h, nkv*hd)
            # RoPE is explicit, preserving each head and feature tile.
            q = [point(f"ropeq_{j}", "rope", [a], columns, 4*count*columns) for j, a in enumerate(q)]
            k = [point(f"ropek_{j}", "rope", [a], columns, 4*count*columns) for j, a in enumerate(k)]
            kv[layer].append((position, count, k, v))
            context = []
            for head in range(nq):
                kh = head//(nq//nkv)
                pieces = hd//columns
                reads = q[head*pieces:(head+1)*pieces]
                for _, _, ks, vs in kv[layer]:
                    reads += ks[kh*pieces:(kh+1)*pieces]+vs[kh*pieces:(kh+1)*pieces]
                length = position+count
                # Includes score32, probability16 and output32 temporary buffers.
                workspace = 6*count*length+4*count*hd
                context.append(w.add(stem+f"_attention_h{head}", "causal_gqa", reads,
                    (count, hd), workspace=workspace, macs=2*count*length*hd,
                    phase=phase, after=after))
            out = linear("o", context, nq*hd, h)
            residual = point("residual1", "residual", x+out, h, 4*count*h)
            norm2 = point("norm2", "norm", [residual], h, 4*count*h)
            gate, up = linear("gate", [norm2], h, inter), linear("up", [norm2], h, inter)
            gated = [point(f"gateup_{j}", "silu_multiply", [a,b], columns, 8*count*columns)
                     for j, (a,b) in enumerate(zip(gate,up))]
            down = linear("down", gated, inter, h)
            x = [point("residual2", "residual", [residual]+down, h, 4*count*h)]
        if phase == "prefill":
            prefill_outputs.append(w.values[x[0]].producer)
        else:
            previous_decode = (w.values[x[0]].producer,)
    return w.freeze()


def trap():
    """Tiny cache/order counterexample, small enough for exact enumeration."""
    w = Workload("cache-trap", dict(evidence="synthetic exact-search fixture"))
    a=w.initial("A", (512,), "weight")
    b=w.initial("B", (256,), "weight")
    c=w.initial("C", (256,), "weight")
    o=w.add("seed", "gemm_complete_rq", [a], (64,), pool="matrix")
    w.add("small", "gemm_complete_rq", [o,b], (64,), pool="matrix")
    w.add("reuse", "gemm_complete_rq", [o,a,c], (64,), pool="matrix")
    return w.freeze()
