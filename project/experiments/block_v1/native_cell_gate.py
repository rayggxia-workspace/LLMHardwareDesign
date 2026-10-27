"""Read actual GDS input gate geometry and Liberty before choosing repair cells."""
import json
import math
from pathlib import Path
import re


def group(text,kind,name):
    matches=list(re.finditer(r'\b'+kind+r'\s*\(\s*"?'+re.escape(name)+r'"?\s*\)\s*\{',text))
    assert len(matches)==1,(kind,name,len(matches))
    start=matches[0].end();depth=1;quoted=False;escaped=False;i=start
    while i<len(text):
        c=text[i]
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif text.startswith('/*',i):
            end=text.find('*/',i+2);assert end!=-1;i=end+1
        elif text.startswith('//',i):
            end=text.find('\n',i+2);assert end!=-1;i=end
        elif c=='"':quoted=True
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth==0:return text[start:i]
        i+=1
    raise AssertionError('Unterminated Liberty group')


def attribute(text,name,required=True):
    matches=re.findall(r'(?m)^\s*'+name+r'\s*:\s*("[^"]*"|[^;\n]+)\s*;',text)
    assert len(matches)<=1,(name,matches)
    if not matches:
        assert not required,name
        return None
    return matches[0].strip().strip('"')


def verify(root,out,cpus,run):
    from io_slots import file_sha
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    inputs=[platform/'lef/NangateOpenCellLibrary.tech.lef',platform/'lef/NangateOpenCellLibrary.macro.mod.lef',
            platform/'lib/NangateOpenCellLibrary_typical.lib',platform/'drc/FreePDK45.lydrc']+sorted((platform/'gds').glob('*.gds'))
    assert len(inputs)>4
    hashes={str(path):file_sha(path)for path in inputs}
    run(['openroad','-no_init','-exit',str(root/'project/experiments/block_v1/native_cell_pins.tcl')],'cell-pins.log')
    run(['klayout','-b','-rd','platform='+str(platform),'-rd','pins='+str(out/'cell-pins.tsv'),
         '-rd','report='+str(out/'cell-gate-geometry.json'),'-r',str(root/'project/experiments/block_v1/native_cell_gate.rb')],'cell-gate.log')
    geometry=json.loads((out/'cell-gate-geometry.json').read_text())
    masters={row['master']:row for row in geometry['masters']}
    dimensions={}
    for line in(out/'cell-dimensions.tsv').read_text().splitlines():
        name,w,h=line.split('\t');assert name not in dimensions
        dimensions[name]=dict(width_um=int(w)/2000,height_um=int(h)/2000,area_um2=int(w)*int(h)/2000**2)
    text=(platform/'lib/NangateOpenCellLibrary_typical.lib').read_text()
    assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text,re.I)
    library={}
    for name,physical in masters.items():
        if not re.search(r'\bcell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)',text):
            assert name=='ANTENNA_X1';library[name]=dict(present=False);continue
        body=group(text,'cell',name);area=float(attribute(body,'area'))
        assert math.isfinite(area)and area>=0
        assert abs(area-dimensions[name]['area_um2'])<1e-6
        pins={}
        for pin in physical['terminals']:
            p=group(body,'pin',pin['term']);direction=attribute(p,'direction')
            assert direction.upper()==pin['direction']
            values=dict(direction=direction)
            for field in ['capacitance','rise_capacitance','fall_capacitance','max_capacitance']:
                raw=attribute(p,field,False)
                if raw is not None:
                    value=float(raw);assert math.isfinite(value)and value>=0;values[field+'_ff']=value
            function=attribute(p,'function',False)
            if function is not None:values['function']=function
            pins[pin['term']]=values
        library[name]=dict(present=True,area_um2=area,pins=pins)
    base=out.parents[2]
    failed=base/'block-v1-20261027-094/tasks/native-cap40-receive-transaction6k-c'
    failed_receipt=json.loads((failed/'receipt.json').read_text());assert failed_receipt['passed']is False
    report=failed/'native-drc-summary.json';assert file_sha(report)==failed_receipt['outputs'][report.name]
    summary=json.loads(report.read_text())
    located=base/'block-v1-20261027-103/tasks/native-drc-locate-c'
    receipt=json.loads((located/'receipt.json').read_text());assert receipt['passed']is True
    location=located/'native-drc-location.json';assert file_sha(location)==receipt['outputs'][location.name]
    diagnostic=json.loads(location.read_text());assert summary['report_sha256']==diagnostic['report_sha256']
    expected={}
    for row in diagnostic['markers']:
        if not row['marker']['category'].endswith('_ANTENNA')or len(row['candidate_nets'])!=1:continue
        net=row['candidate_nets'][0];terms=diagnostic['terminals'][net]
        gates=[t for t in terms if t['kind']=='iterm'];ports=[t for t in terms if t['kind']=='port']
        assert len(gates)==len(ports)==1 and gates[0]['direction']==ports[0]['direction']=='INPUT'
        master=gates[0]['master'];pin=gates[0]['term'];assert master in ('CLKBUF_X1','BUF_X1')
        wanted=summary['items'][row['marker']['index']]['float_fields']['agate']
        expected.setdefault((master,pin),set()).add(wanted)
    controls={}
    for (master,pin),areas in expected.items():
        assert len(areas)==1
        actual=next(t for t in masters[master]['terminals']if t['term']==pin)
        controls[master+'/'+pin]=dict(reported_gate_um2=next(iter(areas)),measured_gate_um2=actual['gate_area_um2'],
            actual_gate_matches=abs(actual['gate_area_um2']-next(iter(areas)))<1e-9,
            missing_contact_rejected=actual['gate_area_um2']>0 and actual['missing_contact_gate_area_um2']==0)
    assert set(controls)=={'BUF_X1/A','CLKBUF_X1/A'}
    for name in masters:
        for pin in masters[name]['terminals']:
            if pin['direction']=='INPUT'and name!='ANTENNA_X1':assert pin['gate_area_um2']>0 and pin['seed_covered_um2']>0
    passed=all(all(row[key]for key in ['actual_gate_matches','missing_contact_rejected'])for row in controls.values())
    record=dict(schema='block-v1-native-cell-gate-probe/1',passed=passed,geometry=geometry,library=library,dimensions=dimensions,
        reference_controls=controls,input_sha256=hashes,source_drc_summary_sha256=file_sha(report),source_location_sha256=file_sha(location),
        qualified_repair=False,scope='Actual native master geometry/Liberty inventory with input-gate agreement controls; no block repair, characterized diode model or DRC qualification')
    (out/'native-cell-gate-probe.json').write_text(json.dumps(record,indent=2)+'\n')
    assert {str(path):file_sha(path)for path in inputs}==hashes
    assert passed,'Actual native gate geometry did not match independent report'
