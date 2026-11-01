"""Physical short-wire/via fixtures -> direct field C -> SPEF -> OpenDB.

Complete capacitance matrices come from independently FV-qualified scenes,
never fitted-model results. The short-wire two-node pi is a unit/view test;
it does not qualify distributed capacitance of full blocks or long routes.
"""
import hashlib
import json
import math
from pathlib import Path
from rc_pipeline import configuration


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root,out,run,index):
    base=out.parents[2]
    reference=base/'block-v1-20261027-034'/('tasks/fv-case-%d'%index)
    prior=json.loads((reference/'receipt.json').read_text());assert prior['passed']is True
    for name in ['fv-case.json','direct-field.jsonl','scene.txt']:
        assert sha(reference/name)==prior['outputs'][name]
    case=json.loads((reference/'fv-case.json').read_text());assert case['passed']is True
    fields=[json.loads(line)for line in(reference/'direct-field.jsonl').read_text().splitlines()]
    assert fields.pop()=={'status':'PASS','mode':'scene3d'}
    rows={r['master']:r for r in fields};names=sorted(rows)
    entries={n:{v['net']:v for v in r['entries']}for n,r in rows.items()}
    assert set(names)=={name for name,box in case['boxes']}
    ground={name:-entries[name]['ground']['cap']for name in names}
    assert all(v>0 for v in ground.values())
    coupling={}
    for i,a in enumerate(names):
        for b in names[i+1:]:
            x,y=entries[a][b],entries[b][a]
            assert abs(x['cap']-y['cap'])<=5*math.hypot(x['sigma'],y['sigma'])+.01*min(entries[a][a]['cap'],entries[b][b]['cap'])
            value=-(x['cap']+y['cap'])/2
            assert value>0,('This fixture requires measured nonzero mutual coupling',a,b,value)
            coupling[a,b]=value
    total_cc={n:sum(v for pair,v in coupling.items()if n in pair)for n in names}
    for n in names:
        diagonal=entries[n][n]
        assert abs(ground[n]+total_cc[n]-diagonal['cap'])<=5*diagonal['sigma']+.005*diagonal['cap']
    config=configuration(root)
    source=base/config['patterns_run']/'tasks/rcx-complete-patterns'
    bound=json.loads((source/'receipt.json').read_text());assert bound['passed']is True
    tech=source/'overlay/research12.tech.lef';assert sha(tech)==bound['outputs']['overlay/research12.tech.lef']
    technology=json.loads((root/'project/experiments/block_v1/technology.json').read_text())
    assert technology['electrical']['sheet_resistance_ohm']==.03
    rvia=technology['electrical']['via_resistance_ohm']
    levels={(10.09,12.09):'metal10',(12.09,12.89):'via10',(12.89,14.89):'metal11',
            (14.89,15.69):'via11',(15.69,17.69):'metal12'}
    grouped={n:[]for n in names};expected_shapes={layer:[]for layer in levels.values()}
    for n,box in case['boxes']:
        x0,y0,z0,x1,y1,z1=box
        layer=levels[round(z0,6),round(z1,6)]
        grouped[n].append((layer,box))
        expected_shapes[layer].append([x0+20,y0+20,x1+20,y1+20])
    def dbu(x):
        value=round(x*2000);assert abs(value-x*2000)<1e-7;return value
    pins=[];nets=[];resistance={}
    for number,n in enumerate(names):
        if index==5:
            dx=4.*number
            start=('metal10',dx,0.);end=('metal12',dx+1.6,1.6)
            paths=[('metal10',[(dx,0.)],'BV1_via10'),
                   ('metal11',[(dx,0.),(dx+1.6,0.)],'BV1_via11'),
                   ('metal12',[(dx+1.6,0.),(dx+1.6,1.6)],None)]
            resistance[n]=.03*(1.6/.8+1.6/.8)+2*rvia
        else:
            assert len(grouped[n])==1
            layer,(x0,y0,z0,x1,y1,z1)=grouped[n][0]
            if x1-x0>y1-y0:
                width=y1-y0;start=(layer,x0+width/2,(y0+y1)/2);end=(layer,x1-width/2,(y0+y1)/2)
            else:
                width=x1-x0;start=(layer,(x0+x1)/2,y0+width/2);end=(layer,(x0+x1)/2,y1-width/2)
            paths=[(layer,[start[1:],end[1:]],None)]
            resistance[n]=.03*(abs(end[1]-start[1])+abs(end[2]-start[2]))/width
        for suffix,p,direction in [('s',start,'INPUT'),('t',end,'OUTPUT')]:
            layer,x,y=p
            pins.append('- %s_%s + NET %s + DIRECTION %s + USE SIGNAL\n + PORT + LAYER %s ( -800 -800 ) ( 800 800 ) + PLACED ( %d %d ) N ;'%
                        (n,suffix,n,direction,layer,dbu(x+20),dbu(y+20)))
        line='- %s ( PIN %s_s ) ( PIN %s_t ) + USE SIGNAL\n'%(n,n,n)
        for i,(layer,points,via)in enumerate(paths):
            line+=(' + ROUTED 'if i==0 else' NEW ')+layer+' '+''.join('( %d %d ) '%(dbu(x+20),dbu(y+20))for x,y in points)
            if via:line+=via
        nets.append(line+' ;')
    (out/'fixture.def').write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN direct_fixture ;\n'
        'UNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( 100000 100000 ) ;\nCOMPONENTS 0 ;\nEND COMPONENTS\n'
        'PINS %d ;\n'%len(pins)+'\n'.join(pins)+'\nEND PINS\nNETS %d ;\n'%len(nets)+'\n'.join(nets)+'\nEND NETS\nEND DESIGN\n')
    (out/'expected-shapes.json').write_text(json.dumps(expected_shapes,indent=2)+'\n')
    atoms=[p for n in names for p in[n,n+'_s',n+'_t']];mapping={v:i+1 for i,v in enumerate(atoms)}
    def node(n,end):return '*%d'%mapping[n+'_'+end]
    for mode in ['actual','wrong-cap-unit','collapsed-coupling']:
        unit='PF'if mode=='wrong-cap-unit'else'FF';collapse=mode=='collapsed-coupling'
        text='*SPEF "IEEE 1481-1998"\n*DESIGN "direct_fixture"\n*DATE "2026-10-27"\n'
        text+='*VENDOR "LLMHardwareDesign"\n*PROGRAM "direct-field-view"\n*VERSION "1"\n*DESIGN_FLOW "SHORT_FIXTURE_PI_ONLY"\n'
        text+='*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 '+unit+'\n*R_UNIT 1 OHM\n*L_UNIT 1 UH\n\n*NAME_MAP\n'
        text+=''.join('*%d %s\n'%(i,v)for v,i in mapping.items())+'\n*PORTS\n'
        text+=''.join(node(n,'s')+' I\n'+node(n,'t')+' O\n'for n in names)
        for i,n in enumerate(names):
            g=ground[n]+(total_cc[n]if collapse else 0)
            text+='\n*D_NET *%d %.17g\n*CONN\n*P %s I\n*P %s O\n*CAP\n'%(mapping[n],ground[n]+total_cc[n],node(n,'s'),node(n,'t'))
            text+='1 %s %.17g\n2 %s %.17g\n'%(node(n,'s'),g/2,node(n,'t'),g/2)
            capid=2
            if not collapse:
                for other in names[i+1:]:
                    for a in ['s','t']:
                        for b in ['s','t']:
                            capid+=1;text+='%d %s %s %.17g\n'%(capid,node(n,a),node(other,b),coupling[n,other]/4)
            text+='*RES\n1 %s %s %.17g\n*END\n'%(node(n,'s'),node(n,'t'),resistance[n])
        (out/(mode+'.spef')).write_text(text)
        script='read_lef {'+str(tech)+'}\nread_def fixture.def\nbench_read_spef '+mode+'.spef\n'
        script+='set output [open '+mode+'.tsv w]\n'
        for n in names:
            script+='set net [[ord::get_db_block] findNet '+n+']\n'
            script+='puts $output "'+n+'\t[$net getTotalResistance]\t[$net getTotalCapacitance]\t[$net getTotalCouplingCap]"\n'
        script+='close $output\nwrite_db '+mode+'.odb\n'
        (out/(mode+'.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',mode+'.tcl'],mode+'.log')
    observed={}
    for mode in ['actual','wrong-cap-unit','collapsed-coupling']:
        values={}
        for line in(out/(mode+'.tsv')).read_text().splitlines():
            n,*fields=line.split('\t');assert n not in values;values[n]=list(map(float,fields))
        assert set(values)==set(names)
        errors={n:[abs(a-b)/max(1,abs(a))for a,b in zip([resistance[n],ground[n],total_cc[n]],values[n])]for n in names}
        accepted=all(math.isfinite(e)and e<2e-5 for row in errors.values()for e in row)
        assert accepted==(mode=='actual'),(mode,errors)
        observed[mode]=dict(accepted=accepted,readback=values,scaled_errors=errors)
    from klayout_overlay import generate
    generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45'),technology,out/'klayout')
    run(['klayout','-b','-r',str(root/'project/experiments/block_v1/primitive_geometry.rb'),
         '-rd','lyt='+str(out/'klayout/research12.lyt'),'-rd','lef='+str(tech),
         '-rd','input='+str(out/'fixture.def'),'-rd','expected='+str(out/'expected-shapes.json'),
         '-rd','output='+str(out/'fixture.gds'),'-rd','report='+str(out/'primitive-geometry.json')],'geometry.log')
    record=dict(schema='block-v1-direct-field-view/1',passed=True,index=index,
        reference=str(reference),reference_sha256=sha(reference/'fv-case.json'),physical_def_sha256=sha(out/'fixture.def'),
        field_matrix_source_sha256=sha(reference/'direct-field.jsonl'),resistance_ohm=resistance,
        ground_ff=ground,coupling_sum_ff=total_cc,readback_and_negatives=observed,
        qualification='FV-qualified short-geometry capacitance, exact mask roundtrip, DC and SPEF units; full-block distributed extraction remains unqualified')
    (out/'direct-field-view.json').write_text(json.dumps(record,indent=2)+'\n')
