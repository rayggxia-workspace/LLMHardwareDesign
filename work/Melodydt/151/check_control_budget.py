"""Check the proposed logical budget/packing; not an RTL test. Python 3.7+."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
contract = json.loads((root / 'static-execution-contract.json').read_text(encoding='utf-8'))
checks = []

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def width(fields):
    return sum(entry[1] for entry in fields)

p = contract['program']
d = contract['command_templates']
c = contract['completion']
r = contract['state_root_design']
check('instruction64', width(p['instruction_fields_LSB_first']) == 64)
check('loop128', width(p['loop_entry_fields_LSB_first']) == 128)
check('stream_template256', width(d['S_stream_record_fields_LSB_first']) == 256)
check('R_template256', width(d['R_record_fields_LSB_first']) == 256)
check('ten_physical_template_captures', d['physical_service_capture_count'] == 10)
check('template_capture640', d['per_service_template_capture_bytes'] * d['physical_service_capture_count'] == d['physical_template_capture_total_bytes'] == 640)
check('ROM_direct_stream_no_second_fetch_bank', d['ROM_streams_directly_to_selected_child_capture'] and d['mother_full_descriptor_cache_bytes'] == 0)
check('completion128', width(c['fields_LSB_first']) == 128)
check('root_ROM512', width(r['static_record_fields_LSB_first']) == 512)
check('root_runtime256', width(r['runtime_fields_LSB_first']) == 256)
check('root32_from_existing_scope', r['selected_product_max_roots'] == max(r['source_counts'].values()))
check('root1024', r['runtime_root_bytes'] == 32 * 32)
for section in ['runtime_storage_estimate', 'permanent_storage_estimate']:
    b = contract[section]
    check(section + '_sum', sum(x['count'] * x['bytes_each'] for x in b['items']) == b['subtotal_bytes'])
    check(section + '_margin', b['subtotal_bytes'] + b['margin_bytes'] == b['budget_point_bytes'])
capture_items = [x for x in contract['runtime_storage_estimate']['items'] if x['name'] == 'per_service_template_capture']
check('physical_capture_cost_in_budget', len(capture_items) == 1 and capture_items[0]['count'] * capture_items[0]['bytes_each'] == 640)
check('corrected_runtime3448_margin648', contract['runtime_storage_estimate']['subtotal_bytes'] == 3448 and contract['runtime_storage_estimate']['margin_bytes'] == 648)
q = contract['permanent_storage_estimate']
check('PC16', q['instruction_count'] < 2 ** q['PC_bits'])
check('param16', q['descriptor_count'] < 2 ** q['descriptor_index_bits'])
check('one_foreground', contract['architecture']['global_foreground_jobs_max'] == 1)
check('same_active_base', contract['same_base']['M1_M10_and_active_geometry_identical_between_products'])
check('no_product_resynthesis', not contract['same_base']['per_product_resynthesis'])
check('no_bootload', not contract['same_base']['bootload'])
check('MEM_deferred_not_absent', contract['memory_scope']['system_has_external_memory'] and contract['memory_scope']['MEM_service_is_deferred_extension'])
check('capacity_unproven', q['capacity_unproven'] and p['capacity_unproven'])
check('no_chip_saving_claim', not contract['runtime_storage_estimate']['total_chip_smaller_claimed'])
files = []
for name in ['static-execution-contract.json', 'control-report.md', 'check_control_budget.py']:
    location = root / name
    if name == 'control-report.md' and not location.exists():
        location = root.parents[2] / 'docs/SAMPLE_ONCHIP_SYSTEM_CONTRACT.md'
    raw = location.read_bytes()
    record_name = 'docs/SAMPLE_ONCHIP_SYSTEM_CONTRACT.md' if name == 'control-report.md' and not (root/name).exists() else name
    files.append({'path': record_name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
print(json.dumps({'passed': True, 'scope': 'logical_specification_only', 'checks': checks, 'artifacts': files}, ensure_ascii=False, indent=2))
