"""Predict the 105530 G4-to-G5 handoff and first three FFN descriptors."""

from collections import deque
import json

from dma_ddr import Beat
from qwen_descriptor_dma import DESCRIPTOR_CRC_BYTES, SLOTS_PER_CHANNEL
from qwen_native_control import P_SCOPE
from qwen_native_ddr import DDR_PS, Proof, WINDOWS, require
from qwen_page_dispatch import MC_CONFIG_PM_ACK, MC_INSTRUCTION_CYCLES, _descriptor_edges
from qwen_prompt_cycle import BURST_BYTES, CORE_PS, ROW_BYTES, SRAM_ACCEPT_TO_ACK, SRAM_WORD_BYTES


GENERATION = 5
LC_BYTES = 352
MC_BYTES = 272
LOCAL_DOMAINS = (1, 2)
MC_DOMAIN = 4
FIXTURE_SEED = 25001


def _lane_ready(mode, cycle, lane, local_zero):
    return not mode or (cycle - local_zero + lane) % 7 != FIXTURE_SEED % 7


def _read_burst(ddr, cycle, tag, address, events, *, lane=None):
    """Advance a sole pending read in the activation slot or selected lane."""
    channel = ((address >> 6) & 1) if lane is None else lane // 2
    wire = channel if lane is None else lane
    device = ddr.dram[channel]
    tick = cycle * CORE_PS // DDR_PS
    require(tick >= ddr.tick[channel] and device.idle and not device.completions(tick),
            "G5 activation DDR did not start drained")
    request = Beat((wire, tag), address, False, None)
    events.append(("admit", cycle, wire, tag, address))
    limit = tick + 4096
    while not device.can_accept(tick, request):
        tick += 1
        require(tick < limit and not device.completions(tick), "G5 activation admission stalled")
    device.submit(tick, request)
    events.append(("ddr_accept", tick, wire, tag, address))
    while tick < limit:
        tick += 1
        done = device.completions(tick)
        if done:
            require(done == [request.identifier], "unexpected G5 activation DDR callback")
            break
    else:
        raise ValueError("G5 activation callback stalled")
    ddr.tick[channel] = tick
    events.append(("callback", tick, wire, tag, address))
    returned = (tick * DDR_PS + CORE_PS - 1) // CORE_PS
    events.append(("return", returned, wire, tag, address))
    return returned


def _fetch_pm(fabric, offer, region, image_bytes, ack_edges, local_zero):
    ddr = fabric.ddr
    admits, sram_writes = [], []
    domain = region["domain"]
    for offset in range(0, image_bytes, BURST_BYTES):
        address = region["address"] + offset
        lane = 2 * ((address >> 11) & 1)
        tag = (GENERATION << 32) | (domain << 16) | offset
        admitted = offer + int(not _lane_ready(fabric.mode, offer, lane, local_zero))
        returned = _read_burst(ddr, admitted, tag, address, ddr.events, lane=lane)
        admits.append({"cycle": admitted, "domain": domain, "tag": tag, "address": address})
        write = returned + 1
        for word in range(offset, min(offset + BURST_BYTES, image_bytes), SRAM_WORD_BYTES):
            ack = write + ack_edges
            sram_writes.append((word, write, ack))
            write = ack + 1
        offer = write
    return admits, sram_writes


def _descriptor(fabric, call, control, local_zero):
    """Drive a two-beat descriptor with the type-fabric lane holds."""
    ddr = fabric.ddr
    client = call["target"]
    address = call["descriptor_address"]
    offer = control["descriptor_admissions"][0]["cycle"]
    base_index = ((address >> 11) & 1) * SLOTS_PER_CHANNEL
    channel = base_index // SLOTS_PER_CHANNEL
    lane_base = channel * 2
    tags = [fabric._allocate(base_index + index, client) for index in range(2)]
    beat_addresses = [address, address + BURST_BYTES]
    device = ddr.dram[channel]
    cycle = offer + 2
    tick = cycle * CORE_PS // DDR_PS
    require(offer > fabric.last_response and tick >= ddr.tick[channel] and device.idle
            and not device.completions(tick), "G5 first descriptors overlap")
    queues = (deque(), deque())
    skids = deque()
    offered = {0: 0}
    submitted, completed = set(), set()
    responses = {}
    while len(responses) < 2:
        require(cycle - offer < 4096, "G5 descriptor did not drain")
        if skids:
            responses[skids.popleft()] = cycle
        for local, queue in enumerate(queues):
            lane = lane_base + local
            if queue and queue[0] in completed:
                index = queue.popleft()
                skids.append(index)
                ddr.events.append(("return", cycle, lane, tags[index], beat_addresses[index]))
            if local in offered and _lane_ready(fabric.mode, cycle, lane, local_zero):
                index = offered.pop(local)
                queue.append(index)
                ddr.events.append(("admit", cycle, lane, tags[index], beat_addresses[index]))
        if cycle == offer + 2:
            offered[int(0 in offered)] = 1
        if len(responses) == 2:
            break
        target = (cycle + 1) * CORE_PS // DDR_PS
        while tick < target:
            for local in (tick % 2, 1 - tick % 2):
                for index in queues[local]:
                    if index in submitted:
                        continue
                    lane = lane_base + local
                    beat = Beat((lane, tags[index]), beat_addresses[index], False, None)
                    if device.can_accept(tick, beat):
                        device.submit(tick, beat)
                        submitted.add(index)
                        ddr.events.append(("ddr_accept", tick, lane, tags[index], beat.address))
                    break
            tick += 1
            for lane, tag in device.completions(tick):
                require(tag in tags, "unexpected G5 descriptor callback tag")
                index = tags.index(tag)
                require(index in submitted and index not in completed and index in queues[lane - lane_base],
                        "unexpected G5 descriptor callback")
                completed.add(index)
                ddr.events.append(("callback", tick, lane, tag, beat_addresses[index]))
        cycle += 1
    ddr.tick[channel] = tick
    fabric.last_response = max(responses.values())
    if not hasattr(fabric, "descriptor_cursors"):
        fabric.descriptor_cursors = {}
    fabric.descriptor_cursors[channel] = (fabric.last_response, 2, client + 1)
    return {"client_responses": [responses[0], responses[1]], "global_tags": tags,
            "service_accept": fabric.last_response + DESCRIPTOR_CRC_BYTES + 2}


