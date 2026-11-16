"""Expand mechanical native-unit wiring in the reviewed physical RTL template."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
NATIVE = ROOT / 'project/rtl/w8a16_v1/m_native_s32.sv'
TEMPLATE = Path(__file__).with_name('m_native_leaf_s32.sv.in')
ACKS = {'alloc_ack_ready', 'fill_ack_ready', 'input_done_ready', 'abort_done_ready',
        'drain_done_ready', 'fault_ready', 'native_fault_ready', 'rsp_ready'}


def continuous(name):
    return name.startswith(('issue_', 'fill_', 'a_')) or name in ACKS


def generate():
    text = NATIVE.read_text()
    header = text[text.index(' input wire clk'):text.index('\n);')]
    header = re.sub(r'//[^\n]*', '', header)
    ports = []
    direction, width = None, ''
    for field in header.split(','):
        field = field.strip()
        match = re.fullmatch(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)', field)
        if match:
            direction, width, name = match.groups()
            width = (width or '').replace('KEY_W-1:0', '127:0')
        else:
            assert re.fullmatch(r'\w+', field), field
            name = field
        ports.append((direction, width, name))
    declarations, defaults, connections = [], [], []
    for direction, width, name in ports:
        if name in ('clk', 'reset'):
            connections.append(f'.{name}({name})')
            continue
        storage = 'reg' if direction == 'input' and not continuous(name) else 'wire'
        declarations.append(f' {storage} {width} n_{name};')
        connections.append(f'.{name}(n_{name})')
        if direction == 'input' and not continuous(name):
            defaults.append(f'  n_{name}=0;')
    result = TEMPLATE.read_text().replace('@DECLARATIONS@', '\n'.join(declarations))
    result = result.replace('@DEFAULTS@', '\n'.join(defaults))
    result = result.replace('@INSTANCE@', " m_native_s32 #(.COMMON_A_SHIFT(1'b1)) native(\n  " + ',\n  '.join(connections) + ');')
    return result


if __name__ == '__main__':
    path = ROOT / 'project/rtl/w8a16_v1/m_native_leaf_s32.sv'
    path.write_text(generate(), newline='\n')
