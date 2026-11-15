"""Compile Qwen3.5 GDN and Falcon-H1 Mamba2 with callback-backed state."""
from math import sqrt
from struct import unpack_from

import numpy as np
from native_tlm_timing import Transfer

from phi_short_plan import PhiCompiler
from qwen3_short_plan import (
    ACT, ATT1, ATT_WIDE, BASE_ABI, CONTEXT, ELEMENT, P, RECURRENT, RESIDUAL,
    ROTARY, U, VECTOR, align, seal,
)

MIX, FFN, HISTORY = 13 << 30, (13 << 30) + (1 << 26), 14 << 30
VEC = 4096


def q16(x):
    return np.rint(np.asarray(x)*65536).clip(-(1 << 31), (1 << 31)-1).astype("<i4").tobytes()


def floats(payload):
    return np.frombuffer(payload, dtype="<i4").astype(np.float32)/65536


def sigmoid(x):
    return 1/(1+np.exp(-np.clip(x, -64, 64)))


def silu(x):
    return x*sigmoid(x)


class HybridCompiler(PhiCompiler):
    immutable_end = 12 << 30

    def __init__(self, *args):
        super().__init__(*args)
        self.initial = []
        self.rec = []

    def kv(self, layer, head, kind):
        return self.immutable_end + ((layer*self.kv_heads+head)*2+kind)*self.kv_bytes

    def compile(self):
        out = super().compile()
        out.update(recurrent=True, recurrent_regions=self.rec, initial=self.initial)
        return out

    def scale_p(self, start, words, gain):
        self.append(P, seal(ELEMENT, 2, VECTOR, "<HIH", words, round(gain*65536), start))

    def residual_gain(self, gain):
        self.append(U, seal(RESIDUAL, 3, VECTOR, "<3HI", 0, 0, self.hidden//4, round(gain*65536)))

    def dense_ffn(self, prefix, layer, position, gate_gain=1., out_gain=1.):
        if self.three_p:
            self.three_p_ffn(prefix+"gate_proj.weight", prefix+"up_proj.weight",
                             prefix+"down_proj.weight", self.ffn, layer, position, opcode=4, gain=gate_gain)
            self.residual_gain(out_gain)
            return
        size = self.ffn*4
        base = FFN + ((position-self.history)*self.layers+layer)*size
        self.mid_buffer = base
        self.scratch_regions.append((base, size))
        for first in range(0, self.ffn, 128):
            self.project(prefix+"gate_proj.weight", 0, first, first+128)
            self.project(prefix+"up_proj.weight", 32, first, first+128)
            self.append(P, seal(ACT, 4, VECTOR, "<3HI", 0, 32, 64, round(gate_gain*65536)))
            self.store_mid_tile(first)
        self.project_spilled_mid(prefix+"down_proj.weight")
        self.residual_gain(out_gain)

    def spill_projection(self, tensor, address, count, gain=1.):
        for first in range(0, count, 128):
            end = min(count, first+128)
            self.project(tensor, 0, first, end)
            if gain != 1:
                self.scale_p(0, (end-first)//4, gain)
            self.store(P, address+first*4, 0, (end-first)//4)

    def recurrent(self, prefix, layer, position, mode):
        step = position-self.history
        channels = 8192 if mode == 1 else 4608
        depth = 128 if mode == 1 else 256
        linear = channels+VEC+64 if mode == 1 else channels+VEC+32
        state = 32*128*depth*4 + channels*4*4
        before = HISTORY + layer*(3 << 23) + step*state
        after = before+state
        received = MIX + ((step*self.layers+layer) << 16)
        self.scratch_regions.extend(((after, state), (received, linear*4)))
        if not step:
            self.initial.append((before, state))
        self.rec.append((step, after, state))
        if mode == 1:
            for name, offset, count in (("qkv", 0, 8192), ("z", 8192, VEC),
                                        ("a", 8192+VEC, 32), ("b", 8192+VEC+32, 32)):
                self.spill_projection(prefix+f"in_proj_{name}.weight", received+offset*4, count)
            names = ("conv1d.weight", "A_log", "dt_bias", "norm.weight")
        else:
            self.spill_projection(prefix+"in_proj.weight", received, linear)
            names = ("conv1d.weight", "conv1d.bias", "A_log", "dt_bias", "D", "norm.weight")
        parameters = self.layout.write(f"recurrent-{position}-{layer}.bin", b"".join(
            q16(self.vector(prefix+name)) for name in names))
        epsilon = round(self.config.get("rms_norm_eps", 1e-6)*2**32)
        self.append(P, seal(RECURRENT, 1, VECTOR, "<HHI4Q", mode, position, epsilon,
                            received, before, after, parameters))
        self.project(prefix+"out_proj.weight", 0, route=1)


class Qwen35Compiler(HybridCompiler):
    model_type, hidden, head_size, heads, kv_heads, ffn, vocab = "qwen3_5_text", 2560, 256, 16, 4, 9216, 248320
    kv_row = 1024

    def __init__(self, *args):
        super().__init__(*args)
        self.kv_bytes = align((self.history+2)*self.kv_row, 4096)

    def has_kv(self, layer):
        return self.config["layer_types"][layer] == "full_attention"

    def vector(self, name):
        data = super().vector(name)
        return data+1 if ".linear_attn." not in name else data

    def final_norm(self):
        self.normalize("model.language_model.norm.weight")

    def coefficients(self, position):
        base = self.config["rope_parameters"]["rope_theta"]**(-np.arange(0, 64, 2)/64)
        angle = np.pad(np.tile(position*base, 2), (0, 192))
        return self.layout.write(f"rope-{position}.bin", q16(np.cos(angle)/4)+q16(np.sin(angle)/4))

    def layer(self, layer, position, coeff):
        pre = f"model.language_model.layers.{layer}."
        self.normalize(pre+"input_layernorm.weight")
        if self.has_kv(layer):
            self.attention(pre+"self_attn.", layer, position, coeff)
        else:
            self.recurrent(pre+"linear_attn.", layer, position, 1)
        self.residual_gain(1.)
        self.normalize(pre+"post_attention_layernorm.weight")
        self.dense_ffn(pre+"mlp.", layer, position)

    def attention(self, pre, layer, position, coefficient):
        def rotate():
            self.load(P, coefficient, 704, 128)
            self.append(P, seal(ROTARY, 4, VECTOR, "<5H", 128, 704, 768, 320, 64))

        for i in range(self.kv_heads):
            k, v = self.kv(layer, i, 0), self.kv(layer, i, 1)
            lo = i*256
            self.project(pre+"k_proj.weight", 128, lo, lo+256)
            self.rms(P, pre+"k_norm.weight", 128, 128, 64)
            rotate()
            self.store(P, k+position*1024, 320, 64)
            self.project(pre+"v_proj.weight", 128, lo, lo+256)
            self.store(P, v+position*1024, 128, 64)
            for head in range(4*i, 4*i+4):
                lo = head*512
                self.project(pre+"q_proj.weight", 128, lo, lo+256)
                self.rms(P, pre+"q_norm.weight", 128, 128, 64)
                rotate()
                self.append(P, seal(ATT_WIDE, 1, VECTOR, "<4HIQQ", position+1, 256, 320, 832, 1 << 26, k, v))
                self.project(pre+"q_proj.weight", 0, lo+256, lo+512)
                self.append(P, seal(ACT, 3, VECTOR, "<3H", 0, 832, 128))
                self.copy(P, CONTEXT, 128, head*64, 64)
        self.project(pre+"o_proj.weight", 0, route=1)


class FalconCompiler(HybridCompiler):
    model_type, hidden, head_size, heads, kv_heads, ffn, vocab = "falcon_h1", 2560, 128, 10, 2, 6144, 65537

    def compile(self):
        out = super().compile()
        out["logits_scale_q16"] = round(self.config["lm_head_multiplier"]*65536)
        out["falcon_multipliers"] = self.config["ssm_multipliers"]
        out["falcon_input_scale"] = self.config["ssm_in_multiplier"]
        return out

    def ingress(self):
        self.append(U, seal(ELEMENT, 1, VECTOR, "<HI", self.hidden//4,
                            round(self.config["embedding_multiplier"]*65536)))

    def final_norm(self):
        self.normalize("model.final_layernorm.weight")

    def coefficients(self, position):
        base = self.config["rope_theta"]**(-np.arange(0, 128, 2)/128)
        angle = np.tile(position*base, 2)
        return self.layout.write(f"rope-{position}.bin", q16(np.cos(angle)/4)+q16(np.sin(angle)/4))

    def layer(self, layer, position, coeff):
        root = f"model.layers.{layer}."
        self.normalize(root+"input_layernorm.weight")
        self.recurrent(root+"mamba.", layer, position, 2)
        self.residual_gain(self.config["ssm_out_multiplier"])
        pre = root+"self_attn."
        self.load(P, coeff, 256, 64)
        for i in range(self.kv_heads):
            k, v = self.kv(layer, i, 0), self.kv(layer, i, 1)
            lo = i*128
            self.project(pre+"k_proj.weight", 160, lo, lo+128)
            self.scale_p(160, 32, self.config["key_multiplier"])
            self.rope(160)
            self.store(P, k+position*512, 320, 32)
            self.project(pre+"v_proj.weight", 192, lo, lo+128)
            self.store(P, v+position*512, 192, 32)
            for head in range(5*i, 5*i+5):
                self.project(pre+"q_proj.weight", 128, head*128, head*128+128)
                self.rope(128)
                self.append(P, seal(ATT1, 1, BASE_ABI, "<6HIQQ", position+1, position, 320,
                                    384, 544, 832, round(2**30/sqrt(128)), k, v))
                self.copy(P, CONTEXT, 832, head*32, 32)
        self.project(pre+"o_proj.weight", 0, route=1)
        self.residual_gain(self.config["attention_out_multiplier"])
        self.normalize(root+"pre_ff_layernorm.weight")
        self.dense_ffn(root+"feed_forward.", layer, position, *self.config["mlp_multipliers"])


class Recurrent:
    def __init__(self, execution):
        self.execution = execution
        self.unit = execution.proj[0]
        self.context = execution.sram[CONTEXT]

    def transfer(self, base, size, done, payload=None):
        """Stream a 64-byte DDR window with eight outstanding transactions."""
        memory, dram = self.execution.memory, self.execution.dram
        sent = returned = 0
        received = bytearray(size) if payload is None else None

        def pump():
            nonlocal sent
            while sent < size and sent-returned < 512:
                offset = sent
                sent += 64
                address = base+offset
                chunk = None if payload is None else payload[offset:offset+64]
                commit = None if chunk is None else memory.begin_write(address, address//64, chunk)
                trans = Transfer(address) if commit is None else Transfer(address, chunk)
                dram.submit(trans, lambda a=address,o=offset,c=commit: callback(a,o,c), channel=1)

        def callback(address, offset, commit):
            nonlocal returned
            if commit is None:
                received[offset:offset+64] = memory(address)
            else:
                commit()
            returned += 64
            if returned == size:
                done(received)
            else:
                pump()

        pump()

    def bind(self, record):
        mode, _, epsilon, source, before, after, params = unpack_from("<HHI4Q", record, 16)
        if mode not in (1, 2) or any(record[56:124]) or (source | before | after | params) % 64:
            raise ValueError("invalid recurrent service descriptor")
        gdn = mode == 1
        channels = 8192 if gdn else 4608
        depth = 128 if gdn else 256
        linear = channels+VEC+(64 if gdn else 32)
        state_bytes = 32*128*depth*4
        param_count = channels*4+192 if gdn else channels*5+96+VEC
        eps = epsilon/2**32

        def run(done):
            def parameters(raw):
                flat = floats(raw)
                conv = flat[:channels*4].reshape(channels, 4)
                if gdn:
                    bias = 0
                    a_log, dt_bias, gamma = np.split(flat[channels*4:param_count], [32, 64])
                    skip = None
                else:
                    bias = flat[channels*4:channels*5]
                    a_log, dt_bias, skip, gamma = np.split(flat[channels*5:param_count], [32, 64, 96])
                self.transfer(source, linear*4,
                              lambda data: inputs(floats(data), conv, bias, a_log, dt_bias, skip, gamma))

            def inputs(linear_values, conv, bias, a_log, dt_bias, skip, gamma):
                if gdn:
                    x, z, a, b = np.split(linear_values, [channels, channels+VEC, channels+VEC+32])
                    beta = sigmoid(b)
                    delta = np.logaddexp(0, a+dt_bias)
                else:
                    z, x, a = np.split(linear_values, [VEC, VEC+channels])
                    zp,xp,bp,cp,dp = self.execution.plan["falcon_multipliers"]
                    multiplier = self.execution.plan["falcon_input_scale"]
                    z *= zp*multiplier
                    x *= multiplier
                    x[:VEC] *= xp
                    x[VEC:VEC+256] *= bp
                    x[VEC+256:] *= cp
                    delta = np.logaddexp(0, a*dp*multiplier+dt_bias)
                    beta = None
                decay = np.exp(-np.exp(a_log)*delta)
                mixed = np.empty(channels, dtype=np.float32)
                out = np.empty(VEC, dtype=np.float32)

                def convolution(first):
                    if first == channels:
                        prepare_heads()
                        return
                    count = min(128, channels-first)
                    old = before+state_bytes+first*16
                    new = after+state_bytes+first*16

                    def loaded(payload):
                        window = floats(payload).reshape(count, 4)
                        window = np.column_stack([window[:, 1:], x[first:first+count]])
                        mixed[first:first+count] = np.sum(window*conv[first:first+count], axis=-1)
                        self.unit.edge(lambda: self.transfer(new, count*16,
                            lambda _: convolution(first+count), q16(window)), count*2)

                    self.transfer(old, count*16, loaded)

                def prepare_heads():
                    keys = silu(mixed+bias)
                    if gdn:
                        query, key, value = np.split(keys, [2048, 4096])
                        query, key = query.reshape(16, 128), key.reshape(16, 128)
                        query /= np.sqrt(np.sum(query**2, axis=1, keepdims=True)+1e-6)*sqrt(128)
                        key /= np.sqrt(np.sum(key**2, axis=1, keepdims=True)+1e-6)
                    else:
                        value, key, query = np.split(keys, [VEC, VEC+256])

                    def state(first):
                        if first == VEC:
                            finish()
                            return
                        count = 16
                        head = first//128
                        idx = slice(first, first+count)
                        start = first*depth*4
                        size = count*depth*4

                        def loaded(payload):
                            block = floats(payload).reshape(count, depth)
                            block *= decay[head]
                            if gdn:
                                k, q = key[head//2], query[head//2]
                                correction = (value[idx]-np.sum(block*k, axis=1))*beta[head]
                                block += correction[:, None]*k
                                out[idx] = np.sum(block*q, axis=1)
                            else:
                                block += (delta[head]*value[idx])[:, None]*key
                                out[idx] = np.sum(block*query, axis=1)+value[idx]*skip[head]
                            # One 32-lane state engine plus local RAM issue slots.
                            cycles = count*depth*(4 if gdn else 3)//32+8
                            self.unit.edge(lambda: self.transfer(after+start, size,
                                             lambda _: state(first+count), q16(block)), cycles)

                        self.transfer(before+start, size, loaded)

                    def finish():
                        if gdn:
                            view = out.reshape(32, 128)
                            view /= np.sqrt(np.mean(view**2, axis=1, keepdims=True)+eps)
                            out[:] = (view*gamma).reshape(VEC)*silu(z)
                        else:
                            out[:] *= silu(z)
                            out[:] *= gamma/np.sqrt(np.mean(out**2)+eps)
                        self.unit.edge(lambda: self.unit.write_span(self.context, 0, q16(out), done), 4096)

                    state(0)

                convolution(0)

            self.transfer(params, align(param_count*4), parameters)
        return run
