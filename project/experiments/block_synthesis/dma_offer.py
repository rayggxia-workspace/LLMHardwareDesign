"""Registered two-lane offer arbitration in the #251 typed DMA fabric."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DmaOfferChannel:
    entries: tuple[int | None, int | None] = (None, None)
    previous_issues: int = 0
    cursor: int = 0

    def advance(self, reserved, ready):
        """Sample lane READY, then fill slots for the next edge.

        Reserved is a bitmap of the 32 physical beat entries for this channel.
        It excludes entries with a successful cancellation on this edge.
        """
        entries = list(self.entries)
        issued = 0
        for lane, entry in enumerate(entries):
            if entry is not None and ready & (1 << lane):
                issued += 1
                entries[lane] = None

        held = sum(entry is not None for entry in entries)
        budget = 4 - self.previous_issues - issued - held
        cursor = self.cursor
        for lane, entry in enumerate(entries):
            if entry is not None or budget <= 0 or not reserved:
                continue
            for offset in range(32):
                candidate = (cursor + offset) % 32
                if reserved & (1 << candidate):
                    entries[lane] = candidate
                    cursor = (candidate + 1) % 32
                    reserved &= ~(1 << candidate)
                    budget -= 1
                    break
        return DmaOfferChannel(tuple(entries), issued, cursor)
