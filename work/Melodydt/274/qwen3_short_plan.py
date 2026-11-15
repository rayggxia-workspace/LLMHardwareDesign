"""Compile Qwen3 short workloads into compact MC pages and timed LC descriptors."""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from struct import pack, pack_into
from zlib import crc32

import assemble_cases
from compile_scope_loops import expand
from emit_native_mother import emit_mother_pages
from make_lc_kernel import kernel
import numpy as np

from qwen3_gather import TABLE, TOPOLOGY
from test_qwen3_rms import weights


U, P, CONTEXT, MID = 3, 0, 1, 2
HIDDEN, HEAD, KV_HEADS, HEADS, FFN, VOCAB = 1024, 128, 8, 16, 3072, 151936
EPS = round(1e-6 * 2**32)
VECTOR, DMA, COPY, ACT, HEAD_OUT, ROTARY, RESIDUAL = 8, 9, 10, 11, 12, 13, 14
ATT_WIDE, ELEMENT, MOE, RECURRENT = 15, 16, 17, 18
BASE_ABI = 0x02500002
PROJ = 0x02505001
PROJ_ABI = 0x02504D02
ATT1 = int.from_bytes(b"ATT1", "little")
ADD2 = 2
STORE, LOAD = 1, 2
KV_START = 1 << 33


def align(size, block=64):
    return (size + block - 1) & -block


def hash_file(path):
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def seal(schema, opcode, abi, format, *values, offset=16):
    raw = bytearray(128)
    pack_into("<IHHII", raw, 0, schema, len(raw), opcode, abi, TOPOLOGY)
    pack_into(format, raw, offset, *values)
    pack_into("<I", raw, 124, crc32(raw[:124]))
    return raw


def projection_record(address, columns, width, first, groups, word, route=0, vocab=False, backing=0):
    payload = seal(HEAD_OUT if vocab else PROJ, 2, PROJ_ABI, "<QQIIHBBHHHBB", address, 0,
                   columns, first, 8, groups, 0, width, 0, width, 1, int(vocab), offset=48)
    pack_into("<6HQQ", payload, 84, 960, word, 0, 0, 0, 0, 0, 0)
    payload[16] = route
    pack_into("<Q", payload, 24, backing)
    pack_into("<I", payload, 124, crc32(payload[:124]))
    return payload


@dataclass(frozen=True)
class Region:
    address: int
    size: int
    path: Path


class Layout:
    def __init__(self, folder, immutable_end=KV_START):
        self.folder = folder
        self.images = []
        self.address = TABLE
        self.proof = []
        self.immutable_end = immutable_end

    def file(self, path, *, expected=None):
        path = path.resolve()
        size = path.stat().st_size
        digest = hash_file(path)
        if not size or size % 64 or expected is not None and expected != digest:
            raise ValueError(f"unaligned or unverified image {path}")
        address = self.address
        self.images.append(Region(address, size, path))
        self.proof.append({"address": address, "bytes": size, "path": str(path), "sha256": digest})
        self.address += size
        if self.address >= self.immutable_end:
            raise ValueError("immutable images intersect KV")
        return address

    def write(self, name, data):
        path = self.folder / name
        path.write_bytes(bytes(data).ljust(align(len(data)), b"\0"))
        return self.file(path)

    def close(self):
        text = "\n".join(f"{r.address} {r.size} {r.path}" for r in self.images)
        (self.folder / "ddr-initial.tsv").write_text(f"{len(self.images)}\n{text}\n")


