"""Compile Gemma-3 text short runs with layer-specific RoPE and exact mask extent."""
from math import sqrt

import numpy as np

from phi_short_plan import PhiCompiler
from qwen3_short_plan import (
    ACT, ATT_WIDE, CONTEXT, ELEMENT, KV_START, MID, P, RESIDUAL, ROTARY, U, VECTOR, align, seal,
)


class GemmaCompiler(PhiCompiler):
    model_type, hidden, head_size, heads, kv_heads, ffn, vocab = "gemma3_text", 2560, 256, 8, 4, 10240, 262208
    token_word = 960
    kv_row = 1024
    residual_fraction_bits = 16

    def __init__(self, *args):
        super().__init__(*args)
        self.kv_bytes = align((self.history+2)*self.kv_row, 4096)
        self.local = "sliding_attention"
        self.global_kind = "full_attention"

    def vector(self, name):
        return super().vector(name)+1.0

    def coefficients(self, position):
        tables = {}
        variants = self.config.get("rope_parameters")
        if variants is None:
            variants = {
                self.local: {"rope_theta": self.config.get("rope_local_base_freq", 10000.0),
                             "factor": 1.0},
                self.global_kind: {"rope_theta": 1000000.0, "factor": self.config["rope_scaling"]["factor"]},
            }
        for kind in (self.local, self.global_kind):
            params = variants[kind]
            inv = params["rope_theta"] ** (-np.arange(0, 256, 2)/256)
            angle = np.tile(position*inv / params.get("factor", 1.0), 2)
            payload = b"".join(np.rint(x(angle)*16384).astype("<i4").tobytes() for x in (np.cos, np.sin))
            tables[kind] = self.layout.write(f"rope-{position}-{kind}.bin", payload)
        return tables

    def kv(self, layer, head, kind):
        return KV_START+((layer*self.kv_heads+head)*2+kind)*self.kv_bytes

    def ingress(self):
        self.append(U, seal(ELEMENT, 1, VECTOR, "<HI", self.hidden//4,
                            round(sqrt(self.hidden)*(1 << self.residual_fraction_bits))))

    def normalize(self, name):
        self.norm_from(U, name, input_shift=16-self.residual_fraction_bits)

    def final_norm(self):
        self.normalize("language_model.model.norm.weight")

    def rotate(self, word):
        self.append(P, seal(ROTARY, 3, VECTOR, "<5H", word, 704, 768, 320, 256))

    def layer(self, layer, position, coeff):
        pre = f"language_model.model.layers.{layer}."
        widths = self.hidden//4
        self.normalize(pre+"input_layernorm.weight")
        kinds = self.config.get("layer_types")
        kind = kinds[layer] if kinds is not None else (
            self.global_kind if (layer+1) % self.config.get("sliding_window_pattern", 6) == 0 else self.local)
        self.load(P, coeff[kind], 704, 128)
        if kind == self.local and position >= self.config["sliding_window"]:
            raise ValueError("sliding eviction needs a circular KV layout outside this short case")
        factor = round(2**30 / sqrt(self.config.get("query_pre_attn_scalar", 256)))
        for head in range(self.kv_heads):
            k, v = self.kv(layer, head, 0), self.kv(layer, head, 1)
            lo, hi = head*256, (head+1)*256
            self.project(pre+"self_attn.k_proj.weight", 128, lo, hi)
            self.rms(P, pre+"self_attn.k_norm.weight", 128, 128, 64)
            self.rotate(128)
            self.store(P, k+position*1024, 320, 64)
            self.project(pre+"self_attn.v_proj.weight", 128, lo, hi)
            self.store(P, v+position*1024, 128, 64)
            for q in (head*2, head*2+1):
                self.project(pre+"self_attn.q_proj.weight", 128, q*256, (q+1)*256)
                self.rms(P, pre+"self_attn.q_norm.weight", 128, 128, 64)
                self.rotate(128)
                self.append(P, seal(ATT_WIDE, 1, VECTOR, "<4HIQQ", position+1, 256, 320, 832, factor, k, v))
                # Attention workspace can overwrite RoPE; reload it before the next head.
                self.copy(P, CONTEXT, 832, q*64, 64)
                self.load(P, coeff[kind], 704, 128)
        self.project(pre+"self_attn.o_proj.weight", 0, route=1)
        self.norm_from(P, pre+"post_attention_layernorm.weight")
        self.append(U, seal(RESIDUAL, 4, VECTOR, "<3H", 0, 0, widths))
        self.normalize(pre+"pre_feedforward_layernorm.weight")
        if self.three_p:
            self.three_p_ffn(pre+"mlp.gate_proj.weight", pre+"mlp.up_proj.weight",
                             pre+"mlp.down_proj.weight", self.ffn, layer, position, opcode=2)
        else:
            self.allocate_mid(layer, position)
            for first in range(0, self.ffn, 128):
                self.project(pre+"mlp.gate_proj.weight", 0, first, first+128)
                self.project(pre+"mlp.up_proj.weight", 32, first, first+128)
                self.append(P, seal(ACT, 2, VECTOR, "<3H", 0, 32, 64))
                self.store_mid_tile(first)
            self.project_spilled_mid(pre+"mlp.down_proj.weight")
        self.norm_from(P, pre+"post_feedforward_layernorm.weight")
        self.append(U, seal(RESIDUAL, 4, VECTOR, "<3H", 0, 0, widths))
