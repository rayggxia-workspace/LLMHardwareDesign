"""Predict the 105530 serial U post-attention residual and RMS page."""

import json
import struct

from qwen_kv_write import write_kv_burst
from qwen_native_control import TOPOLOGY
from qwen_native_ddr import Proof, WINDOWS, require
from qwen_output_front import DRL8, MC_DOMAIN, U_DESCRIPTOR_CLIENT, U_DOMAIN, U_READ_LANE
from qwen_page_dispatch import MC_CONFIG_PM_ACK, MC_INSTRUCTION_CYCLES, _wait_release, dispatch, next_call
from qwen_post_projection import ADD2, ADD2_ABI, NATIVE_ABI, _descriptor, _s128
from qwen_prompt_cycle import BURST_BYTES, ROW_BYTES, SRAM_WORD_BYTES
from qwen_prompt_rms import rms_edges


GENERATION = 4
DWS8 = int.from_bytes(b"DWS8", "little")
WORDS = ROW_BYTES // SRAM_WORD_BYTES
WORDS_PER_BURST = BURST_BYTES // SRAM_WORD_BYTES


def _install(page, fabric, previous_commit):
    require((page["generation"], page["target_mask"], page["bytes"]) == (GENERATION, 8, 240)
            and type(previous_commit) is int and previous_commit > fabric.last_response
            and page["pm_fetches"] == [{"address": page["address"], "bytes": 256,
                                       "write": False, "domain": MC_DOMAIN}],
            "residual page requires a drained O predecessor and resident U PM")
    launch = previous_commit + 1
    offer = launch + 6  # SESSION / MC_OFFER / BEGIN / ACK / STREAM / READ
    admissions, writes = [], []
    for offset in range(0, page["bytes"], BURST_BYTES):
        address = page["address"] + offset
        lane = 2 * ((address >> 11) & 1)
        tag = (GENERATION << 32) | (MC_DOMAIN << 16) | offset
        admit = offer + int(fabric.mode and (offer + lane) % 5 == 0)
        returned = fabric.ddr.read(offer, lane, tag, address)
        admissions.append({"cycle": admit, "address": address, "tag": tag, "domain": MC_DOMAIN})
        offer = returned + 1
        for word in range(offset, min(offset + BURST_BYTES, page["bytes"]), SRAM_WORD_BYTES):
            ack = offer + MC_CONFIG_PM_ACK
            writes.append((word, offer, ack))
            offer = ack + 1
    return {"page_launch": launch, "pm_admissions": admissions, "mc_config_writes": writes}


def _transfer_descriptor(call, expected, source_word):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and (call["target"], call["schema"], call["operation"]) == (U_DOMAIN, expected, 1)
            and struct.unpack_from("<IHHII", raw) == (expected, 128, 1, NATIVE_ABI, TOPOLOGY)
            and not any(raw[18:24]) and not any(raw[40:124]), "unsupported U row-movement descriptor")
    word, = struct.unpack_from("<H", raw, 16)
    address, tag = struct.unpack_from("<QQ", raw, 24)
    require(word == source_word and address % BURST_BYTES == 0
            and (tag == 0 if expected == DRL8 else tag % 128 == 0), "invalid U row-movement operands")
    return word, address, tag


def _load(call, fabric, accepted, word, *, committed):
    word, base, _ = _transfer_descriptor(call, DRL8, word)
    if committed:
        receipts = {address for event, cycle, _, _, address in fabric.ddr.write_events
                    if event == "return" and cycle < accepted}
        require(all(base + offset in receipts for offset in range(0, ROW_BYTES, BURST_BYTES)),
                "U residual load precedes the committed O row")

    reads, stores = [], []
    offer = accepted + 1
    for burst in range(ROW_BYTES // BURST_BYTES):
        address = base + burst * BURST_BYTES
        tag = (call["ticket"] << 7) | burst
        admit = offer + int(fabric.mode and (offer + U_READ_LANE) % 5 == 0)
        returned = fabric.ddr.read(offer, U_READ_LANE, tag, address)
        reads.append({"offer": offer, "admit": admit, "return": returned, "address": address,
                      "lane": U_READ_LANE, "tag": tag})
        offer = returned + 1
        for index in range(WORDS_PER_BURST):
            store = _s128(offer, word + burst * WORDS_PER_BURST + index, 0)
            stores.append(store)
            offer = store["ack"] + 1
    return {"service_accept": accepted, "service_retire": offer + 1, "status": 0,
            "read_bytes": ROW_BYTES, "write_bytes": ROW_BYTES, "source": base,
            "destination": word, "ddr_reads": reads, "sram_writes": stores}


def _add(call, accepted, loaded):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and struct.unpack_from("<IHHII4H", raw)
            == (ADD2, 128, 2, ADD2_ABI, TOPOLOGY, 0, 512, 512, WORDS)
            and loaded["destination"] == 512 and not any(raw[24:124]), "unsupported U residual ADD2")
    # Like P0 ADD2, one word issues two SRAM reads, four AP64 input flits,
    # two four-stage E32 ADD2 halves, two output flits, and one SRAM write.
    # In this serial U phase the SRAM inspect/ACK path has no mode gate.
    command = accepted + 1
    for index in range(WORDS):
        left = _s128(command + 1, index, 0)
        right = _s128(left["ack"] + 1, 512 + index, 0)
        last_e = right["ack"] + 4 + 10
        store = _s128(last_e + 1, 512 + index, 0)
        command = store["ack"] + 2
    return {"service_accept": accepted, "service_retire": command, "status": 0,
            "read_bytes": 2 * ROW_BYTES, "write_bytes": ROW_BYTES, "destination": 512}


