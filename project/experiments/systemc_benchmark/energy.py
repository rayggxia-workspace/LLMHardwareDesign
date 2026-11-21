"""Activity energy accounting, with no implied coefficients or free components.

SI boundary: W, J, ps. Power-tool conversion is required: Nangate and SRAM
libraries do not necessarily use the same power unit. This supplies accounting,
not a validation of coefficient provenance or compressed-trace equivalence.
"""
import math


def nonnegative(value, label):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or value < 0):
        raise ValueError('invalid ' + label)
    return value


def integrate(makespan_ps, required_instances, calibrations, events):
    """Idle includes local clocks/leakage, increments exclude that same idle.

    Parent clocks, controls, wiring and DDR outside leaf calibration must be
    separate required instances. Unknown entries leave total energy null.
    """
    nonnegative(makespan_ps, 'duration')
    names = list(required_instances)
    if not names or makespan_ps == 0 or len(names) != len(set(names)):
        raise ValueError('nonempty unique hardware and positive duration required')
    required = set(names)
    if set(calibrations) - required:
        raise ValueError('calibration for undeclared instance')
    missing, energy, provenance = set(), {}, {}
    for name in names:
        c = calibrations.get(name)
        if not c or c.get('idle_w') is None:
            missing.add(name + ':idle')
            continue
        if c.get('coefficient_class') != 'activity_calibrated' or not c.get('evidence_sha256'):
            missing.add(name + ':calibration_evidence')
        energy[name] = nonnegative(c['idle_w'], 'idle power') * makespan_ps * 1e-12
        provenance[name] = c.get('evidence_sha256')
    for event in events:
        name, command = event['instance'], event['command']
        if name not in required:
            raise ValueError('event for undeclared instance')
        count = event['count']
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError('positive integer event count required')
        coeff = calibrations.get(name, {}).get('commands', {}).get(command)
        if coeff is None:
            missing.add(name + ':' + command)
            continue
        # Do not silently clamp noisy negative subtractions into free savings.
        delta = nonnegative(coeff.get('incremental_j'), 'incremental energy')
        if not coeff.get('evidence_sha256'):
            missing.add(name + ':' + command + ':evidence')
        energy[name] = energy.get(name, 0.) + count * delta
    known = math.fsum(energy.values())
    if not math.isfinite(known):
        raise ValueError('energy overflow')
    return {'complete': not missing, 'joules': known if not missing else None,
            'known_subtotal_j': known, 'known_by_instance_j': energy,
            'missing': sorted(missing), 'calibration_evidence': provenance,
            'boundary': 'accounting only; independent calibration/scope audit required'}
