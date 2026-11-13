"""Materialize shape-specific services from actual leaf-command measurements.

No model names or instance counts occur here. Macro kinds remain the native
M/N/E/G/R/S/T families; inventory, capacities and measurements are inputs.
"""
from copy import deepcopy
import hashlib
import json
import re


def read_profiles(logs):
    if len(logs) != 3 or any(text.count('NATIVE_LEAF_PROBE_PASS seed=219') != 1 for text in logs):
        raise ValueError('three successful native initializations required')
    parsed = []
    for log in logs:
        profile = {}
        for line in log.splitlines():
            if not line.startswith('LEAF '):
                continue
            fields = dict(re.findall(r'(\w+)=([\w-]+)', line))
            kind = fields.pop('kind')
            ticks = int(fields.pop('ticks', fields.pop('execute_ticks', '0')))
            key = kind + ':' + json.dumps({k: int(v) for k, v in fields.items()}, sort_keys=True, separators=(',', ':'))
            if ticks <= 0 or key in profile and profile[key] != ticks:
                raise ValueError('nonpositive or inconsistent native timing')
            profile[key] = ticks
        parsed.append(profile)
    if not parsed[0] or parsed[0] != parsed[1] or parsed[0] != parsed[2]:
        raise ValueError('native profiles differ across initialization states')
    return {'measurements': parsed[0], 'logs_sha256': [hashlib.sha256(s.encode()).hexdigest() for s in logs],
            'scope': 'serialized native leaf driver; primitive numeric checks, not full LC/S integration'}


def duration(profile, kind, **parameters):
    key = kind + ':' + json.dumps(parameters, sort_keys=True, separators=(',', ':'))
    try:
        return profile['measurements'][key]
    except KeyError as exc:
        raise ValueError('no measured native command for ' + key) from exc


def inventory(hardware, profile, groups):
    """Append supplied control groups and their actual macro resources."""
    h = deepcopy(hardware)
    h['native_leaf_profiles'] = deepcopy(profile)
    h['leaf_inventory'] = deepcopy(groups)
    for group, meta in groups.items():
        site = meta['site']
        if site not in h['sites']:
            h['sites'][site] = {k: v for k, v in meta.items() if k not in ('site', 'macros')}
        if h['sites'][site]['words'] != meta['words']:
            raise ValueError('inconsistent private S capacity')
        port, control = meta['io_resource'], group + '.LC.service'
        h['resources'].setdefault(port, 1)
        h['resources'][control] = 1
        for macro in meta['macros']:
            instance = group + '.' + macro
            h['resources'][instance] = 1
            if macro in ('M', 'N', 'R', 'T'):
                h['resources'][instance + '.context'] = 1
                for service in h['services'].values():
                    if instance in service['resources']:
                        service.setdefault('state_resource', instance + '.context')
            for direction in ('read', 'write'):
                h['nets'].setdefault(instance + '.' + direction, {'cost': 1, 'fixed': False,
                    'unit': 'logical interface bundle', 'qualification': 'demand; pins and static wiring remain to bind'})
    return h


def register(hardware, macro, op, numeric, attributes, inputs, outputs, core_ticks, program, *, stateful=False, scratch=0):
    """Return matching real instances, with explicit conservative S accesses."""
    services = []
    for group, meta in hardware['leaf_inventory'].items():
        if macro not in meta['macros']:
            continue
        allowed = meta.get('operations', {}).get(macro)
        if allowed is not None and op not in allowed:
            continue
        instance = group + '.' + macro
        signature = [macro, op, numeric, attributes, inputs, outputs, program]
        digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:20]
        sid = instance + ':' + digest
        reads, writes = sum(inputs), sum(outputs)
        service = {'op': op, 'numeric': numeric, 'attributes': deepcopy(attributes),
                   'site': meta['site'], 'input_words': list(inputs), 'output_words': list(outputs),
                   'ticks': core_ticks + reads * meta['io_read_ticks'] + writes * meta['io_write_ticks'],
                   'resources': [instance, meta['io_resource'], group + '.LC.service'],
                   'controller': group + '.LC',
                   'nets': [instance + '.read', instance + '.write'], 'qualified': True,
                   'native_program': deepcopy(program), 'scratch_words': scratch,
                   'qualification_scope': 'measured native primitive program plus serialized measured S IO',
                   'integrated_lc_timing_qualified': False,
                   'timing_components': {'native': core_ticks, 's_read_words': reads, 's_write_words': writes}}
        if stateful:
            service['state_resource'] = instance + '.context'
        if sid in hardware['services'] and hardware['services'][sid] != service:
            raise ValueError('recipe service identity collision')
        hardware['services'][sid] = service
        services.append(sid)
    if not services:
        raise ValueError('no supplied inventory instance contains macro ' + macro)
    return services
