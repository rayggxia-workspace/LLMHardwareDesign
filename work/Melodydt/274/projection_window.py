"""Use a bounded in-record DDR window with the archived native projection."""
from native_tlm_projection import Projection
from native_tlm_timing import Transfer


class WindowedProjection(Projection):
    def __init__(self, *args, weight_window, **kwargs):
        super().__init__(*args, **kwargs)
        self.weight_window = weight_window

    def fetch(self, base, size, done):
        expected = size // 64
        if base % 64 or size % 64 or size not in (1088, 1152):
            raise ValueError("invalid projection weight record")
        payload = [None] * expected
        issued = returned = 0
        channel = (base >> 11) & 1

        def pump():
            nonlocal issued
            while issued < expected and issued-returned < self.weight_window:
                index = issued
                address = base + index*64
                issued += 1
                self.dram.submit(Transfer(address), lambda i=index, a=address: receive(i, a), channel=channel)

        def receive(index, address):
            nonlocal returned
            if payload[index] is not None:
                raise ValueError("duplicate projection weight beat")
            self.stats["weight_read_returns"] += 1
            payload[index] = self.memory(address)
            returned += 1
            if returned == expected:
                done(b"".join(payload))
            else:
                pump()

        pump()