class Compiler:
    hidden, vocab, token_word, kv_row, kv_heads = HIDDEN, VOCAB, 512, 512, KV_HEADS
    three_p = False

    def __init__(self, checkpoint, frozen, packed, reference, output, layers, history, mode):
        self.layout = Layout(output)
        self.checkpoint = checkpoint
        self.layers = layers
        self.history = history
        self.mode = mode
        self.parts = []
        self.records = {}
        self.calls = []
        self.gamma = {}
        self.positions = [history, history + 1]
        self.kv_row = 512
        self.pad_kv_head = HEAD
        self.kv_heads = KV_HEADS
        self.kv_bytes = align((history + 2) * self.kv_row, 4096)
        self.input_ids = json.loads((reference / "input-ids.json").read_text())
        self.reference = json.loads((reference / "reference.json").read_text())
        base = self.layout.file(frozen / "embedding.s32")
        self.prompt = self.layout.write("prompt.bin", pack("<2i", *self.input_ids[:2]))
        self.add_embedding = seal(3, 4, VECTOR, "<QIHHHH", base, VOCAB, 8192, 0, 32, HIDDEN*4)
        for item in sorted(packed.glob("*/receipt.json")):
            for name, tensor in json.loads(item.read_text())["tensors"].items():
                if name != "model.embed_tokens.weight" and int(name.split(".")[2]) >= layers:
                    continue
                self.records[name] = (self.layout.file(item.parent / tensor["file"], expected=tensor["sha256"]),
                                      *tensor["shape"])

    def append(self, site, raw):
        self.calls.append((site, raw))

    def load(self, site, address, word, words):
        self.append(site, seal(DMA, LOAD, VECTOR, "<QHH", address, word, words))

    def store(self, site, address, word, words):
        self.append(site, seal(DMA, STORE, VECTOR, "<QHH", address, word, words))

    def copy(self, source, site, source_word, dest, words):
        self.append(site, seal(COPY, 1, VECTOR, "<B3H", source, source_word, dest, words))

    def rms(self, site, name, source, dest, words):
        if name not in self.gamma:
            gamma = self.vector(name)
            if gamma.size != words * 4:
                raise ValueError("gamma shape differs from compiled RMS")
            self.gamma[name] = self.layout.write("gamma-" + name + ".bin",
                                                 np.rint(gamma*65536).astype("<i4").tobytes())
        self.rms_address(site, self.gamma[name], source, dest, words)

    def rms_address(self, site, address, source, dest, words, gamma=None):
        if gamma is None:
            gamma = (0 if source else self.hidden//4) if site == U else 224
        self.load(site, address, gamma, words)
        self.append(site, seal(3, 3, VECTOR, "<4HI", source, gamma, dest, words,
                               getattr(self, "eps", EPS)))

    def final_norm(self):
        self.rms(U, "model.norm.weight", 0, self.hidden//4, self.hidden//4)

    def vector(self, name):
        return weights(self.checkpoint, name)

    def add(self, left, right, dest, words):
        self.append(U, seal(3, ADD2, BASE_ABI, "<4H", left, right, dest, words))

    def project(self, name, output_word, start=0, end=None, *, route=0, vocab=False, backing=0):
        address, columns, k = self.records[name]
        end = columns if end is None else end
        if not 0 <= start < end <= columns or (start | end) % 8:
            raise ValueError("projection target differs from whole N8 column groups")
        for first in range(start, end, 128):
            groups = min(128, end - first) // 8
            word = output_word if vocab else output_word+(first-start)//4
            self.append(P, projection_record(address, columns, k, first, groups, word, route, vocab, backing))

    def wave(self, records):
        """Lower one FFN batch to independent CALLs and a common WAIT mask."""
        if len(records) > 1:
            self.parallel_waves[len(self.calls)] = len(records)
        self.calls.extend(records)

    def three_p_ffn(self, gate, up, down, width, layer, position, *, opcode=1, gain=1., up_start=0):
        """Shard Gate/Up and Down by output tile across P0/P1/P2."""
        if self.hidden % 128 or width % 128 or self.hidden > 3072:
            raise ValueError("FFN dimensions exceed the three-P allocation")
        source = U if self.hidden <= 2048 else MID
        word = self.hidden//4 if source == U else 0
        for site in (P, CONTEXT, MID):
            if source != site:
                self.copy(source, site, word, 0, self.hidden//4)
        backing = (15 << 30) + ((position-self.history)*self.layers+layer)*width*4
        self.scratch_regions.append((backing, width*4))

        def descriptor(name, first, word, route=0):
            base, columns, inner = self.records[name]
            if first < 0 or first+128 > columns:
                raise ValueError("three-P tile exceeds the packed projection")
            return projection_record(base, columns, inner, first, 16, word, route,
                                     backing=backing if route == 4 else 0)

        for first in range(0, width, 384):
            items = list(zip((P, CONTEXT, MID), range(first, min(first+384, width), 128)))
            self.wave([(site, descriptor(gate, tile, 768)) for site, tile in items])
            self.wave([(site, descriptor(up, up_start+tile, 800)) for site, tile in items])
            activate = (seal(ACT, opcode, VECTOR, "<3HI", 768, 800, 832, round(gain*65536))
                        if opcode == 4 else seal(ACT, opcode, VECTOR, "<3H", 768, 800, 832))
            self.wave([(site, activate) for site, _ in items])
            for site, tile in items:
                self.store(site, backing+tile*4, 832, 32)
        for first in range(0, self.hidden, 384):
            items = list(zip((P, CONTEXT, MID), range(first, min(first+384, self.hidden), 128)))
            self.wave([(site, descriptor(down, tile, tile//4 if site == P else 768, 4))
                       for site, tile in items])
            for site, tile in items[1:]:
                self.copy(site, P, 768, tile//4, 32)

    def coefficients(self, position):
        frequencies = 1_000_000.0 ** (-np.arange(0, 128, 2) / 128)
        angle = np.tile(position * frequencies, 2)
        data = [np.rint(f(angle) * 16384).astype("<i4").tobytes() for f in (np.cos, np.sin)]
        return self.layout.write(f"rope-{position}.bin", b"".join(data))

    def rope(self, source):
        raw = seal(int.from_bytes(b"RPE1", "little"), 1, BASE_ABI, "<4H10b",
                   source, 256, 288, 320, 14, 0, 0, 14, 0, 0, -16, -16, -16, -14)
        self.append(P, raw)

    def kv(self, layer, head, kind):
        return KV_START + ((layer * KV_HEADS + head)*2 + kind) * self.kv_bytes

    def layer(self, layer, position, coeff):
        prefix = f"model.layers.{layer}."
        self.rms(U, prefix+"input_layernorm.weight", 0, 256, 256)
        self.load(P, coeff, 256, 64)
        for head in range(KV_HEADS):
            k, v = self.kv(layer, head, 0), self.kv(layer, head, 1)
            lo, hi = head * HEAD, (head + 1) * HEAD
            self.project(prefix+"self_attn.k_proj.weight", 160, lo, hi)
            self.rms(P, prefix+"self_attn.k_norm.weight", 160, 160, 32)
            self.rope(160)
            self.store(P, k+position*512, 320, 32)
            self.project(prefix+"self_attn.v_proj.weight", 192, lo, hi)
            self.store(P, v+position*512, 192, 32)
            for q in (2*head, 2*head+1):
                self.project(prefix+"self_attn.q_proj.weight", 128, q*HEAD, (q+1)*HEAD)
                self.rms(P, prefix+"self_attn.q_norm.weight", 128, 128, 32)
                self.rope(128)
                self.append(P, seal(ATT1, 1, BASE_ABI, "<6HIQQ", position+1, position, 320,
                                    384, 544, 832, round(2**30/sqrt(128)), k, v))
                self.copy(P, CONTEXT, 832, q*32, 32)
        self.project(prefix+"self_attn.o_proj.weight", 0, route=1)
        self.copy(P, U, 0, 256, 256)
        self.add(0, 256, 0, 256)
        self.rms(U, prefix+"post_attention_layernorm.weight", 0, 256, 256)
        if self.three_p:
            self.three_p_ffn(prefix+"mlp.gate_proj.weight", prefix+"mlp.up_proj.weight",
                             prefix+"mlp.down_proj.weight", FFN, layer, position)
        else:
            for first in range(0, FFN, 128):
                self.project(prefix+"mlp.gate_proj.weight", 0, first, first+128)
                self.project(prefix+"mlp.up_proj.weight", 32, first, first+128)
                self.append(P, seal(ACT, 1, VECTOR, "<3H", 0, 32, 64))
                self.copy(P, MID, 64, first//4, 32)
            self.project(prefix+"mlp.down_proj.weight", 0, route=2)
        self.copy(P, U, 0, 256, 256)
        self.add(0, 256, 0, 256)

    def pages(self, tag):
        self.layout.address = align(self.layout.address, 128)
        descriptor_base = self.layout.write(tag+"-descriptors.bin", b"".join(raw for _, raw in self.calls))
        groups = []
        offset = 0
        while offset < len(self.calls):
            count = self.parallel_waves.get(offset, 1) if self.three_p else 1
            groups.append(tuple(site for site, _ in self.calls[offset:offset+count]))
            offset += count
        pages = emit_mother_pages(groups, descriptor_base, TOPOLOGY, assemble_cases, expand)
        self.calls.clear()
        if self.three_p:
            self.parallel_waves.clear()
        return [dict(path=f"{tag}-mc-{i}.bin",
                     address=self.layout.write(f"{tag}-mc-{i}.bin", page["image"]),
                     image_bytes=len(page["image"]), crc=crc32(page["image"]),
                     descriptor_base=page["descriptor_base"], count=page["call_count"])
                for i, page in enumerate(pages)]

    def compile(self):
        local = bytearray(kernel())
        pack_into("<I", local, 64, TOPOLOGY)
        local_address = self.layout.write("local.bin", local)
        phases = []
        for position in self.positions:
            coeff = self.coefficients(position)
            self.append(U, self.add_embedding)
            self.ingress()
            first = self.pages(f"pos{position}-ingress")
            layer_pages = []
            for layer in range(self.layers):
                self.layer(layer, position, coeff)
                layer_pages.append(self.pages(f"pos{position}-l{layer}"))
            vocab = []
            if self.mode == "decode":
                self.final_norm()
                self.project(self.head_weight, 0, vocab=True)
                vocab = self.pages(f"pos{position}-head")
            phases.append({"position": position, "ingress": first, "layers": layer_pages, "vocabulary": vocab})
        self.layout.close()
        regions = [(self.kv(layer, head, kind)+self.history*self.kv_row, 2*self.kv_row)
                   for layer in range(self.layers) if self.has_kv(layer)
                   for head in range(self.kv_heads) for kind in range(2)]
        return {"mode": self.mode, "layers": self.layers, "history": self.history,
                "hidden": self.hidden, "vocab": self.vocab, "token_word": self.token_word,
                "kv_row": self.kv_row,
                "local": {"address": local_address, "bytes": len(local), "crc": crc32(local)},
                "first_decode_input": self.reference["decode"][0]["input"],
                "prompt": self.prompt, "phases": phases, "images": self.layout.proof,
                "state": regions, "scratch": getattr(self, "scratch_regions", [])}

    def ingress(self):
        pass

    def has_kv(self, layer):
        return True

    head_weight = "model.embed_tokens.weight"
