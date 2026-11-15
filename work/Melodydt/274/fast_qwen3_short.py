"""Use #270's cycle-preserving batched DDR adapter with the short replay."""
import heapq
import os
from pathlib import Path
import sys

from fast_tlm_replay import DramBridge, TICK_PS
from native_tlm_timing import Clock

import qwen3_short as replay


class BatchedClock(Clock):
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
                limit = time if time == dram.next_tick else time - 1
            elif dram.pending:
                limit = dram.next_tick + 4096*TICK_PS
            else:
                raise RuntimeError("native TLM deadlock")
            dram.advance(limit)


if __name__ == "__main__":
    if os.environ.get("SHORT_PROJECTION_MATH"):
        import native_tlm_projection
        from projection_math import NativeAccumulator
        native_tlm_projection.accumulate = NativeAccumulator(Path(os.environ["SHORT_PROJECTION_MATH"]))
    replay.Clock = BatchedClock
    replay.Dram = DramBridge
    sys.argv[0] = replay.__file__
    replay.main()
