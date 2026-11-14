import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tlm_sram import Sram, load_sram_profile


class SramTest(unittest.TestCase):
    def test_aligned_and_unaligned_width_conversion(self):
        sram = Sram('U0', 16384, 512, 512)
        self.assertEqual(sram.beats(0, 4, write=False, service_bits=512), [(0, 4)])
        self.assertEqual(sram.beats(1, 9, write=False, service_bits=512),
                         [(1, 3), (4, 4), (8, 2)])
        self.assertEqual(sram.beats(1024, 0, write=True, service_bits=512), [])
        narrow = Sram('U0', 16384, 128, 128)
        self.assertEqual(len(narrow.beats(0, 512, write=False, service_bits=512)), 512)
        self.assertEqual(len(sram.beats(0, 512, write=False, service_bits=512)), 128)

    def test_service_and_port_both_limit_write_grouping(self):
        for port_bits in (128, 512):
            sram = Sram('U0', 16384, 512, port_bits)
            gather = sram.beats(512, 512, write=True, service_bits=128)
            self.assertEqual(gather, [(word, 1) for word in range(512, 1024)])
            coalesced = sram.beats(512, 512, write=True, service_bits=512)
            self.assertEqual(len(coalesced), 512 if port_bits == 128 else 128)

    def test_invalid_width_or_outside_instance(self):
        with self.assertRaisesRegex(ValueError, 'width'):
            Sram('U0', 16384, 256, 0)
        with self.assertRaisesRegex(ValueError, 'outside'):
            Sram('U0', 16384, 512, 128).beats(1023, 2, write=True, service_bits=128)

    def test_profile_keeps_instances_on_the_selected_base(self):
        config = {
            'base_sha256': 'a' * 64,
            'sram': {
                'U0.data': dict(assembly='U0', capacity_bytes=16384, read_bits=512, write_bits=128),
                'U0.pm': dict(assembly='U0', capacity_bytes=2048, read_bits=128, write_bits=128),
                'P0.data': dict(assembly='P0', capacity_bytes=16384, read_bits=128, write_bits=128),
            },
        }
        with TemporaryDirectory() as scratch:
            path = Path(scratch) / 'sram.json'
            path.write_text(json.dumps(config))
            instances, checksum = load_sram_profile(path, 'a' * 64, {'U0', 'P0'})
            self.assertEqual(instances['U0.data'].read_bits, 512)
            self.assertEqual(instances['U0.pm'].read_bits, 128)
            self.assertEqual(instances['P0.data'].read_bits, 128)
            self.assertEqual(len(checksum), 64)
            with self.assertRaisesRegex(ValueError, 'different base'):
                load_sram_profile(path, 'b' * 64, {'U0', 'P0'})
            with self.assertRaisesRegex(ValueError, 'P0.data: SRAM assembly'):
                load_sram_profile(path, 'a' * 64, {'U0'})


if __name__ == '__main__':
    unittest.main()

