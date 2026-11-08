"""Fail closed on absent or violated native SRAM clock checks.

The tool must report one minimum-period check and both pulse widths for every
actual bank. This complements setup/hold; it does not replace characterization.
"""
from pathlib import Path
import math
import re


def audit(folder):
    folder = Path(folder)
    clocks = {}
    for line in (folder / 'sram-clocks.tsv').read_text().splitlines():
        pin, clock, period, propagated = line.split('\t')
        assert pin not in clocks and pin.endswith('/clk0')
        assert clock == 'core' and propagated == '1'
        assert math.isfinite(float(period)) and float(period) > 0
        clocks[pin] = dict(clock=clock, period_ns=float(period))
    assert len(clocks) == 4
    periods = (folder / 'sram-period.rpt').read_text()
    pulses = (folder / 'sram-pulse.rpt').read_text()
    violations = (folder / 'sram-clock-violations.rpt').read_text()
    assert not violations.strip(), violations
    assert '(VIOLATED)' not in periods + pulses
    for pin in clocks:
        for text, suffix in [(periods, ''), (pulses, ' (high)'), (pulses, ' (low)')]:
            rows = [line for line in text.splitlines()
                    if re.match(r'^' + re.escape(pin + suffix) + r'\s+', line)]
            assert len(rows) == 1 and rows[0].endswith('(MET)'), (pin, suffix, rows)
            values = rows[0][len(pin + suffix):].split()
            assert len(values) == 4 and values[-1] == '(MET)', rows
            required, actual, slack = map(float, values[:3])
            assert all(map(math.isfinite, (required, actual, slack)))
            assert required > 0 and actual > 0 and slack >= 0
    return dict(passed=True, clocks=clocks, bank_period_checks=4,
                bank_high_pulse_checks=4, bank_low_pulse_checks=4)
