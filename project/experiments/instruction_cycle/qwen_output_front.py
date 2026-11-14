"""Predict the 105530 O-page installation and its first U DRL8 consumer."""

import struct

from qwen_native_control import TOPOLOGY
from qwen_native_ddr import require
from qwen_page_dispatch import MC_CONFIG_PM_ACK, MC_INSTRUCTION_CYCLES, _descriptor_edges
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
