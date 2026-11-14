"""Continue the 105530 generation-1 Q retirement through DRL1 and ADD2."""

from collections import deque
import struct

from dma_ddr import Beat
from qwen_descriptor_dma import DESCRIPTOR_CRC_BYTES, SLOTS_PER_CHANNEL
from qwen_drl1_cycle import gated_edge, run_drl1
from qwen_native_control import TOPOLOGY
from qwen_native_ddr import DDR_PS, require
from qwen_page_dispatch import next_call
from qwen_prompt_cycle import BURST_BYTES, CORE_PS, SRAM_ACCEPT_TO_ACK, SRAM_WORD_BYTES


ADD2 = 3
ADD2_ABI = 7
KVR1 = int.from_bytes(b"KVR1", "little")
NATIVE_ABI = 0x02500002


def _descriptor(fabric, call, offer, *, physical_ready=None, client=0):
    """Fetch both beats with real sibling-lane issue and return skids."""
    ddr = fabric.ddr
    address = call["descriptor_address"]
    require((call["target"], client) in ((0, 0), (3, 1))
            and address % (2 * BURST_BYTES) == 0 and offer > fabric.last_response
            and fabric.open_record is None and all(device.idle for device in ddr.dram),
            "descriptor requires a drained P0 or U transport")
    channel = (address >> 11) & 1
    first_lane = 2 * channel
    entry = channel * SLOTS_PER_CHANNEL
    tags = [fabric._allocate(entry + index, client) for index in range(2)]
    addresses = [address + index * BURST_BYTES for index in range(2)]
    second_offered = offer + 3
    cycle = offer + 2
    if physical_ready is not None:
        require(physical_ready >= second_offered, "descriptor block must hold both reserved beats")
        cycle = physical_ready
    first_physical = cycle
    tick = cycle * CORE_PS // DDR_PS
    device = ddr.dram[channel]
    require(tick >= ddr.tick[channel] and not device.completions(tick), "descriptor DDR did not start idle")

    offered = {first_lane: 0} if physical_ready is None else {first_lane: 0, first_lane + 1: 1}
    queues = [deque(), deque()]
    pending, complete = {}, set()
    skids = deque()
    admitted, returned, responses, lanes = ([None, None] for _ in range(4))
    while None in responses:
        require(cycle - first_physical < 4096, "post-projection descriptor did not drain")
        if skids:
            responses[skids.popleft()] = cycle
        # Capture physical responses and issue admitted holds in lane order.
        for local_lane, queue in enumerate(queues):
            lane = first_lane + local_lane
            if queue and queue[0] in complete:
                index = queue.popleft()
                skids.append(index)
                returned[index] = cycle
                ddr.events.append(("return", cycle, lane, tags[index], addresses[index]))
            if lane in offered and (not ddr.mode or (cycle + lane) % 5):
                index = offered.pop(lane)
                queue.append(index)
                admitted[index], lanes[index] = cycle, lane
                ddr.events.append(("admit", cycle, lane, tags[index], addresses[index]))
        if cycle + 1 == second_offered:
            # At offer+2 the second beat moves RESERVED→OFFERED. If the
            # prior lane is still held, allocate the second lane instead.
            lane = first_lane + int(first_lane in offered)
            offered[lane] = 1

        if None not in responses:
            break
        target = (cycle + 1) * CORE_PS // DDR_PS
        while tick < target:
            for local_lane in (tick % 2, 1 - tick % 2):
                for index in queues[local_lane]:
                    if index in pending:
                        continue
                    lane = first_lane + local_lane
                    beat = Beat((lane, tags[index]), addresses[index], False, None)
                    if device.can_accept(tick, beat):
                        pending[index] = True
                        device.submit(tick, beat)
                        ddr.events.append(("ddr_accept", tick, lane, tags[index], addresses[index]))
                    break
            tick += 1
            for lane, tag in device.completions(tick):
                index = tags.index(tag)
                require(index in pending and index not in complete and lanes[index] == lane,
                        "unexpected post-projection descriptor callback")
                complete.add(index)
                ddr.events.append(("callback", tick, lane, tag, addresses[index]))
        cycle += 1

    ddr.tick[channel] = tick
    assembled = max(responses)
    fabric.last_response = assembled
    crc = assembled + DESCRIPTOR_CRC_BYTES
    serial = call["ticket"]
    return {"descriptor_address": address, "client_accepts": [offer, offer + 1],
            "local_tags": [2 * serial, 2 * serial + 1], "global_tags": tags,
            "phy_admits": admitted, "phy_returns": returned, "client_responses": responses,
            "lanes": lanes, "assembled": assembled, "crc_complete": crc,
            "provider_offer": crc + 2, "service_accept": crc + 2}


def _s128(offer, word, mode):
    accept = gated_edge(offer, mode, 7, 2)
    return {"word": word, "bank": word & 3, "row": word >> 2, "accept": accept,
            "ack": gated_edge(accept + SRAM_ACCEPT_TO_ACK, mode, 11, 4)}


