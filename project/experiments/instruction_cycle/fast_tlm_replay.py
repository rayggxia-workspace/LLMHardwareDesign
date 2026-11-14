"""Execute the sealed two-step TLM with a batched, cycle-preserving DDR bridge."""

import argparse
from collections import Counter
import ctypes
import heapq
from pathlib import Path
import sys


TICK_PS = 630
U64 = ctypes.c_uint64
STAT_KEYS = (
    "reads", "writes", "callbacks", "ddr_queue_ps", "ddr_inflight_ps",
    "dram_backpressure_ticks", "dma_issue_throttle_ticks", "dma_credit_wait_ticks",
    "channel0_peak_queued", "channel1_peak_queued", "channel0_peak_active", "channel1_peak_active",
)


class DramBridge:
    """Keep completions in native tick order, with Python callbacks on the event heap."""

    def __init__(self, clock, library, config, output, *, credits, core_ps=None):
        self.clock = clock
        self.next_tick = TICK_PS
        self.tick_order = next(clock.sequence)
        self.pending = {}
        self.identifier = 0
        self.lib = ctypes.CDLL(str(library))
        char = ctypes.c_char_p
        pointer = ctypes.c_void_p
        integer = ctypes.c_int
        u64_out = ctypes.POINTER(U64)
        for name, result, arguments in (
            ("open", pointer, (char, char, char, ctypes.c_uint32, U64)),
            ("submit", integer, (pointer, U64, U64, integer, integer, U64)),
            ("advance", U64, (pointer, U64)),
            ("pop", integer, (pointer, u64_out)),
            ("stats", integer, (pointer, u64_out)),
            ("close", integer, (pointer,)),
            ("error", char, (pointer,)),
        ):
            function = getattr(self.lib, "fast_dram_" + name)
            function.restype, function.argtypes = result, arguments
        directories = [output / "channel0", output / "channel1"]
        for directory in directories:
            directory.mkdir()
        self.handle = self.lib.fast_dram_open(
            str(config).encode(), *(str(path).encode() for path in directories), credits, core_ps or 0)
        self.check(self.handle is not None)
        self.completion = U64()
        self.stats_buffer = (U64 * len(STAT_KEYS))()
        clock.dram = self

    def check(self, valid):
        if not valid:
            message = self.lib.fast_dram_error(self.handle)
            raise RuntimeError(message.decode() if message else "fast DRAMsim3 bridge failed")

    def submit(self, transfer, done, *, channel=None):
        address = transfer.address
        if address % 64 or not 0 <= address < 16 * (1 << 30):
            raise ValueError("native DDR beat is outside the channel capacity")
        if channel is None:
            channel = (address >> 6) & 1
        identifier = self.identifier
        self.identifier += 1
        self.check(self.lib.fast_dram_submit(self.handle, identifier, address, transfer.payload is not None,
                                             channel, self.clock.now) == 1)
        self.pending[identifier] = done

    @property
    def stats(self):
        self.check(self.lib.fast_dram_stats(self.handle, self.stats_buffer) == 1)
        return Counter({key: value for key, value in zip(STAT_KEYS, self.stats_buffer) if value})

    def advance(self, limit):
        last = self.lib.fast_dram_advance(self.handle, limit)
        self.check(self.next_tick <= last <= limit)
        self.clock.now = last
        self.next_tick = last + TICK_PS
        while True:
            status = self.lib.fast_dram_pop(self.handle, ctypes.byref(self.completion))
            self.check(status >= 0)
            if not status:
                break
            self.clock.after(0, self.pending.pop(self.completion.value))
        self.tick_order = next(self.clock.sequence)

    def close(self):
        if self.pending:
            raise RuntimeError("DDR closed before drain")
        self.check(self.lib.fast_dram_close(self.handle) == 1)
        self.handle = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--fast-ddr", action="store_true")
    parser.add_argument("--pages", type=int, default=0, help="stop at a diagnostic page boundary")
    args, replay_args = parser.parse_known_args()
    if args.pages < 0:
        parser.error("--pages must be nonnegative")
    sys.path.insert(0, str(args.archive.resolve()))
    import native_tlm_timing as timing

    if args.fast_ddr:
        class BatchedClock(timing.Clock):
            dram = None

            def until(self, complete):
                while not complete():
                    dram = self.dram
                    if self.events:
                        time, order, _ = self.events[0]
                        if (time, order) < (dram.next_tick, dram.tick_order):
                            self.now, _, callback = heapq.heappop(self.events)
                            callback()
                            continue
                        # For a later equal-time event, the last tick below it
                        # first assigns the next DDR tick's actual heap order.
                        limit = time if time == dram.next_tick else time - 1
                    elif dram.pending:
                        limit = dram.next_tick + 4096 * TICK_PS
                    else:
                        raise RuntimeError("native TLM deadlock")
                    dram.advance(limit)

        timing.Clock = BatchedClock
        timing.Dram = DramBridge

    import run_native_tlm_request as replay

    class PrefixComplete(Exception):
        pass

    if args.pages:
        original_export = replay.export

        def limited_export(*params, **options):
            for index, page in enumerate(original_export(*params, **options)):
                if index == args.pages:
                    raise PrefixComplete
                yield page

        replay.export = limited_export
    sys.argv = [replay.__file__, *replay_args]
    try:
        replay.main()
    except PrefixComplete:
        print("Completed {} diagnostic pages".format(args.pages))


if __name__ == "__main__":
    main()
