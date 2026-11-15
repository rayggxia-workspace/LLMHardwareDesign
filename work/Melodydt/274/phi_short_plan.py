"""Translate the Phi-4-mini fused dense matrices and LongRoPE into short MC pages."""
import json
from math import log, sqrt
from struct import pack

import numpy as np
from safetensors import safe_open

from llama_short_plan import LlamaCompiler
from qwen3_short_plan import (
    ACT, ATT1, BASE_ABI, CONTEXT, MID, P, RESIDUAL, ROTARY, U, VECTOR,
    Layout, align, seal,
)


class PhiCompiler(LlamaCompiler):
    model_type, hidden, head_size, heads, kv_heads, ffn, vocab = "phi3", 3072, 128, 24, 8, 8192, 200064
    token_word = 960
    immutable_end = 1 << 33
    ffn_context_cache = False

    def __init__(self, checkpoint, packed, reference, output, layers, history, mode):
        self.layout = Layout(output, self.immutable_end)
        config = json.loads((checkpoint / "config.json").read_text())
        config = config.get("text_config", config)
        if (config["model_type"], config["hidden_size"], config.get("num_attention_heads", self.heads),
                config.get("num_key_value_heads", self.kv_heads), config["intermediate_size"],
                config.get("vocab_size", self.vocab)) != (
                self.model_type, self.hidden, self.heads, self.kv_heads, self.ffn, self.vocab):
            raise ValueError("unexpected frozen Phi configuration")
        self.weight_files = sorted(checkpoint.glob("*.safetensors"))
        self.config = config
        self.eps = round(config.get("rms_norm_eps", 1e-6) * 2**32)
        self.layers, self.history, self.mode = layers, history, mode
        self.positions = [history, history+1]
        self.kv_bytes = align((history+2)*512, 4096)
        self.calls, self.gamma, self.records = [], {}, {}
        self.scratch_regions = []
        self.input_ids = json.loads((reference / "input-ids.json").read_text())
        self.reference = json.loads((reference / "reference.json").read_text())
        asset = json.loads((packed / "receipt.json").read_text())
        embedding = asset["tensors"]["embedding"]
        if embedding["shape"] != [self.vocab, self.hidden]:
            raise ValueError("embedding shape differs from the frozen text configuration")
        base = self.layout.file(packed / embedding["file"], expected=embedding["sha256"])
        self.prompt = self.layout.write("prompt.bin", pack("<2i", *self.input_ids[:2]))
        self.add_embedding = seal(3, 4, VECTOR, "<QIHHHH", base, self.vocab,
                                  self.token_word*16, 0, 32, self.hidden*4)
        for name, tensor in asset["tensors"].items():
            if name == "embedding" or name == "head" and mode != "decode":
                continue
            if name != "head":
                layer = int(name.split(".layers.", 1)[1].split(".", 1)[0])
                if layer >= layers or name.startswith("mtp."):
                    continue
            actual = "model.embed_tokens.weight" if name == "head" else name
            self.records[actual] = (self.layout.file(packed / tensor["file"], expected=tensor["sha256"]),
                                    *tensor["padded_shape"])

    def vector(self, name):
        for file in self.weight_files:
            with safe_open(file, framework="pt", device="cpu") as source:
                if name in source.keys():
                    return source.get_tensor(name).float().numpy()
        raise ValueError(f"missing vector {name}")

    def norm_from(self, source, name):
        if name not in self.gamma:
            gamma = self.vector(name)
            self.gamma[name] = self.layout.write("gamma-"+name+".bin",
                                                 np.rint(gamma*65536).astype("<i4").tobytes())
        self.copy(source, MID, 0, 0, self.hidden//4)
        self.load(CONTEXT, self.gamma[name], 0, self.hidden//4)
        self.append(MID, seal(3, 5, VECTOR, "<4HI", 0, 0, 0, self.hidden//4, self.eps))

    def coefficients(self, position):
        c = self.config
        old = c["original_max_position_embeddings"]
        if position >= old:
            raise ValueError("short case crossed the LongRoPE short boundary")
        factors = np.asarray(c["rope_scaling"]["short_factor"])
        dim = factors.size*2
        base = c["rope_theta"]**(-np.arange(0, dim, 2)/dim)
        angle = np.tile(position*base/factors, 2)
        amplitude = sqrt(1+log(c["max_position_embeddings"]/old)/log(old))
        data = [np.rint(f(angle)*amplitude*16384).astype("<i4").tobytes()
                for f in (np.cos, np.sin)]
        return self.layout.write(f"rope-{position}.bin", b"".join(
            np.pad(np.frombuffer(p, dtype="<i4"), (0, 128-dim)).astype("<i4").tobytes()
            for p in data))

    def rotate(self, word):
        dim = len(self.config["rope_scaling"]["short_factor"])*2
        self.append(P, seal(ROTARY, 3, VECTOR, "<5H", word, 256, 288, 320, dim))

    def normalize(self, name):
        self.norm_from(U, name)

    def final_norm(self):
        self.normalize("model.norm.weight")

    def residual(self):
        self.append(U, seal(RESIDUAL, 1, VECTOR, "<3H", 0, 0, self.hidden//4))

    def allocate_mid(self, layer, position):
        size = self.ffn * 4
        self.mid_buffer = (3 << 32) + ((position-self.history)*self.layers+layer)*size
        self.scratch_regions.append((self.mid_buffer, size))

    def store_mid_tile(self, first):
        if self.ffn_context_cache and first < 4096:
            self.copy(P, CONTEXT, 64, first//4, 32)
        else:
            self.store(P, self.mid_buffer + first*4, 64, 32)

    def project_spilled_mid(self, tensor):
        self.project(tensor, 0, route=5 if self.ffn_context_cache else 4, backing=self.mid_buffer)

    def layer(self, layer, position, coeff):
        pre = f"model.layers.{layer}."
        self.allocate_mid(layer, position)
        self.normalize(pre+"input_layernorm.weight")
        self.load(P, coeff, 256, 64)
        qkv = pre+"self_attn.qkv_proj.weight"
        # Persist each head's 128-wide AV result in a separate S store.
        for head in range(8):
            k, v = self.kv(layer, head, 0), self.kv(layer, head, 1)
            lo, hi = head*128, (head+1)*128
            self.project(qkv, 160, 3072+lo, 3072+hi)
            self.rotate(160)
            self.store(P, k+position*512, 320, 32)
            self.project(qkv, 192, 4096+lo, 4096+hi)
            self.store(P, v+position*512, 192, 32)
            for q in range(3*head, 3*head+3):
                self.project(qkv, 128, q*128, (q+1)*128)
                self.rotate(128)
                self.append(P, seal(ATT1, 1, BASE_ABI, "<6HIQQ", position+1, position, 320,
                                    384, 544, 832, round(2**30/sqrt(128)), k, v))
                self.copy(P, CONTEXT, 832, q*32, 32)
        self.project(pre+"self_attn.o_proj.weight", 0, route=1)
        self.residual()
        self.normalize(pre+"post_attention_layernorm.weight")
        fused = pre+"mlp.gate_up_proj.weight"
        for first in range(0, self.ffn, 128):
            self.project(fused, 0, first, first+128)
            self.project(fused, 32, self.ffn+first, self.ffn+first+128)
            self.append(P, seal(ACT, 1, VECTOR, "<3H", 0, 32, 64))
            self.store_mid_tile(first)
        self.project_spilled_mid(pre+"mlp.down_proj.weight")
        self.residual()
