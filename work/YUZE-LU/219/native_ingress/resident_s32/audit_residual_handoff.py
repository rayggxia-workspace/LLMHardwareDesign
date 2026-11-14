"""Read back the stored-link boundary of the C0 resident proof."""

import json
from pathlib import Path
from hashlib import sha256
import re

from route_contract import read_base
from verify_candidate_algo2 import verify_candidate


DATA_WIDTH = 128
OUTBOUND = 'decode.index.transport'


def read(path):
    return json.loads(path.read_bytes())


def view_bytes(base, root, key):
    view = base['views'][key]
    payload = (root / Path(view['path'])).read_bytes()
    if sha256(payload).hexdigest() != view['sha256']:
        raise ValueError(f'changed physical view: {key}')
    return payload


def def_bus(base, root, view, signal, direction):
    text = view_bytes(base, root, view).decode('ascii')
    pins = text.split('\nPINS ', 1)[1].split('\nEND PINS', 1)[0]
    declarations = dict(re.findall(r'^\s+- ' + re.escape(signal) + r'\[(\d+)\]([^;]*);',
                                   pins, flags=re.MULTILINE))
    if set(declarations) != {str(i) for i in range(DATA_WIDTH)} or any(
            f'+ DIRECTION {direction}' not in row for row in declarations.values()):
        raise ValueError(f'physical pad direction or width differs: {view}/{signal}')
    return sum(bool(re.search(r'\+ LAYER (?:M10|metal10)\s', row)) for row in declarations.values())


def audit_data_paths(base_path, handoff):
    base = read_base(base_path)
    spec = read(handoff / 'algorithm2-input.json')
    readback = verify_candidate(spec, handoff, base_path)
    requirements = read(handoff / 'requirements.json')
    members = [row for row in requirements['members'] if row['demand_id'] == OUTBOUND]
    data = sorted((row['bit'], row['driver'], row['sinks']) for row in members if row['signal'] == 'data')
    expected_data = [(i, f'C0/outgoing_data[{i}]', [f'U0/incoming_data[{i}]'])
                     for i in range(DATA_WIDTH)]
    expected_control_widths = dict(address=10, valid=1, ready=1, stored_ack=1, ack_ready=1,
                                   reserved=1, reserved_address=10)
    control_widths = {port: sum(row['signal'] == port for row in members)
                      for port in expected_control_widths}
    if data != expected_data or control_widths != expected_control_widths or len(members) != 153:
        raise ValueError('candidate no longer contains the pinned outbound stored-link')
    endpoints = base['endpoints']
    for member in members:
        if (endpoints[member['driver']]['role'] != 'driver'
                or any(endpoints[sink]['role'] != 'sink' for sink in member['sinks'])):
            raise ValueError('stored-link endpoints do not match their access roles')

    # U1 has a placed DEF. U0 is a staged replacement whose declared
    # endpoint plan is narrower than the netlist's interface.
    u1 = def_bus(base, base_path.parent, 'U.def', 'outgoing_data', 'OUTPUT')
    c0 = def_bus(base, base_path.parent, 'C.def', 'rx_data', 'INPUT')
    staged_plan = view_bytes(base, base_path.parent, 'U.Gather.endpoint_plan').decode('ascii')
    staged_pins = {row.split('\t', 1)[0] for row in staged_plan.splitlines()[1:]}
    u0 = sum(f'outgoing_data[{i}]' in staged_pins for i in range(DATA_WIDTH))
    if c0 != DATA_WIDTH or u0 == DATA_WIDTH or u1 == DATA_WIDTH:
        raise ValueError('ingress access changed; re-evaluate the residual mapping')
    return dict(
        outbound=dict(demand=OUTBOUND, signals=len(members), router_input_sha256=readback['router_input_sha256'],
                      status='existing_candidate_interface_for_index_transfer'),
        inbound=dict(c0_rx_m10=c0, u1_tx_m10=u1, u0_staged_tx_m10=u0,
                     status='input_operand_supply_unresolved'),
    )
