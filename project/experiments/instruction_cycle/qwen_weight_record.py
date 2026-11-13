"""Advance 105530's first two P0 weight records on the live DDR devices."""

from dma_ddr import Beat
from qwen_descriptor_dma import BURST_BYTES, SLOTS_PER_CHANNEL
from qwen_native_ddr import DDR_PS, require
from qwen_prompt_cycle import CORE_PS


CLIENT = 9
SKIDS_PER_CHANNEL = 3
LANE_DEPTH = 16
ISSUE_WINDOW_CREDITS = 4
PREFIX_RECORD_ADDRESSES = (0x4C9000, 0x4CD400)


def _advance_ddr(ddr, channel, tick, target, queues, submitted, completed, addresses):
    """Run the fixture's per-channel, alternating lane scan through one core edge."""
    device = ddr.dram[channel]
    while tick < target:
        for local_lane in (tick % 2, 1 - tick % 2):
            for _, beat in queues[local_lane]:
                if beat.identifier in submitted:
                    continue
                if device.can_accept(tick, beat):
                    device.submit(tick, beat)
                    submitted.add(beat.identifier)
                    ddr.events.append(("ddr_accept", tick, *beat.identifier, beat.address))
                break
        tick += 1
        for identifier in device.completions(tick):
            require(identifier in submitted and identifier not in completed, "unexpected weight DDR callback")
            completed.add(identifier)
            ddr.events.append(("callback", tick, *identifier, addresses[identifier]))
    return tick


def read_weight_record(fabric, offer_cycle, address, *, beats=17):
    """Predict the next physically isolated client-9 record in the frozen prefix.

    The caller supplies the first M request offer from the control/alloc FSM.
    This prefix starts after all earlier physical and client responses and
    ends at the final M fill. Slot serials, arbitration cursors and live DDR
    state survive the handoff between these records.
    """
    ddr = fabric.ddr
    completed_records, issue_cursors, response_cursor = getattr(fabric, "weight_prefix_state", (0, (0, 0), 0))
    require(type(offer_cycle) is int and offer_cycle > fabric.last_response
            and fabric.open_record is None
            and all(device.idle for device in ddr.dram), "first weight record requires a drained prefix")
    require(completed_records < len(PREFIX_RECORD_ADDRESSES) and type(address) is int
            and address == PREFIX_RECORD_ADDRESSES[completed_records] and type(beats) is int and beats == 17,
            "unsupported weight record outside the first two Q projection records")

    channel = (address >> 11) & 1
    lane_base = channel * 2
    entry_base = channel * SLOTS_PER_CHANNEL
    skid_base = channel * SKIDS_PER_CHANNEL
    total_skids = 2 * SKIDS_PER_CHANNEL
    slots = range(entry_base, entry_base + SLOTS_PER_CHANNEL)
    device = ddr.dram[channel]
    tick = offer_cycle * CORE_PS // DDR_PS
    require(tick >= ddr.tick[channel] and not device.completions(tick), "unexpected DDR activity before weight offer")

    accepts, tags = [], []
    admits, returns, responses, lanes = ([None] * beats for _ in range(4))
    occupied = {}
    reserved = []
    offers = [None, None]
    skids = [None] * SKIDS_PER_CHANNEL
    queues = [[], []]
    submitted, completed = set(), set()
    addresses = {}
    issue_cursor = issue_cursors[channel]
    previous_issues = 0
    cycle = offer_cycle
    while None in responses:
        require(cycle - offer_cycle < 4096, "isolated weight record did not drain")
        require(not any(fabric.serials[slot] == 65535 for slot in range(2 * SLOTS_PER_CHANNEL)
                        if slot not in occupied), "weight DMA would require a transport fence")
        # A slot freed by the client handshake on this edge becomes reusable
        # on the next edge, so source allocation sees pre-edge occupancy.
        free_entry = None
        if len(accepts) < beats:
            free_entry = next((slot for slot in slots if slot not in occupied), None)
            require(free_entry is not None, "isolated weight producer exhausted typed slots")

        live_skids = [slot for slot, entry in enumerate(skids) if entry is not None]
        forwarded = min(live_skids, key=lambda slot: (skid_base + slot - response_cursor) % total_skids,
                        default=None)
        if forwarded is not None:
            responses[occupied.pop(skids[forwarded])] = cycle
            skids[forwarded] = None
            response_cursor = (skid_base + forwarded + 1) % total_skids

        issues = 0
        for local_lane in range(2):
            lane = lane_base + local_lane
            queue = queues[local_lane]
            ready = len(queue) < LANE_DEPTH and (not ddr.mode or (cycle + lane) % 5 != 0)
            if queue and queue[0][1].identifier in completed and None in skids:
                entry, beat = queue.pop(0)
                submitted.remove(beat.identifier)
                completed.remove(beat.identifier)
                skids[skids.index(None)] = entry
                returns[occupied[entry]] = cycle
                ddr.events.append(("return", cycle, lane, beat.identifier[1], beat.address))
            if offers[local_lane] is not None and ready:
                entry = offers[local_lane]
                index = occupied[entry]
                tag = tags[index]
                beat = Beat((lane, tag), address + BURST_BYTES * index, False, None)
                queue.append((entry, beat))
                addresses[beat.identifier] = beat.address
                admits[index], lanes[index] = cycle, lane
                offers[local_lane] = None
                issues += 1
                ddr.events.append(("admit", cycle, lane, tag, beat.address))

        held = sum(entry is not None for entry in offers)
        budget = ISSUE_WINDOW_CREDITS - previous_issues - issues - held
        require(budget >= 0, "typed issue credit underflow")
        ordered = sorted(reserved, key=lambda entry: (entry - entry_base - issue_cursor) % SLOTS_PER_CHANNEL)
        for local_lane in range(2):
            if offers[local_lane] is None and budget and ordered:
                entry = ordered.pop(0)
                reserved.remove(entry)
                offers[local_lane] = entry
                issue_cursor = (entry - entry_base + 1) % SLOTS_PER_CHANNEL
                budget -= 1
        previous_issues = issues

        if free_entry is not None:
            occupied[free_entry] = len(accepts)
            reserved.append(free_entry)
            accepts.append(cycle)
            tags.append(fabric._allocate(free_entry, CLIENT))

        if None not in responses:
            break
        target = (cycle + 1) * CORE_PS // DDR_PS
        tick = _advance_ddr(ddr, channel, tick, target, queues, submitted, completed, addresses)
        cycle += 1

    require(not occupied and not any(queues) and not submitted and not completed and device.idle,
            "weight record has live transport after its final client response")
    ddr.tick[channel] = tick
    fabric.last_response = max(responses)
    issue_cursors = list(issue_cursors)
    issue_cursors[channel] = issue_cursor
    fabric.weight_prefix_state = (completed_records + 1, tuple(issue_cursors), response_cursor)
    return {"address": address, "client_accepts": accepts, "phy_admits": admits, "phy_returns": returns,
            "client_responses": responses, "global_tags": tags, "lanes": lanes}
