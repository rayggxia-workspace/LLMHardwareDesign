"""Materialize a complete, conflict-free boundary route in actual DEF/ODB/GDS.

This gate cannot grant full system qualification without PG and combined STA.
"""
import argparse,collections,hashlib,json,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--graph',type=Path,required=True)
    p.add_argument('--route',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pg-audit',type=Path,help='Independently bind whole read-back supply continuity and every qualified native PG view')
    a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,job=os.environ['SLURM_JOB_ID'],inputs={},commands=[],whole_system_qualified=False,system_pg_qualified=False,system_timing_qualified=False)
    def bind(path,digest=None):
        actual=sha(path)
        if digest:assert actual==digest,path
        receipt['inputs'][str(path)]=actual
    def run(command,log):
        with (a.out/log).open('w') as f:q=subprocess.run(list(map(str,command)),stdout=f,stderr=subprocess.STDOUT,cwd=a.out)
        receipt['commands'].append(dict(command=list(map(str,command)),returncode=q.returncode,log=log,sha256=sha(a.out/log)))
        assert q.returncode==0,log
    try:
        if a.pg_audit:
            from system_pg_audit import audit
            bind(Path(__file__).with_name('system_pg_audit.py'))
            result=audit(a.manifest,a.graph,a.route,a.pg_audit,bind)
            (a.out/'system-pg-audit.json').write_text(json.dumps(result,indent=2)+'\n')
            receipt.update(passed=result['passed'],system_pg_qualified=result['passed'],scope=result['scope'])
            return
        m=json.loads(a.manifest.read_text());g=json.loads(a.graph.read_text());r=json.loads((a.route/'receipt.json').read_text())
        assert r['passed'] and r['net_count']==g['connected_nets'] and r['search']['final_conflicts']==0 and r['search']['independent_tree_flood']
        assert not r.get('stage')
        from boundary_links import validate
        bind(Path(__file__).with_name('boundary_links.py'));validate(m,g)
        bind(a.manifest,r['inputs'][str(a.manifest)]);bind(a.graph,r['inputs'][str(a.graph)])
        for name,digest in r['outputs'].items():bind(a.route/name,digest)
        plan=json.loads((a.route/'placement.json').read_text());trees=json.loads((a.route/'trees.json').read_text())
        placement=plan['placements_um'];assert set(placement)==set(g['instances'])
        terminals=plan['terminals'];assert set(trees)==set(terminals)=={'net_'+bit for bit in g['connections']}
        plans={};directions={}
        access=None
        if g.get('pg_access'):
            from pg_interface import verify_source
            bind(Path(__file__).with_name('pg_interface.py'))
            path=Path(g['pg_access']);bind(path,g['pg_access_sha256']);access=json.loads(path.read_text())
            assert access['passed']
            for path,digest in access['inputs'].items():bind(path,digest)
            for top,wrapper in access['wrappers'].items():
                folder=Path(wrapper['folder']);path=folder/'receipt.json';bind(path)
                qualified=json.loads(path.read_text())
                assert qualified['passed'] and qualified['native_drc_zero'] and qualified['full_deck']['total_items']==0
                assert qualified['outputs']['wrapper.odb']==wrapper['odb_sha256']==sha(folder/'wrapper.odb')
                verify_source(m['leaves'][top],folder,qualified,receipt['inputs'])
                wrapper['gds_sha256']=qualified['outputs']['wrapper.gds'];bind(wrapper['gds'],wrapper['gds_sha256'])
        for top,row in m['leaves'].items():
            for entry in row['final_files'].values():bind(entry['path'],entry['sha256'])
            bind(row['pins'],row['pins_sha256']);pins=json.loads(Path(row['pins']).read_text())['pins']
            plans[top]={v['pin']:v for v in pins}
            text=Path(row['final_files']['6_final.v']['path']).read_text()
            ports={match.group(4):match.group(1) for match in re.finditer(r'(?m)^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\S+)\s*;',text)}
            directions[top]={v['pin']:ports[v['pin'].split('[')[0]] for v in pins}
            if access:
                plans[top].update(access['contacts'][top])
                directions[top].update(VDD='input',VSS='input')
        tools=ROOT/'project/experiments/block_v1';sys.path.insert(0,str(tools));from overlay import generate
        spec=tools/'technology-2um-v1.json';bind(spec)
        generate(Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef'),json.loads(spec.read_text()),a.out/'technology')
        def xy(v):return [190+8000*v[0],140+8000*v[1]]
        shapes=[];segments={};vias={};all_edges={}
        terminal_kinds={'net_'+bit:['external' if e['instance']=='TOP' else 'native' for e in [c['driver'],*c['sinks']]] for bit,c in g['connections'].items()}
        def box(layer,first,last,net):
            aa,bb=xy(first),xy(last)
            shapes.append(dict(layer=layer,box_dbu=[min(aa[0],bb[0])-2000,min(aa[1],bb[1])-2000,max(aa[0],bb[0])+2000,max(aa[1],bb[1])+2000],net=net))
        for name,branches in trees.items():
            edges=set();seg=[];cuts=set()
            for path in branches:
                assert path
                for v,w in zip(path,path[1:]):
                    assert sum(abs(x-y) for x,y in zip(v,w))==1
                    edge=tuple(sorted((tuple(v),tuple(w))));edges.add(edge)
            # Merge only collinear consecutive edges, never fill a jog's box.
            lines=collections.defaultdict(set)
            for v,w in edges:
                if v[2]!=w[2]:
                    assert (v[0]+v[1])%2==0;cuts.add((v[0],v[1]));continue
                l=v[2]
                if v[1]==w[1]:lines[(l,'x',v[1])].add(min(v[0],w[0]))
                else:lines[(l,'y',v[0])].add(min(v[1],w[1]))
            for (l,axis,fixed),starts in lines.items():
                ordered=sorted(starts);first=last=ordered[0]
                def emit(lo,hi):
                    aa=(lo,fixed,l) if axis=='x' else (fixed,lo,l)
                    bb=(hi+1,fixed,l) if axis=='x' else (fixed,hi+1,l)
                    seg.append((aa,bb));box('metal'+str(11+l),aa,bb,name)
                for value in ordered[1:]:
                    if value==last+1:last=value
                    else:emit(first,last);first=last=value
                emit(first,last)
            for x,y in cuts:
                for layer in ('via11','metal11','metal12'):box(layer,(x,y,0),(x,y,0),name)
            for (x,y),kind in zip(terminals[name],terminal_kinds[name]):
                if kind=='external':continue
                for layer in ('metal10','via10','metal11'):box(layer,(x,y,0),(x,y,0),name)
            segments[name]=seg;vias[name]=sorted(cuts);all_edges[name]=sorted(edges)
        fixture=dict(schema='complete-qualified-boundary-geometry/1',dbu_per_um=2000,shapes=shapes,branches=trees,
                     terminals={name:[xy((*v,0)) for v in ends] for name,ends in terminals.items()},
                     placements_um=placement,width_um=plan['width_um'],height_um=plan['height_um'],net_count=len(trees),instance_count=len(g['instances']),
                     terminal_kinds=terminal_kinds,whole_system_qualified=False,system_pg_qualified=False)
        fixture['logical_instances']=g['instances']
        fixture['logical_connections']={bit:c for bit,c in g['connections'].items()if not bit.startswith('PG_')}
        (a.out/'routing.json').write_text(json.dumps(fixture)+'\n')
        (a.out/'edges.json').write_text(json.dumps(all_edges)+'\n')
        lef=['VERSION 5.6 ;','UNITS DATABASE MICRONS 2000 ; END UNITS']
        def pin_point(pin):
            if 'xy_um' in pin:return pin['xy_um']
            b=pin['box_dbu'];return [(b[0]+b[2])/4000,(b[1]+b[3])/4000]
        for top,row in m['leaves'].items():
            lef += [f'MACRO SYS_{top}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {row["die_um"][0]} BY {row["die_um"][1]} ;',' SYMMETRY X Y ;']
            for name,pin in plans[top].items():
                x,y=pin_point(pin)
                use='POWER' if name=='VDD' else 'GROUND' if name=='VSS' else 'SIGNAL'
                lef += [f' PIN {name}',f'  DIRECTION {directions[top][name].upper()} ;','  USE '+use+' ;','  PORT','   LAYER metal10 ;',f'   RECT {x-1:.6f} {y-1:.6f} {x+1:.6f} {y+1:.6f} ;','  END',f' END {name}']
            lef += [f'END SYS_{top}']
        lef+=['END LIBRARY'];(a.out/'leaves.lef').write_text('\n'.join(lef)+'\n')
        width,height=int(plan['width_um']*2000),int(plan['height_um']*2000)
        text=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN control_system ;','UNITS DISTANCE MICRONS 2000 ;',f'DIEAREA ( 0 0 ) ( {width} {height} ) ;','COMPONENTS '+str(len(g['instances']))+' ;']
        for name,(x,y) in placement.items():text.append(f'- {name} SYS_{g["instances"][name]} + FIXED ( {int(x*2000)} {int(y*2000)} ) N ;')
        text += ['END COMPONENTS','PINS '+str(len(plan['external_grid_pins']))+' ;']
        top_nets={}
        for bit,c in g['connections'].items():
            for end in [c['driver'],*c['sinks']]:
                if end['instance']=='TOP':top_nets[end['pin']]=('net_'+bit,'INPUT' if end['direction']=='output' else 'OUTPUT')
        assert set(top_nets)==set(plan['external_grid_pins'])
        for pin,point in plan['external_grid_pins'].items():
            net,direction=top_nets[pin];x,y=xy((*point,0))
            use='POWER' if pin=='VDD' else 'GROUND' if pin=='VSS' else 'SIGNAL'
            text.append(f'- {pin} + NET {net} + DIRECTION {direction} + USE {use} + PORT + LAYER metal11 ( -2000 -2000 ) ( 2000 2000 ) + FIXED ( {x} {y} ) N ;')
        text+=['END PINS','NETS '+str(len(trees))+' ;']
        for bit,c in g['connections'].items():
            name='net_'+bit;ends=[c['driver'],*c['sinks']]
            text.append('- '+name+' '+' '.join('( '+('PIN' if e['instance']=='TOP' else e['instance'])+' '+e['pin']+' )' for e in ends))
            if bit.startswith('PG_'):text.append(' + USE '+('POWER' if bit=='PG_VDD' else 'GROUND'))
            route_started=False
            for point,kind in zip(terminals[name],terminal_kinds[name]):
                if kind=='external':continue
                x,y=xy((*point,0));text.append(f' {"NEW" if route_started else "+ ROUTED"} metal10 ( {x} {y} ) BV1_via10');route_started=True
            for point in vias[name]:
                x,y=xy((*point,0));text.append(f' {"NEW" if route_started else "+ ROUTED"} metal11 ( {x} {y} ) BV1_via11');route_started=True
            for first,last in segments[name]:
                x,y=xy(first);xx,yy=xy(last);text.append(f' NEW metal{11+first[2]} ( {x} {y} ) ( {xx} {yy} )')
            text.append(' ;')
        text+=['END NETS','END DESIGN'];(a.out/'6_final.def').write_text('\n'.join(text)+'\n')
        script='set_thread_count 16\nread_lef {'+str(a.out/'technology/research12.tech.lef')+'}\nread_lef {'+str(a.out/'leaves.lef')+'}\nread_def {'+str(a.out/'6_final.def')+'}\n'
        script+='set block [ord::get_db_block]\nif {[llength [$block getInsts]] != '+str(len(g['instances']))+' || [llength [$block getNets]] != '+str(len(trees))+'} {error "Incomplete physical composition"}\n'
        for bit,c in g['connections'].items():
            expected=len(c['sinks'])+1
            script+='set n [$block findNet net_'+bit+']; if {[llength [$n getITerms]]+[llength [$n getBTerms]] != '+str(expected)+'} {error "Boundary endpoint count mismatch"}\n'
        script+='set pg [open {'+str(a.out/'actual-typed-pg.tsv')+'} w]\n'
        for supply,kind in [('VDD','POWER'),('VSS','GROUND')]:
            if 'PG_'+supply not in g['connections']:continue
            script+='set n [$block findNet net_PG_'+supply+']; if {[$n getSigType] ne "'+kind+'"} {error "Wrong actual supply net type"}\n'
            script+='foreach p [$n getITerms] {if {[[$p getMTerm] getSigType] ne "'+kind+'"} {error "Wrong actual macro supply pin type"}}\n'
            script+='foreach p [$n getBTerms] {if {[$p getSigType] ne "'+kind+'"} {error "Wrong actual external supply pin type"}}\n'
            script+='puts $pg "'+supply+'\\t[$n getSigType]\\t[llength [$n getITerms]]\\t[llength [$n getBTerms]]"\n'
        script+='close $pg\n'
        script+='source {'+str(tools/'odb_geometry.tcl')+'}\nbvgeom::export {'+str(a.out/'actual-geometry.tsv')+'}\nwrite_db {'+str(a.out/'6_final.odb')+'}\nwrite_def {'+str(a.out/'roundtrip.def')+'}\n'
        (a.out/'readback.tcl').write_text(script);run(['openroad','-no_init','-exit',a.out/'readback.tcl'],'readback.log')
        from revision300_escape import geometry,compare
        compare(geometry(a.out/'actual-geometry.tsv',set(trees)),shapes)
        request=dict(fixture=str(a.out/'routing.json'),native={name:dict(path=m['leaves'][top]['final_files']['6_final.gds']['path'],sha256=m['leaves'][top]['final_files']['6_final.gds']['sha256']) for name,top in g['instances'].items()},output=str(a.out/'6_final.gds'))
        if access:
            request['native']={name:dict(path=access['wrappers'][top]['gds'],sha256=access['wrappers'][top]['gds_sha256']) for name,top in g['instances'].items()}
        (a.out/'join-input.json').write_text(json.dumps(request,indent=2)+'\n')
        template=Path(__file__).with_name('system_geometry_gds.py');bind(template)
        (a.out/'join.py').write_text(template.read_text().replace('INPUT_MANIFEST_PLACEHOLDER',str(a.out/'join-input.json')))
        run(['klayout','-b','-r',a.out/'join.py'],'gds.log');assert json.loads((a.out/'joined-readback.json').read_text())['passed']
        receipt.update(passed=True,net_count=len(trees),instance_count=len(g['instances']),actual_odb_def_readback=True,actual_joined_gds_readback=True,
                       scope='All declared frozen native instances and every extracted boundary signal/clock/reset net in actual final geometry. PG and full combined STA remain mandatory independent gates.')
    finally:
        receipt['outputs']={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