def predict_g5_front(page, fabric, previous_commit, archive):
    """Continue the drained G4 live DDR fabric through G5's first CALL wave."""
    require((page["generation"], page["target_mask"], page["bytes"]) == (GENERATION, 7, MC_BYTES)
            and len(page["calls"]) == 192 and len(page["waves"]) == 64 and previous_commit > fabric.last_response
            and fabric.open_record is None and fabric.generation == 2 and all(device.idle for device in fabric.ddr.dram),
            "G5 front requires the successful drained G4 predecessor")
    proof = Proof(archive, WINDOWS["next_rms"][0])
    program = json.loads(proof.read("generated/program.json"))
    activation_base = program["ffn_tail"]["normalized"]
    committed = {address for kind, cycle, _, _, address in getattr(fabric.ddr, "write_events", ())
                 if kind == "return" and cycle < previous_commit}
    require(all(activation_base + offset in committed for offset in range(0, ROW_BYTES, BURST_BYTES)),
            "G5 activation source has missing G4 strict write receipts")
    local1, local2, mother = page["pm_fetches"]
    require([(region["domain"], region["bytes"], region["write"]) for region in page["pm_fetches"]]
            == [(1, 384, False), (2, 384, False), (4, 320, False)]
            and mother["address"] == page["address"] and local1["address"] == local2["address"],
            "unexpected G5 native PM inventory")

    activation_events, sram_writes = [], []
    local_zero = previous_commit + 3
    cycle = previous_commit + 6  # P0 handoff, FFN runtime install/config/start and loader READ.
    for tag in range(ROW_BYTES // BURST_BYTES):
        address = activation_base + BURST_BYTES * tag
        returned = _read_burst(fabric.ddr, cycle, tag, address, activation_events)
        cycle = returned + 1
        for word in range(BURST_BYTES // SRAM_WORD_BYTES):
            ack = cycle + SRAM_ACCEPT_TO_ACK
            index = tag * (BURST_BYTES // SRAM_WORD_BYTES) + word
            sram_writes.append((index, cycle, ack))
            cycle = ack + 1
    page_launch = cycle + 1  # Loader DONE accepted; the held program START permits binding.
    # Already resident P0 is skipped, then P1/2 install one at a time.
    pm1, sw1 = _fetch_pm(fabric, page_launch + 6, local1, LC_BYTES, 1, local_zero)
    # LC stream report, SEAL request, bytewise CRC+ACK, and install REPORT.
    pm2, sw2 = _fetch_pm(fabric, sw1[-1][2] + LC_BYTES + 9, local2, LC_BYTES, 1, local_zero)
    # The P2 install REPORT is followed by inactive U, SESSION and MC launch.
    pmm, swm = _fetch_pm(fabric, sw2[-1][2] + LC_BYTES + 11, mother, MC_BYTES, MC_CONFIG_PM_ACK, local_zero)
    readback_first = swm[-1][2] + 2
    readback_stride = MC_CONFIG_PM_ACK + SRAM_WORD_BYTES + 1
    mc_prove = readback_first + len(swm) * readback_stride
    mc_start = mc_prove + 6

    first_wave = []
    require(page["waves"][0] == {"calls": [0, 1, 2], "wait_pc": 14, "wait_mask": 7},
            "G5 first wave is not the native three-P WAIT")
    for target, call in enumerate(page["calls"][:3]):
        require((call["target"], call["wave"], call["mc_pc"], call["schema"], call["operation"])
                == (target, 0, 8 + 2 * target, P_SCOPE, 2), "unsupported G5 first descriptor identity")
        # CALL packet acceptance stalls MC's next instruction fetch. Including
        # ADDPTR and each MC fetch/decode, adjacent CALL decodes are 16 edges apart.
        decode = mc_start + 1 + 8 * MC_INSTRUCTION_CYCLES + MC_CONFIG_PM_ACK - 1 + 16 * target
        local_call = {**call, "ticket": 1}  # LC descriptor serial resets per page.
        control = _descriptor_edges(local_call, decode)
        descriptor = _descriptor(fabric, local_call, control, local_zero)
        first_wave.append({"target": target, "ticket": call["ticket"], "dispatch": control, **descriptor})
    return {"generation": GENERATION, "page_launch": page_launch,
            "activation_events": activation_events, "activation_sram_writes": sram_writes,
            "pm_admissions": pm1 + pm2 + pmm, "lc_config_writes": [sw1, sw2], "mc_config_writes": swm,
            "mc_prove": mc_prove, "mc_start": mc_start, "first_wave": first_wave}
