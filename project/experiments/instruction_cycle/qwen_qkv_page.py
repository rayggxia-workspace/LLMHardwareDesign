"""Advance the 105530 serial P0 QKV page after its first KVR1 store."""

import struct

from qwen_drl1_cycle import DRL1, run_drl1
from qwen_kv_write import write_kv_burst
from qwen_native_control import P_SCOPE, TOPOLOGY
from qwen_native_ddr import require
from qwen_page_dispatch import next_call, page_commit
from qwen_post_projection import ADD2, KVR1, NATIVE_ABI, _descriptor, _s128, run_add2
from qwen_prompt_cycle import BURST_BYTES, SRAM_WORD_BYTES


ROPE = int.from_bytes(b"RPE1", "little")
ROW_WORDS = 32
WORDS_PER_BURST = BURST_BYTES // SRAM_WORD_BYTES


def _rope(call, accepted, mode):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and struct.unpack_from("<IHHII", raw) == (ROPE, 128, 1, NATIVE_ABI, TOPOLOGY)
            and not any(raw[34:124]), "unsupported generation-1 RoPE descriptor")
    source, cosine, sine, destination, *precision = struct.unpack_from("<4H10b", raw, 16)
    bases = (source, cosine, sine, destination)
    require(all(base + ROW_WORDS <= 1024 for base in bases)
            and all(abs(a - b) >= ROW_WORDS for index, a in enumerate(bases) for b in bases[index + 1:])
            and tuple(precision) == (14, 0, 0, 14, 0, 0, -16, -16, -16, -14),
            "unsupported generation-1 RoPE address or precision")

    offer = accepted + 1
    words = []
    for index in range(ROW_WORDS):
        reads = []
        for word in (source + index, source + (index ^ 16), cosine + index, sine + index):
            read = _s128(offer, word, mode)
            reads.append(read)
            offer = read["ack"] + 1
        # Row ROTATE launches the word commit, then E64 serializes each
        # PRODUCT (4 input + 12 ALU + 2 result) and ADD2 (4 + 8 + 2).
        # Low half also negates its paired half. All align/pack shifts are 0.
        first_e = offer + 1
        products = 3 if index < ROW_WORDS // 2 else 2
        write = _s128(first_e + products * 18 + 14, destination + index, mode)
        words.append({"reads": reads, "first_e": first_e, "products": products, "write": write})
        offer = write["ack"] + 2
    return {"service_accept": accepted, "service_retire": offer + 1, "status": 0,
            "read_bytes": ROW_WORDS * 4 * SRAM_WORD_BYTES, "write_bytes": ROW_WORDS * SRAM_WORD_BYTES,
            "source": source, "destination": destination, "words": words}


def _kv(call, accepted, fabric):
    raw = bytes.fromhex(call["descriptor_hex"])
    schema, size, operation, abi, topology = struct.unpack_from("<IHHII", raw)
    source, = struct.unpack_from("<H", raw, 16)
    address, tag = struct.unpack_from("<QQ", raw, 24)
    require(len(raw) == 128 and (schema, size, abi, topology) == (KVR1, 128, NATIVE_ABI, TOPOLOGY)
            and operation in (1, 2) and not any(raw[18:24]) and not any(raw[40:124])
            and source + ROW_WORDS <= 1024 and address % BURST_BYTES == 0, "unsupported generation-1 KVR1 store")

    offer = accepted + 2
    writes = []
    for index in range(ROW_WORDS // WORDS_PER_BURST):
        reads = []
        for word in range(WORDS_PER_BURST):
            read = _s128(offer, source + index * WORDS_PER_BURST + word, fabric.mode)
            reads.append(read)
            offer = read["ack"] + 1
        admit = offer + int(fabric.mode and offer % 7 == 0)
        burst_address = address + index * BURST_BYTES
        write = write_kv_burst(fabric.ddr, admit, (burst_address >> 6) & 1, tag + index, burst_address)
        writes.append({"sram_reads": reads, "address": burst_address, **write})
        # Burst and row report only after the strict write response.
        offer = write["phy_return"] + 3
    return {"service_accept": accepted, "service_retire": offer, "status": 0, "source": source,
            "read_bytes": ROW_WORDS * SRAM_WORD_BYTES, "write_bytes": ROW_WORDS * SRAM_WORD_BYTES,
            "writes": writes}


def predict_generation_one_tail(page, fabric, last_retire, projection, *, last_ticket=7):
    """Predict successive complete services 7 through `last_ticket` on one fabric."""
    require(page["generation"] == 1 and 7 <= last_ticket <= len(page["calls"])
            and projection.fabric is fabric and projection.last_ticket == 3 and projection.pending_output is None,
            "generation-1 continuation requires the completed first projection and first ADD2 lease release")
    stages = []
    retired = last_retire
    last_add2 = last_rope = None
    for index in range(6, last_ticket):
        call = page["calls"][index]
        require(call["target"] == 0 and call["ticket"] == index + 1, "unexpected serial QKV CALL")
        control = next_call(page, index - 1, retired)
        descriptor = _descriptor(fabric, call, control["descriptor_admissions"][0]["cycle"])
        accepted = descriptor["service_accept"]
        schema = call["schema"]
        if schema == P_SCOPE:
            service = projection.run(call, accepted, fabric.mode)
            service.update(service_accept=accepted, status=0, read_bytes=16 * 16 * 17 * BURST_BYTES,
                           write_bytes=ROW_WORDS * SRAM_WORD_BYTES)
            last_add2 = last_rope = None
        elif schema == DRL1:
            service = run_drl1(fabric, call, accepted)
        elif schema == ADD2:
            require(projection.pending_output is not None, "ADD2 has no raw P projection output")
            projection_base, words = projection.pending_output
            service = run_add2(call, accepted, fabric.mode, projection_base)
            projection.release_output(projection_base, words)
            last_add2 = service["destination"]
        elif schema == ROPE:
            service = _rope(call, accepted, fabric.mode)
            require(last_add2 == service["source"], "RoPE has no matching ADD2 result")
            last_rope = service["destination"]
        elif schema == KVR1:
            service = _kv(call, accepted, fabric)
            require(service["source"] in (last_add2, last_rope), "KVR1 has no matching resident result")
        else:
            raise ValueError("unsupported generation-1 service schema: {}".format(schema))
        retired = service["service_retire"]
        stages.append({"call": {"target": call["target"], "ticket": call["ticket"]}, "dispatch": control,
                       "descriptor": descriptor, "service": service})
    result = {"stages": stages}
    if last_ticket == len(page["calls"]):
        require(projection.pending_output is None, "generation-1 page retains a raw P projection lease")
        result["page_commit"] = page_commit(page, retired)
    return result
