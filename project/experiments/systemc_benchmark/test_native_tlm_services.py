"""Check descriptor-driven data flow independently of calibrated DDR timings."""

from argparse import ArgumentParser
from pathlib import Path
from struct import pack, pack_into, unpack
import unittest

from native_tlm_attention import Attention
from native_tlm_dma import CommittedMemory, NativeDMA
from native_tlm_projection import Projection, accumulate
from native_tlm_timing import Clock, Dram, S128, Scheduler
from native_tlm_u import UArithmetic, rne


class CallbackDDR:
    def __init__(self, clock):
        self.clock = clock
        self.offered = []

    def submit(self, transfer, done, *, channel=None):
        self.offered.append(transfer)
        self.clock.after(110, done)


class ReorderingDDR(CallbackDDR):
    def submit(self, transfer, done, *, channel=None):
        self.offered.append(transfer)
        self.clock.after(110 + 10 * (3 - (transfer.address // 64) % 4), done)


def record(fmt, *values):
    descriptor = bytearray(128)
    pack_into(fmt, descriptor, 16, *values)
    return bytes(descriptor)


class NativeTLMServicesTest(unittest.TestCase):
    dram_args = None

    def test_bound_local_wait_delays_mother_until_terminal_transport(self):
        clock = Clock()
        dram = CallbackDDR(clock)
        scheduler = Scheduler(clock, dram, lambda _: bytes(64), core_ps=10)
        pm = bytearray(152)
        pack_into("<III", pm, 16, 0, 3, 128)
        pack_into("<QQQ", pm, 128, 0x4100000000000000, 0x4400000000000001,
                  0x4f00000000000000)
        scheduler.bind_local(0, pm)
        dispatch_times = []

        def dispatch(replies):
            self.assertEqual([address for address, _ in replies], [0, 64])
            dispatch_times.append(clock.now)
            return lambda terminal: clock.after(100, terminal)

        handle = scheduler.submit_local(0, 0, (0, 64), dispatch)
        with self.assertRaisesRegex(ValueError, "overlapping"):
            scheduler.submit_local(0, 1, (128, 192), dispatch)
        scheduler.wait_local((handle,))
        self.assertTrue(scheduler.local_succeeded(handle))
        self.assertEqual(dispatch_times, [1830])
        self.assertEqual(clock.now, 2010)

    def test_dma_handoff_reads_only_live_committed_kv(self):
        for bits in (128, 512):
            for pipeline in (False, True):
                with self.subTest(bits=bits, pipeline=pipeline):
                    self.check_dma_handoff(bits, pipeline)

    def check_dma_handoff(self, bits, pipeline):
        clock = Clock()
        if self.dram_args:
            library, config, output = self.dram_args
            directory = output / f"{bits}-{int(pipeline)}"
            directory.mkdir()
            dram = Dram(clock, library, config, directory, credits=1)
        else:
            dram = CallbackDDR(clock)
        memory = CommittedMemory(lambda _: b"x" * 64, [(0x4000, 512, 91)])
        dma = NativeDMA(clock, dram, memory, core_ps=10, pipeline=pipeline)
        source, consumer = [S128(clock, core_ps=10, port_bits=bits) for _ in range(2)]
        source.words = {i: bytes([i]) * 16 for i in range(32)}
        with self.assertRaisesRegex(ValueError, "unbound"):
            memory.begin_write(0x2000, None, bytes(64))
        with self.assertRaisesRegex(ValueError, "unbound"):
            memory.begin_write(0x4000, 92, bytes(64))
        done = []
        descriptor = record("<H6xQQ", 0, 0x4000, 91)
        dma.provider(source, size=512, store=True)(descriptor)(lambda: done.append("store"))
        clock.until(lambda: bool(memory.pending))
        with self.assertRaisesRegex(ValueError, "before"):
            memory(0x4000)
        clock.until(lambda: bool(done))
        self.assertEqual(len(memory.committed), 8)
        descriptor = record("<H6xQ", 512, 0x4000)
        dma.provider(consumer, size=512)(descriptor)(lambda: done.append("load"))
        clock.until(lambda: len(done) == 2)
        self.assertEqual(consumer.words, {512+i: value for i, value in source.words.items()})
        self.assertEqual(dma.stats, {"read_returns": 8, "write_commits": 8})
        self.assertEqual(source.stats["read_beats"], 32 if bits == 128 else 8)
        self.assertEqual(consumer.stats["write_beats"], 32 if bits == 128 else 8)
        if self.dram_args:
            self.assertEqual(dram.stats["callbacks"], 16)
            self.assertEqual(dram.stats["writes"], 8)
            dram.close()

    def test_wide_sram_splits_unaligned_spans_and_commits_only_selected_banks(self):
        for bits, expected in ((128, 6), (512, 3)):
            with self.subTest(bits=bits):
                clock = Clock()
                sram = S128(clock, core_ps=10, port_bits=bits)
                projection = Projection(clock, None, None, sram, sram, source_word=0, scratch_word=16)
                sram.words[2] = sram.words[9] = b"x" * 16
                payload = bytes(range(96))
                done = []
                projection.write_span(sram, 3, payload, lambda: projection.read_span(sram, 3, 6, done.append))
                self.assertEqual(sram.words, {2: b"x" * 16, 9: b"x" * 16})
                clock.until(lambda: bool(done))
                self.assertEqual(done, [payload])
                self.assertEqual(sram.words[2], b"x" * 16)
                self.assertEqual(sram.words[9], b"x" * 16)
                for direction in ("read", "write"):
                    self.assertEqual(sram.stats[f"{direction}_beats"], expected)
                    self.assertEqual(sram.stats[f"{direction}_bytes"], 96)

    def test_add_consumes_sram_and_releases_only_after_write_ack(self):
        clock = Clock()
        sram = S128(clock, core_ps=10)
        u = UArithmetic(clock, sram)
        sram.words = {0: pack("<4i", 5, -3, 11, -9), 512: pack("<4i", -6, 6, -11, 4)}
        done = []
        u.add(record("<4H", 0, 512, 0, 1))(lambda: done.append(sram.words[0]))
        self.assertEqual(sram.words[0], pack("<4i", 5, -3, 11, -9))
        clock.until(lambda: bool(done))
        self.assertEqual(done, [pack("<4i", -1, 3, 0, -5)])
        self.assertGreater(clock.now, 0)

    def test_ffn_down_store_interleaves_real_private_sram_results(self):
        for bits in (128, 512):
            for pipeline in (False, True):
                with self.subTest(bits=bits, pipeline=pipeline):
                    self.check_ffn_down_store(bits, pipeline)

    def check_ffn_down_store(self, bits, pipeline):
        clock = Clock()
        dram = ReorderingDDR(clock)
        memory = CommittedMemory(lambda _: b"", [(8192, 8192, 128)])
        dma = NativeDMA(clock, dram, memory, core_ps=10, pipeline=pipeline)
        banks = [S128(clock, core_ps=10, port_bits=bits) for _ in range(3)]
        expected = b"".join(word.to_bytes(16, "little") for word in range(512))
        for word in range(512):
            group, lane = divmod(word, 2)
            banks[group % 3].words[2 * (group // 3) + lane] = expected[16*word:16*(word+1)]
        done = []
        dma.provider(None, size=8192, store=True, down_sram=banks)(
            record("<8xQQ", 8192, 128))(lambda: done.append(True))
        clock.until(lambda: bool(done))
        self.assertEqual(b"".join(memory(a) for a in range(8192, 16384, 64)), expected)

    def test_signed_round_ties_even(self):
        self.assertEqual([rne(x, 1) for x in (-7, -5, -3, -1, 1, 3, 5, 7)],
                         [-4, -2, -2, 0, 0, 2, 2, 4])

    def test_rope_uses_both_halves_and_commits_all_words(self):
        clock = Clock()
        sram = S128(clock, core_ps=10)
        u = UArithmetic(clock, sram)
        for word in range(32):
            sram.words[word] = pack("<4i", *((word + 1,) * 4))
            sram.words[32+word] = bytes(16)
            sram.words[64+word] = pack("<4i", *((16384,) * 4))
        descriptor = record("<4H10b", 0, 32, 64, 96, 14, 0, 0, 14, 0, 0, -16, -16, -16, -14)
        done = []
        u.rope(descriptor)(lambda: done.append(True))
        clock.until(lambda: bool(done))
        for word in range(32):
            expected = (word ^ 16) + 1
            self.assertEqual(sram.words[96+word], pack("<4i", *((-expected if word < 16 else expected,) * 4)))

    def test_projection_ordinary_and_head16_records(self):
        # Nonuniform lane/position data exposes a K16/lane layout transposition.
        activation = list(range(128))
        weights = [lane - 4 if within == chunk else 0
                   for chunk in range(8) for lane in range(8) for within in range(16)]
        weight_data = pack("<1024b", *weights)
        expected = [sum(chunk * 17 * (lane - 4) for chunk in range(8)) for lane in range(8)]
        for head16 in (False, True):
            scale = pack("<H", 0x3c00) * (64 if head16 else 8)
            record = weight_data + scale + (b"" if head16 else bytes(48))
            prefix = [0]*8
            accumulate(record, activation, 0, prefix, head16)
            self.assertEqual(prefix, expected)

    def test_attention_reads_two_committed_positions_and_writes_weighted_value(self):
        for window in (1, 8):
            for bits in (128, 512):
                for pipeline in (False, True):
                    with self.subTest(window=window, bits=bits, pipeline=pipeline):
                        self.check_attention(window, bits, pipeline)

    def check_attention(self, window, bits, pipeline):
        clock = Clock()
        dram = ReorderingDDR(clock)
        memory = CommittedMemory(lambda _: b"", [(4096, 1024, 64), (8192, 1024, 128)])
        for address, values in ((4096, [0]*128), (4608, [0]*128),
                                (8192, list(range(128))), (8704, list(range(128, 256)))):
            payload = pack("<128i", *values)
            for i in range(8):
                beat = address + i*64
                memory.begin_write(beat, beat//64, payload[i*64:(i+1)*64])()
        sram = S128(clock, core_ps=10, port_bits=bits)
        sram.words.update((i, bytes(16)) for i in range(32))
        aperture = Projection(clock, dram, memory, sram, sram, source_word=0, scratch_word=32)
        attention = Attention(clock, dram, memory, aperture, kv_window=window, pipeline=pipeline)
        descriptor = record("<6HIQQ", 2, 1, 0, 512, 544, 800, 1 << 30, 4096, 8192)
        done = []
        attention.provider(descriptor)(lambda: done.append(True))
        clock.until(lambda: bool(done))
        result = b"".join(sram.words[i] for i in range(800, 832))
        self.assertEqual(unpack("<128i", result), tuple(range(64, 192)))
        self.assertEqual(attention.stats["kv_read_returns"], 80)
        self.assertEqual(len(dram.offered), 80)
        if window > 1 or pipeline:
            self.assertEqual(attention.stats["kv_window_peak"], window)

    def test_attention_ping_pong_keeps_results_and_ddr_addresses(self):
        positions = 69
        observed = []
        for pipeline in (False, True):
            clock = Clock()
            dram = ReorderingDDR(clock)
            sram = S128(clock, core_ps=10, port_bits=512)
            q = pack("<4i", 1, 2, 3, 4)
            sram.words.update((i, q) for i in range(32))
            aperture = Projection(clock, dram, None, sram, sram, source_word=0, scratch_word=32)
            key, value = 65536, 131072
            history = {
                base + row*512 + offset: pack("<16i", *(
                    (row+1)*(offset//4+lane+1) for lane in range(16)))
                for base in (key, value) for row in range(positions) for offset in range(0, 512, 64)
            }
            attention = Attention(clock, dram, history.__getitem__, aperture, kv_window=8, pipeline=pipeline)
            descriptor = record("<6HIQQ", positions, positions-1, 0, 512, 544, 800,
                                1 << 30, key, value)
            done = []
            attention.provider(descriptor)(lambda: done.append(True))
            clock.until(lambda: bool(done))
            observed.append((
                [sram.words[i] for i in range(800, 832)],
                sorted(transfer.address for transfer in dram.offered)))
        self.assertEqual(observed[0], observed[1])


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dram", nargs=3, type=Path, metavar=("LIBRARY", "CONFIG", "OUTPUT"))
    args = parser.parse_args()
    if args.dram:
        args.dram[2].mkdir()
        NativeTLMServicesTest.dram_args = args.dram
    unittest.main(argv=[__file__], verbosity=2)
