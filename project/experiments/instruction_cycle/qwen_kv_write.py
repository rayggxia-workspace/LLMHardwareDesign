"""Predict a drained native 105530 KV write on the shared live DDR devices."""

from dma_ddr import Beat
from qwen_native_ddr import DDR_PS, require
from qwen_prompt_cycle import BURST_BYTES, CORE_PS


def write_kv_burst(ddr, ready_cycle, channel, tag, address):
    """Advance DDR from an already gated physical admit to the write receipt.

    The successful 105530 KV store owns one dedicated bridge slot across
    both channels. The request shares the devices with native lane reads,
    but the caller must drain those reads before entering this prefix.
    """
    require(type(ready_cycle) is int and ready_cycle >= 0
            and type(channel) is int and channel in (0, 1)
            and type(tag) is int and 0 <= tag < 1 << 64
            and type(address) is int and 0 <= address < 1 << 34 and address % BURST_BYTES == 0
            and channel == (address >> 6) & 1, "invalid 105530 KV write request")
    require(ddr.mode in (0, 1) and (not ddr.mode or ready_cycle % 7),
            "KV physical write admit violates request gate")
    require(all(device.idle and device.native_strict_writes for device in ddr.dram),
            "KV writes require the drained strict DDR bridge")
    if not hasattr(ddr, "write_events"):
        ddr.write_events = []
    if ddr.write_events:
        require(ready_cycle > ddr.write_events[-1][1], "KV write overlaps the previous physical receipt")
    device = ddr.dram[channel]
    admit_tick = ready_cycle * CORE_PS // DDR_PS
    require(admit_tick >= ddr.tick[channel] and not device.completions(admit_tick),
            "unexpected activity before KV write")
    request = Beat((channel, tag), address, True, None)
    ddr.write_events.append(("admit", ready_cycle, channel, tag, address))
    tick = admit_tick
    while not device.can_accept(tick, request):
        tick += 1
        require(tick - admit_tick < 4096 and not device.completions(tick),
                "strict KV write could not enter DDR")
    device.submit(tick, request)
    ddr.write_events.append(("ddr_accept", tick, channel, tag, address))
    accepted_tick = tick
    for tick in range(tick + 1, tick + 4097):
        completions = device.completions(tick)
        if completions:
            require(completions == [request.identifier], "unexpected KV write completion")
            break
    else:
        raise ValueError("strict KV write did not complete within 4096 DDR ticks")
    ddr.tick[channel] = tick
    ddr.write_events.append(("callback", tick, channel, tag, address))
    returned = (tick * DDR_PS + CORE_PS - 1) // CORE_PS
    if ddr.mode and returned % 11 == 0:
        returned += 1
    ddr.write_events.append(("return", returned, channel, tag, address))
    return {"phy_admit": ready_cycle, "ddr_accept": accepted_tick, "callback": tick, "phy_return": returned}
