"""Bind compact mother calls to local descriptor fetches and provider completions."""

from struct import unpack_from
from zlib import crc32

from replay_tlm_mother import execute


def descriptor_key(record, topology):
    if len(record) != 128:
        raise ValueError("local controller requires a complete 128-byte descriptor")
    schema, length, opcode, abi, record_topology = unpack_from("<IHHII", record)
    checksum, = unpack_from("<I", record, 124)
    if length != 128 or record_topology != topology or crc32(record[:124]) != checksum:
        raise ValueError("local descriptor failed size, topology or CRC validation")
    return schema, abi, opcode


def run_page(page, *, topology, descriptor_base, descriptor_bytes, scheduler, providers,
             after_wait=None, timing=None, instruction=None, wait_timing=None):
    """Issue real descriptor addresses through a timed backend.

    The backend owns task admission, both 64-byte DDR reads, CRC timing,
    provider execution and the returned local terminal. A CALL stays live
    until the backend reports completion. The provider registry is explicit.
    """
    offered = set()
    dispatched = set()
    pending = {}

    def issue(target, slot, registers):
        address = registers[0] | (registers[1] << 32)
        if (registers[2:7] != (0x00010080, 0x02510001, topology, 0x02500002, 0)
                or not page["targets"] & (1 << target) or address % 128
                or not descriptor_base <= address <= descriptor_base + descriptor_bytes - 128
                or address in offered):
            raise ValueError("mother CALL differs from the compiled local controller binding")
        offered.add(address)
        issue_ps = scheduler.clock.now if timing is not None else None

        def dispatch(replies):
            if address in dispatched:
                raise ValueError("duplicate local descriptor dispatch")
            beats = {}
            for beat_address, payload in replies:
                if beat_address not in (address, address + 64) or beat_address in beats or len(payload) != 64:
                    raise ValueError("descriptor reply does not match its physical read")
                beats[beat_address] = payload
            if len(beats) != 2:
                raise ValueError("descriptor dispatch requires two returned DDR beats")
            record = beats[address] + beats[address + 64]
            key = (target, *descriptor_key(record, topology))
            if key not in providers:
                raise ValueError(f"missing timed local provider {key}")
            dispatched.add(address)
            run = providers[key](record)
            if timing is None:
                return run
            dispatch_ps = scheduler.clock.now

            def measured(terminal):
                def finished():
                    timing(key, issue_ps, dispatch_ps, scheduler.clock.now)
                    terminal()

                run(finished)
            return measured

        handle = scheduler.submit_local(target, slot, (address, address + 64), dispatch)
        if handle in pending:
            raise ValueError("duplicate live local handle")
        pending[handle] = address
        return handle

    def wait(handles):
        start = scheduler.clock.now if wait_timing is not None else None
        scheduler.wait_local(handles)
        if wait_timing is not None:
            wait_timing(scheduler.clock.now - start)
        for handle in handles:
            if pending[handle] not in dispatched or not scheduler.local_succeeded(handle):
                raise ValueError("mother WAIT lacks a dispatched and successful local terminal")
            del pending[handle]
        if after_wait is not None:
            after_wait()

    execute(page["instructions"], issue=issue, wait=wait,
            max_steps=page["max_steps"], entry_pc=page["entry_pc"], instruction=instruction)
    if len(offered) * 128 != descriptor_bytes:
        raise ValueError("local CALLs do not exhaust the sealed descriptor extent")
