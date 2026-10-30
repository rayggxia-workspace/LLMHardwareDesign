"""Compare exact 12-decimal tokens with a receipt-bound native reference.

Timing slacks and violation counts are never adjusted by this parser.
"""
from decimal import Decimal
import re
def audit(text, pins, budget, reference):
    from constraint_readback import audit as legacy
    assert sum(line.startswith('create_clock ')for line in text.splitlines()) == 1
    assert 'set_max_delay'not in text and 'set_min_delay'not in text
    normalized = []
    for line in text.splitlines():
        value = None
        key = None
        token_index = 1
        if line.startswith('create_clock '):
            key='clock_ns';value = budget[key];token_index = 4
        elif line.startswith('set_clock_transition '):
            key='clock_transition_ns';value = budget[key]
        elif line.startswith('set_clock_uncertainty '):
            key='uncertainty_ns';value = budget[key]
        elif line.startswith(('set_input_delay ', 'set_output_delay ')):
            kind = 'input' if line.startswith('set_input_delay ') else 'output'
            minimum = ' -min ' in line
            assert minimum != (' -max ' in line)
            key=kind+'_delay_'+('min' if minimum else 'max')+'_ns';value = budget[key]
        elif line.startswith('set_load '):
            key='output_load_ff';value = budget['output_load_pf']*1000;token_index = 2
        elif line.startswith('set_driving_cell '):
            for flag in ['-input_transition_rise', '-input_transition_fall']:
                match = re.search(re.escape(flag)+r' (\S+)', line)
                assert match and Decimal(match.group(1)) == 0
                line = line[:match.start(1)]+'0.0000'+line[match.end(1):]
        if value is not None:
            tokens = list(re.finditer(r'\S+', line))
            match = tokens[token_index]
            observed = Decimal(match.group())
            assert observed == Decimal(reference[key]), ('Unexpected native serialization', line, reference[key])
            # Coverage/grammar remain checked by the unchanged baseline parser.
            line = line[:match.start()]+str(value)+line[match.end():]
        normalized.append(line)
    result = legacy('\n'.join(normalized)+'\n', pins, budget)
    result.update(serialization_digits=12,
                  serialization_model='Exact tokens from same-tool approved-budget native fixture, receipt-bound with negative controls',
                  numerical_slack_tolerance_added=False)
    return result
