"""Compile the Llama 3.2 dense decoder with padded 64-dimensional attention."""
import json
from math import sqrt
from struct import pack

import numpy as np
from safetensors import safe_open

from qwen3_short_plan import (
    ACT, ATT1, BASE_ABI, CONTEXT, MID, P, ROTARY, U, VECTOR, Compiler, Layout, align, seal,
)


class LlamaCompiler(Compiler):
    hidden, vocab, token_word = 2048, 128256, 512
    model_type, head_size, heads, kv_heads, ffn = "llama", 64, 32, 8, 8192

    def __init__(self, checkpoint, packed, reference, output, layers, history, mode):
        self.layout = Layout(output)
        config = json.loads((checkpoint / "config.json").read_text())
        if (config["model_type"], config["hidden_size"], config["head_dim"], config["num_attention_heads"],
                config["num_key_value_heads"], config["intermediate_size"], config["vocab_size"]) != (
                self.model_type, self.hidden, self.head_size, self.heads, self.kv_heads, self.ffn, self.vocab):
            raise ValueError("unexpected frozen Llama configuration")
        self.weight_file, = checkpoint.glob("*.safetensors")
        self.config = config
        self.rope_args = config["rope_scaling"]
        self.theta = config["rope_theta"]
        self.eps = round(config["rms_norm_eps"] * 2**32)
        self.layers, self.history, self.mode = layers, history, mode
        self.positions = [history, history + 1]
        self.kv_bytes = align((history + 2) * 512, 4096)
        self.calls, self.gamma = [], {}
        self.records = {}
        self.input_ids = json.loads((reference / "input-ids.json").read_text())
        self.reference = json.loads((reference / "reference.json").read_text())
        asset = json.loads((packed / "receipt.json").read_text())
        embedding = asset["tensors"]["embedding"]
        base = self.layout.file(packed / embedding["file"], expected=embedding["sha256"])
        self.prompt = self.layout.write("prompt.bin", pack("<2i", *self.input_ids[:2]))
        self.add_embedding = seal(3, 4, VECTOR, "<QIHHHH", base, self.vocab,
                                  self.token_word*16, 0, 32, self.hidden*4)
        for name, tensor in asset["tensors"].items():
            if name == "embedding" or name == "head" and mode != "decode":
                continue
            if name != "head" and int(name.split(".")[2]) >= layers:
                continue
            actual = "model.embed_tokens.weight" if name == "head" else name
            if tensor["shape"] != tensor["padded_shape"]:
                raise ValueError("unexpected padded projection weight")
            self.records[actual] = (self.layout.file(packed / tensor["file"], expected=tensor["sha256"]),
                                    *tensor["shape"])

    def vector(self, name):
        with safe_open(self.weight_file, framework="pt", device="cpu") as source:
            return source.get_tensor(name).float().numpy()

    def coefficients(self, position):
        base = self.theta ** (-np.arange(0, 64, 2) / 64)
        c = self.rope_args
        wavelength = 2 * np.pi / base
        context = c["original_max_position_embeddings"]
        high, low = c["high_freq_factor"], c["low_freq_factor"]
        scale = np.clip((context / wavelength - low) / (high - low), 0, 1)
        inv = base * (scale + (1-scale)/c["factor"])
        angle = np.tile(position*inv, 2)
        coeff = [np.rint(f(angle)*16384).astype("<i4").tobytes() for f in (np.cos, np.sin)]
        return self.layout.write(f"rope-{position}.bin", b"".join(coeff))

    def rotary64(self, source):
        self.append(P, seal(ROTARY, 1, VECTOR, "<5H", source, 256, 272, 320, 16))

    def layer(self, layer, position, coeff):
        pre = f"model.layers.{layer}."
        self.rms(U, pre+"input_layernorm.weight", 0, 512, 512)
        self.load(P, coeff, 256, 32)
        for head in range(8):
            k, v = self.kv(layer, head, 0), self.kv(layer, head, 1)
            lo, hi = head*64, (head+1)*64
            self.project(pre+"self_attn.k_proj.weight", 160, lo, hi)
            self.rotary64(160)
            self.store(P, k+position*512, 320, 32)
            self.project(pre+"self_attn.v_proj.weight", 192, lo, hi)
            self.append(P, seal(ROTARY, 2, VECTOR, "<2H", 192, 320))
            self.store(P, v+position*512, 320, 32)
            for q in range(4*head, 4*head+4):
                self.project(pre+"self_attn.q_proj.weight", 128, q*64, (q+1)*64)
                self.rotary64(128)
                self.append(P, seal(ATT1, 1, BASE_ABI, "<6HIQQ", position+1, position, 320,
                                    384, 544, 832, round(2**30/sqrt(64)), k, v))
                self.copy(P, CONTEXT, 832, q*16, 16)
        self.project(pre+"self_attn.o_proj.weight", 0, route=1)
        self.copy(P, U, 0, 512, 512)
        self.add(0, 512, 0, 512)
        self.rms(U, pre+"post_attention_layernorm.weight", 0, 512, 512)
        # Place two 4096-wide Mid fragments in separate 16KiB stores.
        for first in range(0, 8192, 128):
            self.project(pre+"mlp.gate_proj.weight", 0, first, first+128)
            self.project(pre+"mlp.up_proj.weight", 32, first, first+128)
            self.append(P, seal(ACT, 1, VECTOR, "<3H", 0, 32, 64))
            self.copy(P, CONTEXT if first < 4096 else MID, 64, (first%4096)//4, 32)
        self.project(pre+"mlp.down_proj.weight", 0, route=3)
        self.copy(P, U, 0, 512, 512)
        self.add(0, 512, 0, 512)