def run_add2(call, service_accept, mode, projection_base):
    """Predict successful P0 bias with its retained raw-output lease."""
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and call["target"] == 0 and call["ticket"] >= 5
            and struct.unpack_from("<IHHII", raw) == (ADD2, 128, 2, ADD2_ABI, TOPOLOGY)
            and not any(raw[24:124]), "unsupported P0 bias descriptor")
    left, right, destination, count = struct.unpack_from("<4H", raw, 16)
    require(left == projection_base and count == 32
            and all(base + count <= 1024 for base in (left, right, destination))
            and all(base == destination or abs(base - destination) >= count for base in (left, right)),
            "ADD2 descriptor differs from the retained Q output lease")

    words = []
    cmd = service_accept + 1
    for index in range(count):
        left_read = _s128(cmd + 1, left + index, mode)
        right_read = _s128(left_read["ack"] + 1, right + index, mode)
        # Both S128 operands carry two 64-bit flits. Core ADD2 uses two
        # TOTAL/SCALE/ROUND/PACK passes and E64 returns two halves.
        e_inputs = list(range(right_read["ack"] + 1, right_read["ack"] + 5))
        e_outputs = [e_inputs[-1] + 9, e_inputs[-1] + 10]
        store = _s128(e_outputs[-1] + 1, destination + index, mode)
        words.append({"command": cmd, "read_left": left_read, "read_right": right_read,
                      "e_inputs": e_inputs, "e_outputs": e_outputs, "write": store})
        # The word service reports after the real store ACK. Scope consumes
        # that report before offering the next word or its terminal.
        cmd = store["ack"] + 2
    return {"service_accept": service_accept, "service_retire": cmd, "status": 0,
            "read_bytes": 2 * count * SRAM_WORD_BYTES, "write_bytes": count * SRAM_WORD_BYTES,
            "raw_lease_release": cmd, "destination": destination, "words": words}


def _first_store_offer(call, service_accept, mode):
    raw = bytes.fromhex(call["descriptor_hex"])
    require(len(raw) == 128 and struct.unpack_from("<IHHII", raw) == (KVR1, 128, 2, NATIVE_ABI, TOPOLOGY),
            "unsupported first KVR1 store descriptor")
    source, = struct.unpack_from("<H", raw, 16)
    address, tag = struct.unpack_from("<QQ", raw, 24)
    require(source + 32 <= 1024 and address % BURST_BYTES == 0 and not any(raw[18:24])
            and not any(raw[40:124]), "invalid first KVR1 store descriptor")
    offer = service_accept + 2  # Row issues one burst, then requests its first S128 word.
    reads = []
    for index in range(BURST_BYTES // SRAM_WORD_BYTES):
        read = _s128(offer, source + index, mode)
        reads.append(read)
        offer = read["ack"] + 1
    accepted_if_idle = offer + int(mode and offer % 7 == 0)
    return {"source": source, "address": address, "tag": tag, "sram_reads": reads,
            "first_ddr_write_offer": offer, "first_ddr_write_accept_if_idle": accepted_if_idle}


def run_post_projection(page, fabric, q_retire, *, through_store=False):
    """Advance tickets 4–5, then model the first KVR1 store with strict writes."""
    require(page["generation"] == 1 and len(page["calls"]) >= 6 and q_retire > fabric.last_response,
            "post-projection prediction requires the retired first Q service")
    q_descriptor = bytes.fromhex(page["calls"][2]["descriptor_hex"])
    projection_base, = struct.unpack_from("<H", q_descriptor, 86)
    stages = []
    retired = q_retire
    for index in range(3, 6):
        call = page["calls"][index]
        control = next_call(page, index - 1, retired)
        descriptor = _descriptor(fabric, call, control["descriptor_admissions"][0]["cycle"])
        accepted = descriptor["service_accept"]
        stage = {"call": {"target": call["target"], "ticket": call["ticket"]}, "dispatch": control,
                 "descriptor": descriptor}
        stages.append(stage)
        if index == 5:
            boundary = _first_store_offer(call, accepted, fabric.mode)
            require(boundary["source"] == stages[-2]["service"]["destination"],
                    "KVR1 source differs from the preceding ADD2 destination")
            result = {"stages": stages, "write_ready": boundary}
            if through_store:
                from qwen_kv_write import write_kv_burst
                writes = []
                offer = accepted + 2
                words_per_beat = BURST_BYTES // SRAM_WORD_BYTES
                for beat in range(8):
                    reads = []
                    for word in range(words_per_beat):
                        read = _s128(offer, boundary["source"] + beat * words_per_beat + word, fabric.mode)
                        reads.append(read)
                        offer = read["ack"] + 1
                    admit = offer + int(fabric.mode and offer % 7 == 0)
                    address = boundary["address"] + beat * BURST_BYTES
                    write = write_kv_burst(fabric.ddr, admit, (address >> 6) & 1, boundary["tag"] + beat, address)
                    writes.append({"sram_reads": reads, "address": address, **write})
                    # Burst REPORT is consumed by the row on the following
                    # edge; the row then issues the next burst on its own edge.
                    offer = write["phy_return"] + 3
                stage["service"] = {"service_retire": offer, "read_bytes": 512,
                                    "write_bytes": 512, "writes": writes}
                result["write_events"] = fabric.ddr.write_events
            return result
        service = (run_drl1(fabric, call, accepted) if index == 3 else
                   run_add2(call, accepted, fabric.mode, projection_base))
        stage["service"] = service
        retired = service["service_retire"]
