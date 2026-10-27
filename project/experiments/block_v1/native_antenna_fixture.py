"""Actual diode/GDS controls before any full-block prefabrication repair."""
import json
from pathlib import Path


def verify(root,out,cpus,run):
    from io_slots import file_sha
    from native_drc import summarize
    from native_formal import inspect
    assert cpus>=4
    platform=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45')
    prior=out.parents[2]/'block-v1-20261027-108/tasks/native-cell-gate-probe'
    receipt=json.loads((prior/'receipt.json').read_text());assert receipt['passed']is True
    path=prior/'native-cell-gate-probe.json';assert file_sha(path)==receipt['outputs'][path.name]
    geometry=json.loads(path.read_text());assert geometry['passed']is True
    actual=next(m for m in geometry['geometry']['masters']if m['master']=='ANTENNA_X1')
    assert actual['terminals'][0]['diode_area_um2']>0 and geometry['library']['ANTENNA_X1']['present']
    gds=Path(actual['gds_file']);deck=platform/'drc/FreePDK45.lydrc'
    inputs={str(p):file_sha(p)for p in [gds,deck,platform/'lib/NangateOpenCellLibrary_typical.lib']}
    for p,digest in inputs.items():assert digest==geometry['input_sha256'][p]
    pins=prior/'cell-pins.tsv';assert file_sha(pins)==receipt['outputs'][pins.name]
    fixtures=out/'fixtures';fixtures.mkdir()
    run(['klayout','-b','-r',str(root/'project/experiments/block_v1/native_antenna_fixture.rb'),
         '-rd','pins='+str(pins),'-rd','gds='+str(gds),'-rd','out='+str(fixtures)],'fixture-build.log')
    cases={}
    for name in ['unprotected','connected','disconnected','missing_contact']:
        report=fixtures/(name+'.lyrdb')
        run(['klayout','-b','-r',str(deck),'-rd','in_gds='+str(fixtures/(name+'.gds')),
             '-rd','report_file='+str(report)],'fixture-'+name+'.log')
        result=summarize(report)
        (fixtures/(name+'-summary.json')).write_text(json.dumps(result,indent=2)+'\n')
        cases[name]=dict(report_sha256=file_sha(report),gds_sha256=file_sha(fixtures/(name+'.gds')),
            antenna_count=sum(v for k,v in result['categories'].items()if k.endswith('_ANTENNA')),
            categories=result['categories'],items=result['items'])
    assert cases['unprotected']['antenna_count']>0
    assert cases['connected']['antenna_count']==0
    assert cases['disconnected']['antenna_count']>0
    assert cases['missing_contact']['antenna_count']>0
    # Outputless protection cells must preserve the actual logic/state boundary.
    before='module diode_probe(input a,output z); BUF_X1 b(.A(a),.Z(z)); endmodule\n'
    after='module diode_probe(input a,output z); BUF_X1 b(.A(a),.Z(z)); ANTENNA_X1 d(.A(a)); endmodule\n'
    (out/'before.v').write_text(before);(out/'after.v').write_text(after)
    lib=platform/'lib/NangateOpenCellLibrary_typical.lib'
    config='format: verilog\ninput_paths:\n  - '+str(out/'before.v')+'\n  - '+str(out/'after.v')+'\n'
    config+='liberty_files:\n - '+str(lib)+'\nlog_file: '+str(out/'diode-kepler.log')+'\n'
    (out/'diode-kepler.yml').write_text(config)
    run(['/OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal','--config',str(out/'diode-kepler.yml')],'diode-formal-command.log')
    formal=inspect((out/'diode-kepler.log').read_text());assert formal['passed'],formal
    assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    record=dict(schema='block-v1-native-antenna-fixture/1',passed=True,cases=cases,formal=formal,
        source_probe_sha256=file_sha(path),input_sha256=inputs,qualified_block_repair=False,
        scope='Actual BUF_X1 and ANTENNA_X1 GDS on a deliberately long M1 fixture; unchanged full native deck and actual Liberty LEC. Antenna connectivity controls only, not full fixture DRC, legalization, PG, timing or block qualification')
    (out/'native-antenna-fixture.json').write_text(json.dumps(record,indent=2)+'\n')
