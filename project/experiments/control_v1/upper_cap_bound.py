"""Failure-only lower bound under the declared uniform upper RC model."""
import json,math,re,subprocess,sys
from pathlib import Path


def inspect(manifest,graph,terminals,out,inputs,sha):
    root=Path(__file__).resolve().parents[3]
    native=root/'project/experiments/block_v1';sys.path.insert(0,str(native))
    from native_cell_gate import group,attribute
    helper=native/'native_cell_gate.py';inputs[str(helper)]=sha(helper)
    lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    inputs[str(lib)]=sha(lib);text=lib.read_text()
    assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text,re.I)
    spec=native/'technology-2um-v1.json';inputs[str(spec)]=sha(spec);technology=json.loads(spec.read_text())
    geo=technology['geometry_um'];electrical=technology['electrical']
    ff_per_um=.0088541878128*electrical['relative_permittivity']*(geo['width']/geo['dielectric_gap']+2*geo['thickness']/geo['spacing'])
    assert ff_per_um>0 and geo['pitch']==4
    from steiner_wire_bound import grid_tree_bound
    helper=Path(__file__).with_name('steiner_wire_bound.py');inputs[str(helper)]=sha(helper)
    drivers={};limits={}
    for top,row in manifest['leaves'].items():
        odb=row['final_files']['6_final.odb'];assert sha(odb['path'])==odb['sha256'];inputs[odb['path']]=odb['sha256']
        table=out/(top+'-output-drivers.tsv')
        script='set_thread_count 16\nread_db {'+odb['path']+'}\nset f [open {'+str(table)+'} w]\n'
        script+='''foreach port [[ord::get_db_block] getBTerms] {
 if {[$port getIoType] ne "OUTPUT" || [$port getSigType] in {POWER GROUND}} {continue}
 set net [$port getNet];if {$net eq "NULL"} {error "Unconnected native output"}
 set found 0
 foreach term [$net getITerms] {
  set pin [$term getMTerm]
  if {[$pin getIoType] ne "OUTPUT"} {continue}
  incr found;set inst [$term getInst]
  puts $f "[$port getName]\\t[$inst getName]\\t[[$inst getMaster] getName]\\t[$pin getName]\\t[$net getName]"
 }
 if {$found!=1} {error "Native output requires exactly one physical driver"}
}
close $f
'''
        source=out/(top+'-output-drivers.tcl');source.write_text(script)
        with (out/(top+'-output-drivers.log')).open('w')as log:
            subprocess.run(['openroad','-no_init','-exit',source],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert sha(odb['path'])==odb['sha256']
        entries={}
        for line in table.read_text().splitlines():
            port,instance,master,pin,net=line.split('\t');assert port not in entries
            key=(master,pin)
            if key not in limits:
                body=group(group(text,'cell',master),'pin',pin);assert attribute(body,'direction')=='output'
                raw=attribute(body,'max_capacitance',False);limits[key]=float(raw)if raw is not None else None
            limit=limits[key]
            if limit is not None:assert math.isfinite(limit)and limit>0
            entries[port]=dict(instance=instance,master=master,pin=pin,net=net,max_capacitance_ff=limit)
        drivers[top]=entries
    def local_xy(pin):
        if 'xy_um' in pin:return pin['xy_um']
        box=pin['box_dbu'];assert len(box)==4
        return [(box[0]+box[2])/4000,(box[1]+box[3])/4000]
    pins={top:{p['pin']:local_xy(p)for p in json.loads(Path(row['pins']).read_text())['pins']}
          for top,row in manifest['leaves'].items()}
    for row in manifest['leaves'].values():
        assert sha(row['pins'])==row['pins_sha256'];inputs[row['pins']]=row['pins_sha256']
    rows=[];unbounded=[]
    for bit,connection in graph['connections'].items():
        driver=connection['driver'];name='net_'+bit;points=terminals[name]
        if driver['instance']=='TOP':continue
        top=graph['instances'][driver['instance']];physical=drivers[top][driver['pin']]
        limit=physical['max_capacitance_ff']
        if limit is None:unbounded.append(dict(net=name,driver=driver,physical_driver=physical));continue
        # Any connected rectilinear tree spans its full X and Y extents. This
        # wire-only HPWL bound ignores every native capacitance, detour, sink,
        # via and endpoint capacitance, so a violation is sufficient to reject
        # this placement under the uniform research model, never to accept it.
        tree_bound=grid_tree_bound(points)
        length=geo['pitch']*tree_bound['necessary_wire_grid_edges']
        caps={variant:length*ff_per_um*factor for variant,factor in electrical['estimate_variants'].items()}
        x,y=pins[top][driver['pin']];w,h=manifest['leaves'][top]['die_um'];assert 0<=x<=w and 0<=y<=h
        pair_bounds=[];rotation_bounds=[]
        for sink in connection['sinks']:
            if sink['instance'] in ['TOP',driver['instance']]:continue
            peer=graph['instances'][sink['instance']];xx,yy=pins[peer][sink['pin']];ww,hh=manifest['leaves'][peer]['die_um']
            assert 0<=xx<=ww and 0<=yy<=hh
            # Two fixed N-oriented rectangles must be separated in at least
            # one of four directions. Aligning the orthogonal pin coordinates
            # and allowing zero channel gap gives a placement-independent
            # lower bound, even before all other blocks are considered.
            pair_bounds.append(min(w-x+xx,x+ww-xx,h-y+yy,y+hh-yy))
            rotation_bounds.append(min(x,w-x,y,h-y)+min(xx,ww-xx,yy,hh-yy))
        independent=max(pair_bounds,default=0)
        independent_caps={variant:independent*ff_per_um*factor for variant,factor in electrical['estimate_variants'].items()}
        rotated=max(rotation_bounds,default=0)
        rotated_low_cap=rotated*ff_per_um*electrical['estimate_variants']['low']
        rows.append(dict(net=name,driver=driver,physical_driver=physical,sinks=len(connection['sinks']),
                         minimum_wire_um=length,tree_bound=tree_bound,wire_capacitance_lower_bound_ff=caps,
                         any_nonoverlap_placement_minimum_wire_um=independent,
                         any_nonoverlap_placement_wire_capacitance_lower_bound_ff=independent_caps,
                         any_nonoverlap_placement_low_variant_violates=independent_caps['low']>limit+1e-9,
                         any_rotation_any_placement_minimum_wire_um=rotated,
                         any_rotation_any_placement_low_wire_cap_ff=rotated_low_cap,
                         any_rotation_any_placement_low_variant_violates=rotated_low_cap>limit+1e-9,
                         low_variant_violates=caps['low']>limit+1e-9))
    violations=[row for row in rows if row['low_variant_violates']]
    result=dict(executed=True,lower_bound='max(HPWL, ceil(L1 metric MST/2)) of actual grid terminals; necessary only',
        research_model=True,calibrated_process=False,ff_per_um_base=ff_per_um,
        low_variant_wire_only_violations=len(violations),bounded_native_driver_nets=len(rows),
        any_nonoverlap_placement_low_variant_violations=sum(row['any_nonoverlap_placement_low_variant_violates']for row in rows),
        any_rotation_any_placement_low_variant_violations=sum(row['any_rotation_any_placement_low_variant_violates']for row in rows),
        absent_liberty_limits=unbounded,rows=rows,whole_system_qualified=False,
        scope='Failure-only necessary condition for this placement under the existing declared uniform RC model. Native capacitance and route detours omitted conservatively; no route, setup/hold, geometry or manufacturing acceptance.')
    (out/'wire-cap-lower-bound.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
