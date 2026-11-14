"""Predict the 105530 O-page installation and its first U DRL8 consumer."""

import struct

from qwen_attention_front import DWS1, _activation_store
from qwen_native_control import P_SCOPE, TOPOLOGY
from qwen_native_ddr import require
from qwen_page_dispatch import MC_CONFIG_PM_ACK, MC_INSTRUCTION_CYCLES, _descriptor_edges, _wait_release, next_call
from qwen_post_projection import NATIVE_ABI, _descriptor
from qwen_prompt_cycle import BURST_BYTES, ROW_BYTES, SRAM_ACCEPT_TO_ACK, SRAM_WORD_BYTES


GENERATION = 3
MC_DOMAIN = 4
U_DOMAIN = 3
U_DESCRIPTOR_CLIENT = 1
U_READ_LANE = 3
LC_IMAGE_BYTES = 352
MC_IMAGE_BYTES = 272
DRL8 = int.from_bytes(b"DRL8", "little")
FIRST_PROJECTION = 157
LAST_STORE = 188


def _fetch_pm(fabric, offer, address, byte_count, domain, config_ack):
    admissions, writes = [], []
    for offset in range(0, byte_count, BURST_BYTES):
        base = address + offset
        lane = 2 * ((base >> 11) & 1)
        tag = (GENERATION << 32) | (domain << 16) | offset
        admitted = offer + int(fabric.mode and (offer + lane) % 5 == 0)
        returned = fabric.ddr.read(offer, lane, tag, base)
        admissions.append({"cycle": admitted, "address": base, "tag": tag, "domain": domain})
        write = returned + 1
        for word in range(offset, min(offset + BURST_BYTES, byte_count), SRAM_WORD_BYTES):
            ack = write + config_ack
            writes.append((word, write, ack))
            write = ack + 1
        offer = write
    return admissions, writes


def _install(page, fabric, previous_commit):
    require((page["generation"], page["target_mask"], page["bytes"]) == (GENERATION, 9, MC_IMAGE_BYTES)
            and type(previous_commit) is int and previous_commit > fabric.last_response,
            "O page requires a committed ATT1/DWS1 predecessor")
    local, mother = page["pm_fetches"]
    require((local["domain"], local["bytes"], local["write"]) == (U_DOMAIN, 384, False)
            and (mother["domain"], mother["bytes"], mother["write"], mother["address"])
            == (MC_DOMAIN, 320, False, page["address"]), "unexpected O-page installation inventory")

    launch = previous_commit + 1
    # The cohort visits three unchanged domains before accepting the U
    # installer. Its BEGIN request/ACK and stream launch precede DDR READ.
    lc_accept = launch + 1 + U_DOMAIN
    local_pm, local_writes = _fetch_pm(fabric, lc_accept + 4, local["address"], LC_IMAGE_BYTES, U_DOMAIN, 1)
    seal_config = local_writes[-1][2] + 2
    # Config SEAL consumes one byte per edge, then the ACK is registered.
    seal_ack = seal_config + LC_IMAGE_BYTES + 1
    # LC REPORT, cohort SESSION, MC launch, BEGIN request/ACK, STREAM, READ.
    mother_pm, mother_writes = _fetch_pm(fabric, seal_ack + 7, mother["address"], MC_IMAGE_BYTES,
                                        MC_DOMAIN, MC_CONFIG_PM_ACK)
    readback_first = mother_writes[-1][2] + 2
    readback_stride = MC_CONFIG_PM_ACK + SRAM_WORD_BYTES + 1
    proof = readback_first + len(mother_writes) * readback_stride
    # Config prove/prepare each ACK at +1. Install REPORT, deploy and
    # START then precede the MC's first PM instruction request.
    start = proof + 6
    call = page["calls"][0]
    require((call["target"], call["ticket"], call["wave"], call["mc_pc"])
            == (U_DOMAIN, 1, 0, 8), "unexpected O-page first CALL")
    decode = start + 1 + call["mc_pc"] * MC_INSTRUCTION_CYCLES + MC_CONFIG_PM_ACK - 1
    return {"page_launch": launch, "pm_admissions": local_pm + mother_pm,
            "lc_config_writes": local_writes, "mc_config_writes": mother_writes,
            "lc_seal_ack": seal_ack, "mc_prove": proof, "mc_start": start}, _descriptor_edges(call, decode)