def _store(call, fabric, accepted, producer, expected_base):
    word, base, tag = _transfer_descriptor(call, DWS8, producer["destination"])
    require(expected_base == base, "U DWS8 does not match the bound residual/RMS destination")
    offer = accepted + 2
    writes = []
    for burst in range(ROW_BYTES // BURST_BYTES):
        sram_reads = []
        for index in range(WORDS_PER_BURST):
            read = _s128(offer, word + burst * WORDS_PER_BURST + index, 0)
            sram_reads.append(read)
            offer = read["ack"] + 1
        admit = offer + int(fabric.mode and offer % 7 == 0)
        address = base + burst * BURST_BYTES
        transfer = write_kv_burst(fabric.ddr, admit, (address >> 6) & 1, tag + burst, address)
        writes.append({"address": address, "sram_reads": sram_reads, **transfer})
        offer = transfer["phy_return"] + 3
    return {"service_accept": accepted, "service_retire": offer, "status": 0,
            "read_bytes": ROW_BYTES, "write_bytes": ROW_BYTES, "address": base, "writes": writes}


def _rms(call, accepted, gamma, profile):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and struct.unpack_from("<IHHII4H", raw)
            == (ADD2, 128, 3, ADD2_ABI, TOPOLOGY, 512, 0, 0, 0)
            and not any(raw[32:124]) and gamma["source"] == profile["gamma_address"],
            "unsupported U post-attention RMS descriptor")
    epsilon, baseline, *_ = struct.unpack_from("<I4b", raw, 24)
    require(epsilon > 0 and -32 <= baseline <= 31 and 0 <= profile["extra"] <= 31 - baseline
            and 0 < profile["factor"] < 1 << 32, "invalid sealed U post-attention RMS profile")
    # Scope OFFER launches the resident-gamma core, then FACTOR accepts two
    # edges after the service. Apply uses the same U.S/E32 as prompt RMS.
    timing = rms_edges(accepted, profile["extra"])
    retire = timing["last_result_sram_ack"] + 3  # APPLY, core, scope reports.
    return {"service_accept": accepted, "service_retire": retire, "status": 0,
            "read_bytes": 4 * ROW_BYTES, "write_bytes": ROW_BYTES, "destination": 0,
            "factor_accept": timing["factor_accept"], "apply_accept": timing["apply_accept"],
            "extra_shift": profile["extra"]}


def predict_residual_page(page, fabric, previous_commit, archive):
    """Predict the six successful U services on the same live DDR state."""
    calls = page["calls"]
    bindings = ((DRL8, 1), (ADD2, 2), (DWS8, 1), (DRL8, 1), (ADD2, 3), (DWS8, 1))
    require(len(calls) == len(bindings)
            and all((call["target"], call["ticket"], call["wave"], call["mc_pc"], call["schema"], call["operation"])
                    == (U_DOMAIN, index + 2, index, 8, *kind)
                    for index, (call, kind) in enumerate(zip(calls, bindings))), "unsupported U residual page CALLs")
    program = json.loads(Proof(archive, WINDOWS["next_rms"][0]).read("generated/program.json"))
    output = program["output_projection"]
    residual = program["first_residual"]
    profile = program["post_attention_rms"]
    result = _install(page, fabric, previous_commit)
    local_calls = [{**call, "target": 0, "ticket": index + 1} for index, call in enumerate(calls)]
    local_page = {**page, "generation": 1, "target_mask": 1, "calls": local_calls}
    control = dispatch(local_page, result["mc_config_writes"][-1][2], fabric.mode)
    stages = []
    retired = None
    for index, call in enumerate(calls):
        if index:
            control = next_call(local_page, index - 1, retired)
        for admission in control["descriptor_admissions"]:
            admission["target"] = U_DOMAIN
        desc = _descriptor(fabric, {**call, "ticket": index + 1}, control["descriptor_admissions"][0]["cycle"],
                           client=U_DESCRIPTOR_CLIENT)
        accepted = desc["service_accept"]
        previous = stages[-1]["service"] if stages else None
        if index == 0:
            service = _load(call, fabric, accepted, 512, committed=True)
            require(service["source"] == output["output_base"], "U DRL8 does not consume the bound O backing")
        elif index == 1:
            service = _add(call, accepted, previous)
        elif index == 2:
            service = _store(call, fabric, accepted, previous, residual["source"])
        elif index == 3:
            service = _load(call, fabric, accepted, 0, committed=False)
        elif index == 4:
            service = _rms(call, accepted, previous, profile)
        else:
            service = _store(call, fabric, accepted, previous, profile["output_address"])
        retired = service["service_retire"]
        stages.append({"call": {"target": U_DOMAIN, "ticket": call["ticket"]},
                       "dispatch": control, "descriptor": desc, "service": service})
    wait = _wait_release(retired)["mc_wait_release"]
    return {"generation": GENERATION, **result, "stages": stages,
            "page_commit": wait + 2 * MC_INSTRUCTION_CYCLES + 2}
