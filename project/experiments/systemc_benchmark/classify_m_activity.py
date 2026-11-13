"""Audit remaining diode activity pins against OpenDB and original Liberty.

Does not turn a sampled zero-delay gate estimate into complete chip energy.
The diode input load remains in the extracted circuit; no load is removed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for name in ('unannotated','physical_identities','db_log','liberty','output'):
        p.add_argument(name,type=Path)
    p.add_argument('--sample-label', default='M')
    p.add_argument('--annotated-count', type=int)
    a=p.parse_args()
    text=a.unannotated.read_text(); count=re.findall(r'(?m)^unannotated\s+(\d+)$',text)
    if len(count)!=1:raise ValueError('activity count absent')
    pins={x.strip() for x in text.split('Unannotated pins:',1)[1].splitlines() if x.strip()}
    rows=[x.split() for x in a.physical_identities.read_text().splitlines()]
    if not rows or any(len(x)!=2 or x[1]!='ANTENNA_X1' or not x[0].endswith('/A') for x in rows):
        raise ValueError('unclassified or non-input-diode pin')
    if len(pins)!=int(count[0]) or len(rows)!=len(pins) or {x[0] for x in rows}!=pins:
        raise ValueError('physical and activity identities differ')
    marker='PHYSICAL_UNANNOTATED_DIODE_COUNT '+str(len(pins))
    if marker not in a.db_log.read_text():raise ValueError('OpenDB audit did not complete')
    lib=a.liberty.read_text();match=re.search(r'cell\s*\(\s*ANTENNA_X1\s*\)\s*\{',lib)
    if not match:raise ValueError('original diode cell absent')
    begin=match.end();depth=1;quoted=False;escaped=False;end=begin
    for end in range(begin,len(lib)):
        c=lib[end]
        if escaped:escaped=False;continue
        if c=='\\' and quoted:escaped=True;continue
        if c=='"':quoted=not quoted
        if not quoted:
            if c=='{':depth+=1
            elif c=='}':depth-=1
        if depth==0:break
    if depth:raise ValueError('unterminated library cell')
    cell=lib[begin:end]
    leakage=re.findall(r'(?:cell_leakage_power|(?<![\w])value)\s*:\s*([\d.eE+-]+)',cell)
    tables=re.findall(r'values\s*\(\s*"([\d.eE+, -]+)"\s*\)',cell)
    if len(leakage)!=3 or len(tables)!=2 or any(float(x)!=0 for x in leakage):
        raise ValueError('diode leakage assumptions differ')
    values=[float(v) for t in tables for v in t.split(',')]
    if len(values)!=14 or any(values):raise ValueError('nonzero/unknown diode internal power')
    capacitance=re.findall(r'(?m)^\s*capacitance\s*:\s*([\d.eE+-]+)',cell)
    if len(capacitance)!=1 or float(capacitance[0])<=0:raise ValueError('diode load missing')
    result={'remaining_pin_count':len(pins),'all_remaining_physical_masters':'ANTENNA_X1',
        'all_remaining_pin_names':'A','library_own_internal_and_leakage_power_zero':True,
        'input_capacitance_in_native_lib_units':float(capacitance[0]),
        'input_load_removed':False,'scope':'only classify unannotated '+a.sample_label+' diode inputs',
        'annotated_pin_count':a.annotated_count,
        'inputs_sha256':{str(x):digest(x) for x in [a.unannotated,a.physical_identities,a.db_log,a.liberty,Path(__file__)]},
        'full_model_energy_qualified':False,
        'limitations':['zero-delay activity lacks delay-induced glitches','only sampled '+a.sample_label+' workloads','other chip and DDR energy still missing']}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'classified_pins':len(pins),'full_model_energy_qualified':False}))

if __name__=='__main__':main()
