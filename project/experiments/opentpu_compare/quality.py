"""Strict extracted-result gates; Slurm completion alone is never acceptance."""
import math
import re

def nonnegative(x):
    return isinstance(x,(int,float)) and math.isfinite(x) and x>=0

def require_toolchain(row):
    """Use sealed, compute-node observations rather than a tool version guess."""
    expected={
        'orfs-current-repacked.sif':'49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a',
        'openroad':'0a4cdf08482bab2d99543e8b32b4b142e013becc7f2c1598afb39ba058193f53',
        'yosys':'c2eb1a5e00957ef65553f1fb4abce0b34bb22173570080c7682c1999f7aafc5b'}
    observed={}
    for key in ['image.sha256','tools.sha256']:
        assert row.get('collected_file_integrity',{}).get(key), 'Unsealed tool identity: '+key
        for line in row.get(key,'').splitlines():
            digest,path=line.split(None,1)
            name=path.rsplit('/',1)[-1]
            assert name not in observed, 'Duplicate tool identity'
            observed[name]=digest
    assert observed==expected, 'Actual compute-node tool/image differs from the fixed experiment'
    return observed

def require_sealed_input(consumer,producer,relative):
    """Bind what a proof/STA actually read to the producer's sealed output."""
    relative=relative.replace('\\','/')
    path=producer['spec']['remote'].rstrip('/')+'/'+relative
    expected=producer.get('sealed_artifact_sha256',{}).get(relative)
    actual=consumer.get('input-sha256.json',{}).get(path)
    assert expected and actual==expected, 'Proof/STA input does not match sealed artifact: '+path

def evaluate(row):
    f=row.get('metrics',{}).get('6_report.json',{})
    d=row.get('metrics',{}).get('5_2_route.json',{})
    report=row.get('final_report','')
    match=re.search(r'finish max_capacitance_check_slack\s*\n-+\s*\n([^\n]+)',report)
    cap=float(match[1]) if match else None
    gates={'pipeline_zero':row.get('exit_code')=='0',
        'drc_zero':d.get('detailedroute__route__drc_errors')==0,
        'antenna_nets_zero':d.get('detailedroute__antenna__violating__nets')==0,
        'antenna_pins_zero':d.get('detailedroute__antenna__violating__pins')==0,
        'worst_cap_margin_nonnegative':nonnegative(cap)}
    for typ in ['setup','hold']:
        gates[typ+'_slack_nonnegative']=nonnegative(f.get('finish__timing__'+typ+'__ws'))
        gates[typ+'_tns_zero']=f.get('finish__timing__'+typ+'__tns')==0
    for typ in ['cap','slew','fanout']:
        gates[typ+'_count_zero']=f.get('finish__timing__drv__max_'+typ)==0
        gates[typ+'_margin_nonnegative']=nonnegative(f.get('finish__timing__drv__max_'+typ+'_limit'))
    return dict(passed=all(gates.values()),gates=gates,worst_cap_margin_fF=cap,
        area_um2=f.get('finish__design__instance__area'),
        die_area_um2=f.get('finish__design__die__area'),
        setup_ns=f.get('finish__timing__setup__ws'),hold_ns=f.get('finish__timing__hold__ws'),
        signal_wire_um=d.get('detailedroute__route__wirelength'),signal_vias=d.get('detailedroute__route__vias'))

if __name__=='__main__':
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parent/'results'
    data=json.loads((root/'latest.json').read_text())
    output={k:evaluate(v) for k,v in data['attempts'].items() if v.get('metrics',{}).get('6_report.json')}
    (root/'quality-latest.json').write_text(json.dumps(output,indent=2)+'\n')
    for k,v in output.items(): print(k,json.dumps(v))
