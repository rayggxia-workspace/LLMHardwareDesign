import unittest

from a2_cycle import ProgramMemory, observed_jobs
from s_arbiter import Request, simulate


class A2BoundaryTest(unittest.TestCase):
    def test_program_memory_gates_absolute_edges_and_registers_response(self):
        beats = []
        pm = ProgramMemory("PM", 2, lambda edge, kind, address: beats.append((edge, address)))
        self.assertEqual(pm.read(4, 128, 32), 20)
        self.assertEqual(beats, [(5, 128), (15, 144)])
        with self.assertRaisesRegex(ValueError, "unaligned"):
            pm.read(0, 132)

    def test_log_cannot_drop_a_reused_job(self):
        log = "A2 10 START 7 1 1\nA2 20 RESULT 7 1 1 0 128 16\nPASS A2 jobs=2 status=0 cycles=21\n"
        with self.assertRaisesRegex(ValueError, "incomplete"):
            observed_jobs(log, "start")

    def test_log_excludes_config_reads_but_requires_monotonic_runtime_edges(self):
        log = ("A2 2 MCPM 0\nA2 10 START 7 1 1\nA2 13 MCPM 128\n"
               "A2 12 LCPM 176\nA2 20 RESULT 7 1 1 0 128 16\nPASS A2 jobs=1 status=0 cycles=21\n")
        with self.assertRaisesRegex(ValueError, "out of order"):
            observed_jobs(log, "start")

    def test_narrow_arbiter_rejects_non_integer_clock_and_addresses(self):
        for request, latency, stalls in ((Request(0.5, 0, 0, 1), 2, []),
                                        (Request(0, 0, 1.5, 1), 2, []),
                                        (Request(0, 0, 0, 1), True, []),
                                        (Request(0, 0, 0, 1), 2, [(1, 2.5)])):
            with self.subTest(request=request, latency=latency, stalls=stalls):
                with self.assertRaises(ValueError):
                    simulate([[request]], stalls, [[]], latency)
