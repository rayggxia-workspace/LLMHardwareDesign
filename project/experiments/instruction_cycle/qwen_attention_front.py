"""Predict the serial short-context ATT1/DWS1 page in 105530."""

import struct

from qwen_attention_dot import DOT_BEGIN_TO_CHUNK, dot_chunk, score_scale_and_softmax
from qwen_kv_write import write_kv_burst
from qwen_native_control import TOPOLOGY
from qwen_native_ddr import require
from qwen_page_dispatch import MC_CONFIG_PM_ACK, MC_INSTRUCTION_CYCLES, _wait_release, dispatch, next_call
from qwen_post_projection import NATIVE_ABI, _descriptor, _s128
from qwen_prompt_cycle import BURST_BYTES, SRAM_WORD_BYTES


ATT1 = int.from_bytes(b"ATT1", "little")
DWS1 = int.from_bytes(b"DWS1", "little")
MC_DOMAIN = 4
PM_WORD_BYTES = 16
KV_ROW_BYTES = 512
FIRST_TICKET = 125
LAST_TICKET = 156


def _load_page(page, fabric, previous_commit):
    require(page["generation"] == 2 and page["target_mask"] == 1 and page["bytes"] == 240
            and type(previous_commit) is int and previous_commit > fabric.last_response,
            "attention page requires a committed generation-1 predecessor")
    require(page["pm_fetches"] == [{"address": page["address"], "bytes": 256, "write": False, "domain": MC_DOMAIN}],
            "ATT1 page unexpectedly reinstalls LC PM")
    launch = previous_commit + 1
    # With a reusable LC image, cohort SESSION and MC_OFFER are followed by
    # installer BEGIN, its ACK, and streaming launch before REQUEST.
    offer = launch + 6
    pm_rows, pm_writes = [], []
    for offset in range(0, page["bytes"], BURST_BYTES):
        address = page["address"] + offset
        lane = 2 * ((address >> 11) & 1)
        tag = (page["generation"] << 32) | (MC_DOMAIN << 16) | offset
        admitted = offer + int(fabric.mode and (offer + lane) % 5 == 0)
        returned = fabric.ddr.read(offer, lane, tag, address)
        pm_rows.append({"cycle": admitted, "domain": MC_DOMAIN, "address": address, "tag": tag})
        write = returned + 1
        for word in range(offset, min(offset + BURST_BYTES, page["bytes"]), PM_WORD_BYTES):
            ack = write + MC_CONFIG_PM_ACK
            pm_writes.append((word, write, ack))
            write = ack + 1
        offer = write

    # Readback/prove and MC fetch timings are shared with the first page.
    # LC SESSION is new, hence the descriptor-fetch local name starts at 1,
    # independent of the globally increasing provider ticket.
    normalized = {**page, "generation": 1, "calls": [{**page["calls"][0], "ticket": 1}]}
    control = dispatch(normalized, pm_writes[-1][2], fabric.mode)
    return launch, pm_rows, pm_writes, control


def _attention_profile(call):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and (call["target"], call["schema"], call["operation"]) == (0, ATT1, 1)
            and FIRST_TICKET <= call["ticket"] < LAST_TICKET and call["ticket"] % 2 == 1
            and struct.unpack_from("<IHHII", raw) == (ATT1, 128, 1, NATIVE_ABI, TOPOLOGY)
            and not any(raw[48:124]), "unexpected short ATT1 descriptor")
    count, position, q, score, work, output, scale, key, value = struct.unpack_from("<6HIQQ", raw, 16)
    require((count, position, score, work, output) == (3, 2, 512, 672, 928) and 0 <= q <= 480 and q % 32 == 0
            and 0 < scale <= 0x40000000 and abs(key - value) >= count * KV_ROW_BYTES
            and key % BURST_BYTES == value % BURST_BYTES == 0, "unsupported short ATT1 profile")
    return count, q, score, work, output, key, value


def _refill_read(fabric, offer, ticket, serial, address):
    lane = 2 * ((address >> 6) & 1) + 1
    tag = (ticket << 32) | serial
    admitted = offer + int(fabric.mode and (offer + lane) % 5 == 0)
    returned = fabric.ddr.read(offer, lane, tag, address)
    return {"offer": offer, "admit": admitted, "return": returned, "address": address, "lane": lane, "tag": tag}


