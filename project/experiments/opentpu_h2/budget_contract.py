"""Derive the v01 resource contract from sealed native H1 measurements."""
import collections
import hashlib
import gzip
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
results=HERE/'results'
evidence=results/'budget-03'
terminal=json.loads((evidence/'terminal.json').read_text())
assert 'COMPLETED|0:0|' in terminal['sacct'] and terminal['sacct'].endswith('|UNLIMITED')
raw=gzip.decompress((evidence/'electrical-budget.rpt.gz').read_bytes())
report=raw.decode()
assert hashlib.sha256(raw).hexdigest()==terminal['manifest']['electrical-budget.rpt']
slew,cap=report.split('\nmax capacitance\n')
def rows(text):
    found=[]
    for pin,limit,actual,slack,status in re.findall(r'^\s*(\S+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+\((MET|VIOLATED)\)',text,re.M):
        found.append(dict(pin=pin,limit=float(limit),actual=float(actual),slack=float(slack),status=status))
    assert found and all(r['status']=='MET' and r['slack']>=0 for r in found)
    return found
slew,cap=rows(slew),rows(cap)
inventory=results/'inventory-03'/'active-inventory.tsv.gz'
# Native original bytes downloaded from inventory-03, never inferred counts.
invterminal=json.loads((results/'inventory-03'/'terminal.json').read_text())
raw=gzip.decompress(inventory.read_bytes())
assert hashlib.sha256(raw).hexdigest()==invterminal['manifest']['active-inventory.tsv']
instances=[row.split('\t') for row in raw.decode().splitlines()]
counts=collections.Counter(row[1] for row in instances)
active={k:v for k,v in counts.items() if not k.startswith(('FILLCELL','TAPCELL','llhd_'))}
clock=[dict(zip(['name','master','xy_dbu','orient','status'],row)) for row in instances if row[0].startswith(('clkbuf_','clkload'))]
assert len(clock)==4 and collections.Counter(r['master'] for r in clock)=={'BUF_X16':3,'INV_X32':1}
macro_slew=[r for r in slew if r['pin'].startswith(('u_act/','u_mxu/'))]
macro_cap=[r for r in cap if r['pin'].startswith(('u_act/','u_mxu/'))]
contract=dict(version='h2-opentpu-target-conditioned-v01',state='candidate; no qualified H2 route yet',
    source_h1_commit='ce5896de47921fcdc422c4ac9c05cefcb6666bff',source_h1_attempt='top-split-reuse-20-01',
    inventory_manifest_sha256=invterminal['manifest_sha256'],budget_manifest_sha256=terminal['manifest_sha256'],
    clock_ns=2.5,io_delay_ns=.5,input_driver='BUF_X4/Z',output_load_fF=5,clock_input_transition_ns=.05,
    initial_compute_mapped_cells=169109,dff=37023,synthetic_sram=12,external_bits=1662,boundary_bits=685,
    parent_instances_including_fill_tap_macros=len(instances),parent_active_support_counts=active,
    parent_active_support_total=sum(active.values()),parent_clock_resources=clock,
    parent_data_support_count=sum(active.values())-len(clock),
    post_freeze_active_additions_allowed=0,post_freeze_active_master_or_position_changes_allowed=0,
    custom_metals=['metal8','metal9','metal10'],custom_vias=['via8','via9'],
    fixed_access='All native V7 signal landings prepaid and frozen; no new/moved V7 or lower via. Lower data conductors and all clock/PG conductors fixed.',
    manufacturing_boundary='M1-M7 can precede customization. Block M8-M9, V7 landing patterns and any upper fixed clock/PG geometry remain post-fixed manufacturing; no literal 3-mask or only-3-process claim.',
    electrical_units=dict(slew='ns',capacitance='fF'),
    actual_h1_macro_wns_ns=dict(setup=.075443432,hold=.074719347),
    min_macro_slew_headroom=min(macro_slew,key=lambda r:r['slack']),
    min_macro_cap_headroom=min(macro_cap,key=lambda r:r['slack']),
    electrical_row_counts=dict(slew=len(slew),cap=len(cap),macro_slew=len(macro_slew),macro_cap=len(macro_cap)),
    macro_pin_slew_budget=macro_slew,macro_pin_cap_budget=macro_cap,
    acceptance='Original absolute electrical/setup/hold/DRC/antenna/PG limits, full hierarchical extraction and RC coverage; no post-freeze repair of active devices.',
    scope='Single openTPU H1-conditioned access/wire inventory, not independent multi-graph base or manufacturing signoff. Abstract macro budgets do not replace child-internal load and full-hierarchy STA.')
(results/'resource-contract-v01.json').write_text(json.dumps(contract,indent=2)+'\n')
print(json.dumps({k:v for k,v in contract.items() if not k.startswith('macro_pin')},indent=2))
