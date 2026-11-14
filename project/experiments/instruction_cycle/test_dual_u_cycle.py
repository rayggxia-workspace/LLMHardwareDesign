import unittest

from dual_u_cycle import log_events
from dual_u_services import Services


SUMMARY = "GENERATED_CONTROL_PASS cycles=21 commits=3 confirmed_bytes=80 pm_requests=4\n"


class DualUValidationTest(unittest.TestCase):
    def test_start_cannot_replace_prior_window_without_reset(self):
        log = "START cycle=5\nSTART cycle=9\n" + SUMMARY
        for allow_restart in (False, True):
            with self.assertRaisesRegex(ValueError, "duplicate START"):
                log_events(log, allow_restart=allow_restart)
        reset = "START cycle=5\nEPOCH_BEGIN cycle=8\nSTART cycle=9\n" + SUMMARY
        self.assertEqual(log_events(reset, allow_restart=True)[0], 9)

    def test_rejects_out_of_order_summary_and_duplicate_event_fields(self):
        with self.assertRaisesRegex(ValueError, "out-of-order"):
            log_events(SUMMARY + "START cycle=9\n")
        with self.assertRaisesRegex(ValueError, "duplicate RTL event field"):
            log_events("START cycle=9\nFETCH kind=MC addr=128 addr=144 cycle=10\n" + SUMMARY)
        with self.assertRaisesRegex(ValueError, "after completion summary"):
            log_events("START cycle=9\n" + SUMMARY + "FETCH kind=MC addr=144 cycle=20\n")
        with self.assertRaisesRegex(ValueError, "outside a START window"):
            log_events("FETCH kind=MC addr=128 cycle=8\nSTART cycle=9\n" + SUMMARY)
        with self.assertRaisesRegex(ValueError, "epoch edges are out of order"):
            log_events("START cycle=5\nEPOCH_BEGIN cycle=2\nSTART cycle=9\n" + SUMMARY, allow_restart=True)

    def test_local_e_and_incoming_copy_compete_for_one_private_s(self):
        def service(op, n0, n1=0, n2=0):
            return dict(native_op=op, native0=n0, native1=n1, native2=n2)

        sim = Services({0: {40: 1, 41: 2}, 1: {40: 3}}, request_period=7, request_phase=2)
        schedule = {0: {0: service(0x103, 60), 1: service(0x101, 40 | (60 << 10))},
                    2: {0: service(0x100, 24 | (42 << 5), 40 | (41 << 10))}}
        for cycle in range(26):
            sim.step(cycle, schedule.get(cycle, {}), {0: True, 1: True})
        events = sim.events
        self.assertIn(dict(cycle=9, kind="S_CONTEND", block=0, mask=6), events)
        self.assertIn(dict(cycle=9, kind="S_GRANT", block=0, client=2, addr=60, write=1), events)
        self.assertIn(dict(cycle=13, kind="S_GRANT", block=0, client=1, addr=41, write=0), events)
        self.assertEqual(sim.memory[0][60], 3)
        self.assertEqual(sim.memory[0][42], 3)