def _k_refill(call, accepted, fabric, profile):
    count, _, _, work, _, key, value = profile
    # All three K and V positions were stored by the preceding QKV page.
    committed = {address for kind, cycle, _, _, address in getattr(fabric.ddr, "write_events", ())
                 if kind == "return" and cycle < accepted}
    require(all(base + offset in committed for base in (key, value)
                for offset in range(0, count * KV_ROW_BYTES, BURST_BYTES)), "ATT1 K/V inputs are not committed")
    offer = accepted + 2  # ATT1 K_REFILL accepts the loader, then READ.
    reads, sram = [], []
    for burst in range(count * KV_ROW_BYTES // BURST_BYTES):
        address = key + burst * BURST_BYTES
        read = _refill_read(fabric, offer, call["ticket"], burst, address)
        reads.append(read)
        offer = read["return"] + 1
        for index in range(BURST_BYTES // SRAM_WORD_BYTES):
            word = work + burst * (BURST_BYTES // SRAM_WORD_BYTES) + index
            response = _s128(offer, word, fabric.mode)
            sram.append(response)
            offer = response["ack"] + 1
    # Loader REPORT is consumed in K_WAIT. DOT_BEGIN offers on the next edge.
    return reads, sram, offer + 1


def _finish_attention(call, qk_begin, reads, fabric, profile):
    count, q, score, work, output, _, value = profile
    mode = fabric.mode
    qk = dot_chunk(qk_begin + DOT_BEGIN_TO_CHUNK, mode, 128, count, False, q, work, score)
    normalize = score_scale_and_softmax(qk["reply"] + 1, mode, score)
    av_begin = normalize["av_dot_begin"]
    av_groups = []
    serial = len(reads)
    for group in range(16):
        refill = av_begin + DOT_BEGIN_TO_CHUNK
        v_reads, sram = [], []
        for row in range(count):
            offer = refill + 1
            for beat in range(2):
                address = value + row * KV_ROW_BYTES + 128 * (group // 4) + BURST_BYTES * beat
                read = _refill_read(fabric, offer, call["ticket"], serial, address)
                serial += 1
                v_reads.append(read)
                offer = read["return"] + 1
                if beat == (group >> 1) & 1:
                    for index in range(2):
                        store = _s128(offer, work + 2 * row + index, mode)
                        sram.append(store)
                        offer = store["ack"] + 1
            # The range loader REPORT is accepted in V_WAIT. V_REFILL or
            # DOT_STEP becomes valid on the very next cycle.
            refill = offer + 1
        dot = dot_chunk(refill, mode, count, 8, True, score, work, output + 2 * group)
        av_groups.append({"index": group, "dot_begin": av_begin, "v_reads": v_reads,
                          "v_sram_writes": sram, "dot": dot})
        av_begin = dot["reply"] + 1
    return {"qk": qk, "normalize": normalize, "av_groups": av_groups, "service_retire": av_begin,
            "status": 0, "read_bytes": serial * BURST_BYTES, "write_bytes": KV_ROW_BYTES,
            "output_sram_base": output}


def _attention(call, accepted, fabric, through_retire):
    profile = _attention_profile(call)
    reads, sram, qk = _k_refill(call, accepted, fabric, profile)
    result = {"service_accept": accepted, "k_reads": reads, "k_sram_writes": sram, "qk_begin": qk}
    if through_retire:
        result.update(_finish_attention(call, qk, reads, fabric, profile))
    return result


def _activation_store(call, accepted, fabric, output_sram_base):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and (call["target"], call["schema"], call["operation"]) == (0, DWS1, 1)
            and struct.unpack_from("<IHHII", raw) == (DWS1, 128, 1, NATIVE_ABI, TOPOLOGY)
            and not any(raw[18:24]) and not any(raw[40:124]), "unsupported short DWS1 descriptor")
    source, = struct.unpack_from("<H", raw, 16)
    address, tag = struct.unpack_from("<QQ", raw, 24)
    require(source == output_sram_base and address % KV_ROW_BYTES == 0 and tag % 8 == 0,
            "DWS1 did not bind the preceding ATT1 result")

    # DWS1 routes to the same one-slot store provider as KVR1. The row
    # command and its first burst command precede the first S128 offer.
    offer = accepted + 2
    writes = []
    words_per_burst = BURST_BYTES // SRAM_WORD_BYTES
    for burst in range(KV_ROW_BYTES // BURST_BYTES):
        reads = []
        for word in range(words_per_burst):
            read = _s128(offer, source + burst * words_per_burst + word, fabric.mode)
            reads.append(read)
            offer = read["ack"] + 1
        admitted = offer + int(fabric.mode and offer % 7 == 0)
        dst = address + burst * BURST_BYTES
        write = write_kv_burst(fabric.ddr, admitted, (dst >> 6) & 1, tag + burst, dst)
        writes.append({"sram_reads": reads, "address": dst, **write})
        # Burst REPORT, row ISSUE/REPORT, and next SRAM request/provider REPORT.
        offer = write["phy_return"] + 3
    return {"service_accept": accepted, "service_retire": offer, "status": 0,
            "read_bytes": KV_ROW_BYTES, "write_bytes": KV_ROW_BYTES, "address": address, "writes": writes}


def predict_attention_page(page, fabric, previous_commit, *, last_ticket=LAST_TICKET):
    """Run generation 2 through its requested provider or its page commit."""
    require(len(page["calls"]) == LAST_TICKET - FIRST_TICKET + 1
            and FIRST_TICKET <= last_ticket <= LAST_TICKET
            and all((call["ticket"], call["wave"]) == (FIRST_TICKET + index, index)
                    for index, call in enumerate(page["calls"])), "unsupported serial ATT1/DWS1 sequence")
    launch, pm_rows, pm_writes, control = _load_page(page, fabric, previous_commit)
    local_calls = [{**call, "ticket": index + 1} for index, call in enumerate(page["calls"])]
    local_page = {**page, "generation": 1, "calls": local_calls}
    retired = lease = None
    stages = []
    for index, call in enumerate(page["calls"][:last_ticket - FIRST_TICKET + 1]):
        if index:
            control = next_call(local_page, index - 1, retired)
        offer = control["descriptor_admissions"][0]["cycle"]
        descriptor = _descriptor(fabric, local_calls[index], offer)
        accepted = descriptor["service_accept"]
        if index % 2 == 0:
            require(lease is None, "ATT1 launch overlaps a live DWS1 output lease")
            service = _attention(call, accepted, fabric, True)
            lease = service["output_sram_base"]
        else:
            service = _activation_store(call, accepted, fabric, lease)
            lease = None
        retired = service["service_retire"]
        stages.append({"call": {"target": call["target"], "ticket": call["ticket"]},
                       "dispatch": control, "descriptor": descriptor, "service": service})
    result = {"generation": page["generation"], "page_launch": launch, "pm_admissions": pm_rows,
              "mc_config_writes": pm_writes, "stages": stages}
    if last_ticket == LAST_TICKET:
        require(lease is None, "attention page retains an output lease")
        # The final WAIT releases before LOOP falls through to END and the
        # cohort accepts MC terminal and publishes page commit.
        wait = _wait_release(retired)["mc_wait_release"]
        result["page_commit"] = wait + 2 * MC_INSTRUCTION_CYCLES + 2
    return result


def predict_first_attention(page, fabric, previous_commit, *, through_retire=False):
    """Run the first ATT1 through QK BEGIN, optionally through its terminal."""
    launch, pm_rows, pm_writes, control = _load_page(page, fabric, previous_commit)
    call = page["calls"][0]
    ddr_request = control["descriptor_admissions"][0]["cycle"]
    descriptor = _descriptor(fabric, {**call, "ticket": 1}, ddr_request)
    service = _attention(call, descriptor["service_accept"], fabric, through_retire)
    return {"generation": page["generation"], "ticket": call["ticket"], "page_launch": launch,
            "pm_admissions": pm_rows, "mc_config_writes": pm_writes,
            "dispatch": control, "descriptor": descriptor, **service}
