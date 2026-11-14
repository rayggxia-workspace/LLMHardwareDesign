"""Advance the 105530 serial P0 QKV page after its first KVR1 store."""

import hashlib
import json
import struct

from qwen_drl1_cycle import DRL1, run_drl1
from qwen_kv_write import write_kv_burst
from qwen_native_control import P_SCOPE, TOPOLOGY
from qwen_native_ddr import Proof, WINDOWS, fields, require
from qwen_page_dispatch import next_call, page_commit
from qwen_post_projection import ADD2, KVR1, NATIVE_ABI, _descriptor, _s128, run_add2
from qwen_prompt_cycle import BURST_BYTES, ROW_BYTES, SRAM_WORD_BYTES, load_row
from qwen_prompt_rms import range_shift, rms_edges


ROPE = int.from_bytes(b"RPE1", "little")
ROW_WORDS = 32
WORDS_PER_BURST = BURST_BYTES // SRAM_WORD_BYTES
HISTORY_ROW_SHA = (
    "134e40c84572c83a5aaf999c23a702536df5c60d3acc22a70f8a6fd50e6e82f6",
    "380fafd7343579c46fdcf3bc5da76d5df664a8fb27cc9f15f337fe0a68ab00d6",
)


def read_history_rows(archive, embedding):
    """Bind the two additional historical tokens and their RMS scan profiles."""
    proof = Proof(archive, WINDOWS["next_rms"][0])
    program = json.loads(proof.read("generated/program.json"))["prompt_ingress"]
    tokens = struct.unpack_from("<3I", proof.read("generated/token.bin"))
    reference = tuple(int(line, 16) for line in proof.read("generated/history-meta.hex").splitlines())
    gamma, baseline, *_ = map(int, fields(proof.read("generated/rms-descriptor.txt"), 7))
    require(len(reference) == len(tokens) == 3 and tokens == tuple(program["tokens"])
            and gamma == program["gamma_address"] and program["serial_rms"] is True,
            "invalid historical row metadata")
    rows = []
    with embedding.open("rb") as source:
        for token, metadata, expected in zip(tokens[1:], reference[1:], HISTORY_ROW_SHA):
            source.seek(token * ROW_BYTES)
            data = source.read(ROW_BYTES)
            digest = hashlib.sha256(data).hexdigest()
            require(len(data) == ROW_BYTES and metadata & 0xffffffff == token and digest == expected,
                    "historical token differs from sealed embedding range")
            _, _, selected = range_shift(struct.unpack("<{}i".format(ROW_BYTES // 4), data), baseline)
            extra = selected - baseline
            require(extra == (metadata >> 64) & 63, "historical RMS shift differs from sealed row metadata")
            rows.append({"token": token, "address": program["embedding_address"] + (token - tokens[0]) * ROW_BYTES,
                         "gamma_address": gamma, "extra_shift": extra,
                         "row_sha256": digest})
    return rows


def _refill_history(ddr, retired, row):
    # After K/V store number four or eight, the wrapper retires the old
    # embedding row. The next token is already held in the one prompt beat.
    embedding_done, _ = load_row(ddr, retired + 3, 1, row["address"], 0)
    gamma_done, _ = load_row(ddr, embedding_done + 3, 3, row["gamma_address"], ROW_BYTES // SRAM_WORD_BYTES)
    gamma_ack = gamma_done - 1
    edges = rms_edges(gamma_ack, row["extra_shift"])
    return {**row, "previous_store_retire": retired, "last_gamma_sram_ack": gamma_ack,
            "row_publish": edges["row_publish_visible"]}


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


def _resident_result(resident, destination, kind):
    # The page can preserve a completed K/V row across several unrelated
    # P scopes. Invalidate only an overwritten region in the same P SRAM.
    for source in tuple(resident):
        if abs(source - destination) < ROW_WORDS:
            del resident[source]
    if kind is not None:
        resident[destination] = kind


def predict_generation_one_tail(page, fabric, last_retire, projection, *, last_ticket=7, history_rows=None):
    """Predict successive complete services 7 through `last_ticket` on one fabric."""
    require(page["generation"] == 1 and 7 <= last_ticket <= len(page["calls"])
            and projection.fabric is fabric and projection.last_ticket == 3 and projection.pending_output is None,
            "generation-1 continuation requires the completed first projection and first ADD2 lease release")
    stages = []
    retired = last_retire
    resident = {}
    history = []
    for index in range(6, last_ticket):
        call = page["calls"][index]
        require(call["target"] == 0 and call["ticket"] == index + 1, "unexpected serial QKV CALL")
        control = next_call(page, index - 1, retired)
        physical_ready = None
        if index in (20, 40):
            require(history_rows is not None and len(history_rows) == 2,
                    "continuation needs the bound historical embedding rows")
            history.append(_refill_history(fabric.ddr, retired, history_rows[len(history)]))
            physical_ready = history[-1]["row_publish"]
        descriptor = _descriptor(fabric, call, control["descriptor_admissions"][0]["cycle"],
                                 physical_ready=physical_ready)
        accepted = descriptor["service_accept"]
        schema = call["schema"]
        if schema == P_SCOPE:
            service = projection.run(call, accepted, fabric.mode)
            service.update(service_accept=accepted, status=0, read_bytes=16 * 16 * 17 * BURST_BYTES,
                           write_bytes=ROW_WORDS * SRAM_WORD_BYTES)
            _resident_result(resident, projection.pending_output[0], None)
        elif schema == DRL1:
            service = run_drl1(fabric, call, accepted)
            destination, = struct.unpack_from("<H", bytes.fromhex(call["descriptor_hex"]), 16)
            _resident_result(resident, destination, None)
        elif schema == ADD2:
            require(projection.pending_output is not None, "ADD2 has no raw P projection output")
            projection_base, words = projection.pending_output
            service = run_add2(call, accepted, fabric.mode, projection_base)
            projection.release_output(projection_base, words)
            _resident_result(resident, service["destination"], ADD2)
        elif schema == ROPE:
            service = _rope(call, accepted, fabric.mode)
            require(resident.get(service["source"]) == ADD2, "RoPE has no matching ADD2 result")
            _resident_result(resident, service["destination"], ROPE)
        elif schema == KVR1:
            source, = struct.unpack_from("<H", bytes.fromhex(call["descriptor_hex"]), 16)
            producer = ROPE if call["operation"] == 1 else ADD2
            require(resident.get(source) == producer, "KVR1 has no matching resident result")
            service = _kv(call, accepted, fabric)
        else:
            raise ValueError("unsupported generation-1 service schema: {}".format(schema))
        retired = service["service_retire"]
        stages.append({"call": {"target": call["target"], "ticket": call["ticket"]}, "dispatch": control,
                       "descriptor": descriptor, "service": service})
    result = {"stages": stages, "history_rows": history}
    if last_ticket == len(page["calls"]):
        require(projection.pending_output is None, "generation-1 page retains a raw P projection lease")
        result["page_commit"] = page_commit(page, retired)
    return result
