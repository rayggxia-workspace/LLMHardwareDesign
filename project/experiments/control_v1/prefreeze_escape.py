"""Bounded M10 escape repair before final RC and every independent final gate."""
import hashlib,json,shutil,sys
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def repair(root,out,results,top,names,run):
    # Both targets have a retained complete-native-DRC failure. This is a
    # pre-freeze wire edit, followed by fresh RC and every original final gate.
    assert top=='control_s_arbiter' and names in (['dout[117]'],['din[633]'])
    sys.path.insert(0,str(root/'project/experiments/block_v1'))
    from native_escape import records,simplify,parse
    from native_escape_audit import readback
    pins={p['pin']:tuple(round(x*2000) for x in p['xy_um']) for p in json.loads((out/'pins.json').read_text())['pins']}
    original=results/'5_route.odb';saved=out/'prefreeze-original.odb'
    shutil.copyfile(original,saved);assert sha(original)==sha(saved)
    def execute(name,body):
        path=out/(name+'.tcl');path.write_text('set_thread_count 16\nread_db {'+str(saved)+'}\n'+body)
        run(['openroad','-no_init','-exit',path],name+'.log')
    execute('prefreeze-before','write_def {'+str(out/'prefreeze-before.def')+'}\nwrite_verilog {'+str(out/'prefreeze-before.v')+'}\n')
    selected={text.lstrip().split()[1]:text for text in records(out/'prefreeze-before.def') if text.lstrip().split()[1] in names}
    assert set(selected)==set(names)
    changed={};plans={}
    for name,text in selected.items():
        candidate,plan=simplify(text,pins[name]);assert plan['changed'],name
        plan['header']=parse(text)[0];plans[name]=plan;changed[name]=candidate
    patch=out/'prefreeze-patch.def'
    patch.write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN '+top+' ;\nUNITS DISTANCE MICRONS 2000 ;\nNETS '+str(len(changed))+' ;\n'+''.join(changed.values())+'END NETS\nEND DESIGN\n')
    execute('prefreeze-edit','read_def -floorplan_initialize {'+str(patch)+'}\nwrite_def {'+str(out/'prefreeze-after.def')+'}\nwrite_verilog {'+str(out/'prefreeze-after.v')+'}\nwrite_db {'+str(out/'prefreeze-edited.odb')+'}\n')
    proof=readback(out/'prefreeze-before.def',out/'prefreeze-after.def',plans)
    assert sha(out/'prefreeze-before.v')==sha(out/'prefreeze-after.v'),'Logical netlist changed'
    shutil.copyfile(out/'prefreeze-edited.odb',original)
    proof.update(plans=plans,source_odb_sha256=sha(saved),edited_odb_sha256=sha(original),helper_sha256=sha(Path(__file__)),
                 logical_netlist_sha256=sha(out/'prefreeze-after.v'),whole_native_drc_qualified=False,
                 scope='Pre-freeze fixed-pin M10 escape simplification only. Other net DEF records, all cells/pins/PG, target lower stack and all vias retained. Fresh final RC and all independent gates still mandatory.')
    path=out/'prefreeze-proof.json';path.write_text(json.dumps(proof,indent=2)+'\n')
    return dict(proof_sha256=sha(path),source_odb_sha256=sha(saved),edited_odb_sha256=sha(original))
