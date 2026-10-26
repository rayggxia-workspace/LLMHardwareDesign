"""Compare fitted RCX against independent 3D rows on held-out wire geometry.

Lock error gates before seeing results. Includes all native/new layers and
both parallel and perpendicular M10/M11 and M11/M12 coupling experiments.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
from rc_pipeline import configuration


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root,out,cpus,run):
    assert cpus>=8
    base=out.parents[2]
    config=configuration(root)
    fit=base/config['fit_run']/'tasks/reference-fit'
    receipt=json.loads((fit/'receipt.json').read_text());assert receipt['passed']is True
    model=fit/'research12.rules';assert sha(model)==receipt['outputs'][model.name]
    fit_record=json.loads((fit/'reference-fit.json').read_text())
    manifest_path=Path(fit_record['manifest']);assert sha(manifest_path)==fit_record['manifest_sha256']
    layers=json.loads(manifest_path.read_text())['layers']
    tech=Path(json.loads(manifest_path.read_text())['source_folder'])/'overlay/research12.tech.lef'
    prior=json.loads((tech.parent.parent/'receipt.json').read_text())
    assert sha(tech)==prior['outputs']['overlay/research12.tech.lef']
    qualified=base/config['solver_run']/'tasks/fsv-build/fsv-qualified.json'
    tool=json.loads(qualified.read_text());binary=Path(tool['binary']);assert sha(binary)==tool['binary_sha256']
    cases=[];nets=[];masters=[]
    def add_case(name, layer_numbers, orientations):
        case_id=len(cases);ox=(case_id%4)*400+100;oy=(case_id//4)*400+100
        members=[];targets=[]
        for number,orientation in zip(layer_numbers,orientations):
            layer='metal%d'%number;spec=layers[layer];width=spec['width'];gap=1.5*width
            length=150*width
            for i in range(-2,3):
                net=name+'_m%d_%d'%(number,i+3)
                if orientation=='V':x0=x1=ox+i*(width+gap);y0=oy-length/2;y1=oy+length/2
                else:y0=y1=oy+i*(width+gap);x0=ox-length/2;x1=ox+length/2
                # Default DEF extensions are half-width. Endpoint pin squares
                # are contained in this same union, never an extra capacitor.
                box=[x0-width/2,y0-width/2,spec['height'],x1+width/2,y1+width/2,spec['height']+spec['thickness']]
                value=dict(name=net,layer=layer,width=width,points=[x0,y0,x1,y1],box=box,
                           resistance_ohm=spec['rsheet']*length/width)
                members.append(value);nets.append(value)
                if i==0:targets.append(net);masters.append(net)
        path=out/('%06d.txt'%case_id)
        path.write_text('background 3.9\n'+''.join('master '+n+'\n'for n in targets)+''.join(
            'box '+n['name']+' '+' '.join('%.12g'%v for v in n['box'])+'\n'for n in members))
        cases.append(dict(id=case_id,name=name,scene=str(path),scene_sha256=sha(path),nets=members,masters=targets))
    for number in range(1,13):add_case('same%d'%number,[number],['V'if number%2==0 else'H'])
    for lower,upper in [(10,11),(11,12)]:
        add_case('parallel%d_%d'%(lower,upper),[lower,upper],['V','V'])
        add_case('cross%d_%d'%(lower,upper),[lower,upper],['H','V'])
    def dbu(value):
        integer=round(value*2000);assert abs(integer-value*2000)<1e-6;return integer
    pins=[];routes=[]
    for net in nets:
        x0,y0,x1,y1=map(dbu,net['points']);half=dbu(net['width']/2)
        for suffix,x,y,direction in [('a',x0,y0,'INPUT'),('b',x1,y1,'OUTPUT')]:
            pins.append('- {name}_{suffix} + NET {name} + DIRECTION {direction} + USE SIGNAL\n'
                        ' + PORT + LAYER {layer} ( {lo} {lo} ) ( {hi} {hi} ) + PLACED ( {x} {y} ) N ;'.format(
                            **net,suffix=suffix,direction=direction,lo=-half,hi=half,x=x,y=y))
        routes.append('- {name} ( PIN {name}_a ) ( PIN {name}_b ) + USE SIGNAL\n'
                      ' + ROUTED {layer} ( {x0} {y0} ) ( {x1} {y1} ) ;'.format(**net,x0=x0,y0=y0,x1=x1,y1=y1))
    (out/'heldout.def').write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\n'
        'DESIGN heldout ;\nUNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( 3200000 3200000 ) ;\n'
        'COMPONENTS 0 ;\nEND COMPONENTS\nPINS %d ;\n'%len(pins)+'\n'.join(pins)+'\nEND PINS\nNETS %d ;\n'%len(nets)+
        '\n'.join(routes)+'\nEND NETS\nEND DESIGN\n')
    (out/'masters.txt').write_text('\n'.join(masters)+'\n')
    (out/'heldout-inputs.json').write_text(json.dumps(dict(cases=cases,model_sha256=sha(model)),indent=2)+'\n')
    # The low coupling threshold is explicit: retain relevant small couplings
    # instead of folding them to ground to improve agreement artificially.
    script='read_lef {'+str(tech)+'}\nread_def heldout.def\n'
    script+='define_process_corner -ext_model_index 0 research\nextract_parasitics -ext_model_file {'+str(model)+'} -coupling_threshold 0.000001 -context_depth 3\n'
    script+=r'''
set output [open extracted.tsv w]
set ccoutput [open coupling.tsv w]
set input [open masters.txt r]
while {[gets $input name]>=0} {
  set net [[ord::get_db_block] findNet $name]
  puts $output "$name\t[$net getTotalResistance]\t[$net getTotalCapacitance]\t[$net getTotalCouplingCap]"
  foreach node [$net getCapNodes] {
    foreach cc [$node getCCSegs] {
      set source [[$cc getSourceCapNode] getNet]
      set target [[$cc getTargetCapNode] getNet]
      puts $ccoutput "$name\t[$cc getId]\t[$source getName]\t[$target getName]\t[$cc getCapacitance]"
    }
  }
}
close $input
close $output
close $ccoutput
write_spef extracted.spef
write_db extracted.odb
'''
    (out/'extract.tcl').write_text(script)
    workers=min(4,cpus//2);threads=cpus//workers
    def solve(case):
        target=out/('reference-%02d.jsonl'%case['id'])
        with target.open('w')as stream:
            result=subprocess.run([str(binary),'scene3d',str(threads),case['scene']],stdout=stream,stderr=subprocess.STDOUT)
        assert result.returncode==0,target
        rows=[json.loads(line)for line in target.read_text().splitlines()]
        assert rows[-1]=={'status':'PASS','mode':'scene3d'}
        assert {r['master']for r in rows[:-1]}==set(case['masters'])
        return rows[:-1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers)as pool:
        rows=[row for values in pool.map(solve,cases)for row in values]
    # Preserve independent held-out references even if this candidate's
    # extraction reader/solver fails. No dependency on fitted RCX results.
    run(['openroad','-no_init','-exit','extract.tcl'],'extraction.log')
    extracted={}
    for line in(out/'extracted.tsv').read_text().splitlines():
        name,*values=line.split('\t');assert name not in extracted;extracted[name]=list(map(float,values))
    assert set(extracted)==set(masters)
    coupled={};segment_ids=set()
    for line in(out/'coupling.tsv').read_text().splitlines():
        master,identifier,a,b,value=line.split('\t')
        if identifier in segment_ids:continue
        segment_ids.add(identifier);pair=tuple(sorted((a,b)))
        coupled[pair]=coupled.get(pair,0)+float(value)
    results=[];passed=True
    lookup={n['name']:n for n in nets}
    for row in rows:
        name=row['master'];entries={e['net']:e for e in row['entries']};total=entries[name]['cap']
        actual_r,actual_g,actual_c=extracted[name]
        ref_g=-entries['ground']['cap'];ref_c=total-ref_g
        r_error=abs(actual_r-lookup[name]['resistance_ohm'])/lookup[name]['resistance_ohm']
        t_error=abs(actual_g+actual_c-total)/total
        g_error=abs(actual_g-ref_g)/total;c_error=abs(actual_c-ref_c)/total
        uncertainty=5*entries[name]['sigma']/total
        checks=dict(resistance=r_error<=.02,total=t_error<=.10+uncertainty,
                    ground=g_error<=.10+uncertainty,coupling_sum=c_error<=.10+uncertainty)
        pairs=[]
        cross_layer_coverage=True
        for other,entry in entries.items():
            if other in (name,'ground'):continue
            actual=coupled.get(tuple(sorted((name,other))),0)
            if lookup[other]['layer']!=lookup[name]['layer']and -entry['cap']>=.0001*total:
                cross_layer_coverage &= actual>0
            if -entry['cap']<.05*total:continue
            error=abs(actual+entry['cap']);ok=error<=.20*(-entry['cap'])+5*entry['sigma']
            pairs.append(dict(net=other,reference_ff=-entry['cap'],extracted_ff=actual,passed=ok))
        checks['significant_coupling_pairs']=all(pair['passed']for pair in pairs)
        checks['cross_layer_coupling_present']=cross_layer_coverage
        passed &= all(checks.values())
        results.append(dict(master=name,reference_total_ff=total,reference_ground_ff=ref_g,
                            extracted_total_ff=actual_g+actual_c,extracted_ground_ff=actual_g,
                            extracted_coupling_ff=actual_c,resistance_relative_error=r_error,
                            total_relative_error=t_error,ground_error_over_total=g_error,
                            coupling_error_over_total=c_error,coupling_pairs=pairs,checks=checks))
    record=dict(schema='block-v1-heldout-rc/1',passed=passed,cases=cases,model_sha256=sha(model),binary_sha256=sha(binary),
                declared_gates=dict(resistance_relative=.02,total_relative=.10,ground_error_over_total=.10,
                                    coupling_sum_error_over_total=.10,additional_total_sigma=5,
                                    significant_pair_min_fraction=.05,significant_pair_relative=.20,
                                    cross_layer_nonzero_min_fraction=.0001),results=results,
                scope='Held-out primitive wires; access-via R/C and full hierarchy boundary validation remain separate')
    (out/'heldout-rc.json').write_text(json.dumps(record,indent=2)+'\n')
    assert passed,'Held-out extraction/reference disagreement; inspect heldout-rc.json'