def _load_av(call, fabric, accepted):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and (call["schema"], call["operation"]) == (DRL8, 1)
            and struct.unpack_from("<IHHII", raw) == (DRL8, 128, 1, NATIVE_ABI, TOPOLOGY)
            and not any(raw[18:24]) and not any(raw[32:124]), "unsupported U DRL8 descriptor")
    destination, = struct.unpack_from("<H", raw, 16)
    source, = struct.unpack_from("<Q", raw, 24)
    require(destination == 512 and source % BURST_BYTES == 0, "unsupported U DRL8 scratch or backing")
    committed = {address for kind, cycle, _, _, address in getattr(fabric.ddr, "write_events", ())
                 if kind == "return" and cycle < accepted}
    require(all(source + offset in committed for offset in range(0, ROW_BYTES, BURST_BYTES)),
            "U DRL8 requires all sixteen committed ATT1 output spans")

    offer = accepted + 1
    reads, stores = [], []
    words_per_burst = BURST_BYTES // SRAM_WORD_BYTES
    for burst in range(ROW_BYTES // BURST_BYTES):
        address = source + burst * BURST_BYTES
        tag = (call["ticket"] << 7) | burst
        admit = offer + int(fabric.mode and (offer + U_READ_LANE) % 5 == 0)
        returned = fabric.ddr.read(offer, U_READ_LANE, tag, address)
        reads.append({"offer": offer, "admit": admit, "return": returned,
                      "address": address, "lane": U_READ_LANE, "tag": tag})
        offer = returned + 1
        for word in range(words_per_burst):
            index = destination + burst * words_per_burst + word
            ack = offer + SRAM_ACCEPT_TO_ACK
            stores.append({"word": index, "accept": offer, "ack": ack})
            offer = ack + 1
    # The U inspect port is ungated in both modes. The DRL8 loader's DONE
    # is accepted one edge after the last SRAM ACK, then provider REPORT.
    return {"service_accept": accepted, "service_retire": offer + 1, "status": 0,
            "read_bytes": ROW_BYTES, "write_bytes": ROW_BYTES, "source": source,
            "destination": destination, "ddr_reads": reads, "sram_writes": stores}


def predict_output_front(page, fabric, previous_commit):
    """Advance the existing live devices to the committed AV load terminal."""
    setup, control = _install(page, fabric, previous_commit)
    call = page["calls"][0]
    descriptor = _descriptor(fabric, call, control["descriptor_admissions"][0]["cycle"], client=U_DESCRIPTOR_CLIENT)
    service = _load_av(call, fabric, descriptor["service_accept"])
    return {"generation": GENERATION, **setup,
            "stages": [{"call": {"target": call["target"], "ticket": call["ticket"]},
                        "dispatch": control, "descriptor": descriptor, "service": service}]}


def predict_output_page(page, fabric, previous_commit, projection, *, last_ticket=LAST_STORE):
    """Continue the same physical P0 and DDR channels through the O page."""
    calls = page["calls"]
    require(len(calls) == 1 + LAST_STORE - FIRST_PROJECTION + 1
            and FIRST_PROJECTION <= last_ticket <= LAST_STORE
            and projection.fabric is fabric and projection.previous is not None
            and projection.last_ticket < FIRST_PROJECTION and projection.pending_output is None,
            "O page requires a drained projection instance from QKV")
    require(all((call["target"], call["ticket"], call["wave"], call["mc_pc"], call["schema"])
                == (0, FIRST_PROJECTION + index, index + 1, 13, P_SCOPE if index % 2 == 0 else DWS1)
                for index, call in enumerate(calls[1:])), "unsupported O projection/store sequence")
    result = predict_output_front(page, fabric, previous_commit)
    stages = result["stages"]
    loaded_av = stages[0]["service"]
    local_calls = [{**call, "ticket": index + 1} for index, call in enumerate(calls[1:])]
    local_page = {**page, "generation": 1, "target_mask": 1, "calls": local_calls}
    retired = loaded_av["service_retire"]
    next_limit = last_ticket - FIRST_PROJECTION + 1
    seen_tiles = set()
    row_address = tile = None
    for index, call in enumerate(calls[1:1 + next_limit]):
        if index:
            control = next_call(local_page, index - 1, retired)
        else:
            require(page["waves"][0]["wait_pc"] == 10 and page["waves"][1]["wait_pc"] == 15,
                    "unexpected U-to-P control sequence")
            wait = _wait_release(retired)
            # SETHI and LOOP-BEGIN separate the initial U WAIT from P CALL.
            decode = wait["mc_wait_release"] + 3 * MC_INSTRUCTION_CYCLES
            control = {**wait, **_descriptor_edges(local_calls[0], decode)}
        offer = control["descriptor_admissions"][0]["cycle"]
        descriptor = _descriptor(fabric, local_calls[index], offer)
        accepted = descriptor["service_accept"]
        raw = bytes.fromhex(call["descriptor_hex"])
        if index % 2 == 0:
            tile, = struct.unpack_from("<I", raw, 68)
            require(tile not in seen_tiles, "O projection repeats an output tile")
            seen_tiles.add(tile)
            service = projection.run(call, accepted, fabric.mode, loaded_av=loaded_av)
            service.update(service_accept=accepted, status=0, read_bytes=256 * 17 * BURST_BYTES, write_bytes=512)
        else:
            base, words = projection.pending_output
            address, = struct.unpack_from("<Q", raw, 24)
            head = address - 4 * tile
            if row_address is None:
                row_address = head
            require(head == row_address and words * SRAM_WORD_BYTES == 512, "O DWS1 does not commit its projection span")
            service = _activation_store(call, accepted, fabric, base)
            projection.release_output(base, words)
        retired = service["service_retire"]
        stages.append({"call": {"target": call["target"], "ticket": call["ticket"]},
                       "dispatch": control, "descriptor": descriptor, "service": service})
    if last_ticket == LAST_STORE:
        require(seen_tiles == set(range(0, 2048, 128)), "O page does not cover its complete output row")
        wait = _wait_release(retired)["mc_wait_release"]
        result["page_commit"] = wait + 2 * MC_INSTRUCTION_CYCLES + 2
    return result
