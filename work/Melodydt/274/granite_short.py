"""Granite MoE short inference with token-dependent, timed expert weight fetches."""
from struct import pack, unpack, unpack_from

import numpy as np
from native_tlm_u import rne

from phi_short_plan import PhiCompiler
from qwen3_short_plan import (
    ACT, CONTEXT, COPY, ELEMENT, KV_START, MID, MOE, P, RESIDUAL,
    U, VECTOR, projection_record, seal,
)


class GraniteCompiler(PhiCompiler):
    model_type, hidden, head_size, heads, kv_heads, ffn, vocab = "granitemoe", 1536, 64, 24, 8, 512, 49155
    token_word = 960

    def compile(self):
        plan = super().compile()
        plan["moe"] = True
        plan["logits_scale_q16"] = round(65536/self.config["logits_scaling"])
        return plan

    def coefficients(self, position):
        base = self.config["rope_theta"]**(-np.arange(0, 64, 2)/64)
        angles = np.tile(position*base, 2)
        return self.layout.write(f"rope-{position}.bin", b"".join(
            np.rint(f(angles)*16384).astype("<i4").tobytes() for f in (np.cos, np.sin)))

    def kv(self, layer, head, kind):
        return KV_START + ((layer*self.kv_heads+head)*2+kind)*self.kv_bytes

    def ingress(self):
        scale = round(self.config["embedding_multiplier"]*65536)
        self.append(U, seal(ELEMENT, 1, VECTOR, "<HI", self.hidden//4, scale))

    def normalize(self, name):
        self.rms(U, name, 0, self.hidden//4, self.hidden//4)

    def residual(self):
        gain = round(self.config["residual_multiplier"]*65536)
        self.append(U, seal(RESIDUAL, 3, VECTOR, "<3HI", 0, 0, self.hidden//4, gain))

    def layer(self, layer, position, coeff):
        pre = f"model.layers.{layer}."
        self.normalize(pre+"input_layernorm.weight")
        self.load(P, coeff, 256, 32)
        for head in range(self.kv_heads):
            k, v = self.kv(layer, head, 0), self.kv(layer, head, 1)
            lo, hi = head*64, (head+1)*64
            self.project(pre+"self_attn.k_proj.weight", 160, lo, hi)
            self.cache_k64(k, position)
            self.project(pre+"self_attn.v_proj.weight", 192, lo, hi)
            self.cache_v64(v, position)
            for q in range(3*head, 3*head+3):
                self.project(pre+"self_attn.q_proj.weight", 128, q*64, (q+1)*64)
                self.attend64(position, round(2**30*self.config["attention_multiplier"]), k, v)
                self.copy(P, CONTEXT, 832, q*16, 16)
        self.project(pre+"self_attn.o_proj.weight", 0, route=1)
        self.residual()
        self.normalize(pre+"post_attention_layernorm.weight")
        moe = pre+"block_sparse_moe."
        self.project(moe+"router.layer.weight", 0)
        table = b"".join(pack("<QQ", *(self.records[moe+f"{name}.weight.expert{expert:02d}"][0]
                                        for name in ("input_linear", "output_linear")))
                         for expert in range(40))
        address = self.layout.write(f"experts-{position}-{layer}.bin", table)
        self.load(P, address, 64, 40)
        self.append(P, seal(MOE, 1, VECTOR, "<4H", position, layer, 40, 8))
        self.residual()


class Router:
    def __init__(self, execution, activation):
        self.execution = execution
        self.ram = execution.sram
        self.proj = execution.proj
        self.activate = activation

    def bind(self, record):
        position, layer, experts, top = unpack_from("<4H", record, 16)
        if (experts, top) != (40, 8) or any(record[24:124]):
            raise ValueError("invalid Granite MoE descriptor")
        unit, target = self.proj[0], self.ram[P]
        partial_words = 384

        def run(done):
            def route(raw, table):
                scores = np.frombuffer(raw, dtype="<i4").astype(np.float64)
                chosen = np.lexsort((np.arange(experts), -scores))[:top]
                coeff = np.exp((scores[chosen]-scores[chosen[0]])/65536)
                p = np.rint(coeff/coeff.sum()*65536).astype(np.int64)
                self.execution.experts.append({"position": position, "layer": layer,
                                               "ids": chosen.tolist(), "probabilities_q16": p.tolist()})
                ordered = sorted(zip(chosen.tolist(), p.tolist()))
                unit.edge(lambda: expert(ordered, table, 0), 160)

            def expert(ordered, table, index):
                if index == len(ordered):
                    unit.read_span(self.ram[CONTEXT], 0, partial_words,
                                   lambda values: unit.write_span(target, 0, values, done))
                    return
                identifier, probability = ordered[index]
                left, right = unpack_from("<QQ", table, 16*identifier)

                def activated(tile):
                    if tile == 4:
                        down(0)
                        return
                    gate = projection_record(left, 1024, 1536, tile*128, 16, 0)
                    up = projection_record(left, 1024, 1536, 512+tile*128, 16, 32)
                    g = seal(ACT, 1, VECTOR, "<3H", 0, 32, 64)
                    transfer = seal(COPY, 1, VECTOR, "<B3H", P, 64, tile*32, 32)
                    unit.provider(gate)(lambda: unit.provider(up)(lambda: self.activate(g)(
                        lambda: self.execution.providers[MID, COPY, VECTOR, 1](transfer)(
                            lambda: activated(tile+1)))))

                def down(tile):
                    if tile == 12:
                        expert(ordered, table, index+1)
                        return
                    op = projection_record(right, 1536, 512, tile*128, 16, 0, route=2)
                    engine = self.proj[2]

                    def add(raw):
                        new = np.frombuffer(raw, dtype="<i4").tolist()

                        def write(old):
                            data = pack("<128i", *(a+rne(b*probability, 16) for a,b in
                                                   zip(unpack("<128i", old), new)))
                            unit.edge(lambda: unit.write_span(self.ram[CONTEXT], tile*32, data,
                                                             lambda: down(tile+1)), 96)
                        if index == 0:
                            write(bytes(512))
                        else:
                            unit.read_span(self.ram[CONTEXT], tile*32, 32, write)

                    engine.provider(op)(lambda: unit.read_span(target, 0, 32, add))

                activated(0)

            unit.read_span(target, 0, 10, lambda scores:
                           unit.read_span(target, 64, 40, lambda table: route(scores, table)))
        return run
