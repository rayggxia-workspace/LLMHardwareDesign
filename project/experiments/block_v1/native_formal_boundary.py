"""Diagnose actual unmatched native boundaries without accepting or altering them.

The installed Naja parser reads both immutable full netlists. All top ports,
their actual drivers and readers, and name/bit IDs remain visible. This probe
does not establish equivalence, waive unmatched outputs, or qualify a block.
"""
import ctypes
import json
from pathlib import Path
import sys


def snapshot(top, name_id):
    def bit(term):
        # Installed Naja exposes getBit only for a bus-bit term. Scalars are
        # represented as bit 0 here, without invoking an unavailable method.
        return term.getBit() if hasattr(term,'getBit') else 0

    def endpoint(term):
        return dict(instance=term.getInstance().getName(),
                    master=term.getInstance().getModel().getName(),
                    pin=term.getBitTerm().getName(),
                    bit=bit(term.getBitTerm()),
                    direction=str(term.getBitTerm().getDirection()))

    terms=[]
    for term in top.getBitTerms():
        net=term.getNet()
        terms.append(dict(name=term.getName(),name_id=name_id(term.getName().encode()),
                          bit=bit(term),direction=str(term.getDirection()),
                          term_id=term.getID(),
                          net=None if net is None else dict(name=net.getName(),type=net.getTypeAsString(),
                              constants=dict(zero=net.isConstant0(),one=net.isConstant1(),
                                             x=net.isConstantX(),z=net.isConstantZ()),
                              top_terms=[dict(name=t.getName(),bit=bit(t),direction=str(t.getDirection()))
                                         for t in net.getBitTerms()],
                              instance_terms=[endpoint(t)for t in net.getInstTerms()])))
    return dict(top=top.getName(),terms=terms)


def verify(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus>=4
    source=out.parents[2]/'block-v1-20261027-080/tasks/native-run-shared109-c'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    results=source/'flow/results/nangate45/bv1_shared109_C/base'
    before,after=results/'1_synth_lec.v',results/'6_final.v'
    log=source/'flow/logs/nangate45/bv1_shared109_C/base/6_final_lec_check.log'
    inputs={str(p):file_sha(p)for p in [before,after,log]}
    for p,digest in inputs.items():assert digest==receipt['outputs'][str(Path(p).relative_to(source))]
    from native_formal import inspect
    original=inspect(log.read_text());assert original['counts']['diff1 outputs']==2 and not original['passed']
    prefix=Path('/OpenROAD-flow-scripts/tools/install/kepler-formal')
    library=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
    shim=out/'native-name-ids.so'
    run(['g++','-std=c++17','-shared','-fPIC','-O2','-I'+str(prefix/'include'),
         str(root/'project/experiments/block_v1/native_name_ids.cpp'),'-L'+str(prefix/'lib'),
         '-Wl,-rpath,'+str(prefix/'lib'),'-lnaja_nl','-o',str(shim)],'name-helper-build.log')
    # The shared interner is supplied by the same installed libnaja_nl used by
    # naja.so. No debugger, patched verifier, or modified parser is involved.
    sys.path.insert(0,str(prefix/'lib/python/naja'))
    import naja
    helper=ctypes.CDLL(str(shim))
    name_id=helper.bv1_name_id;name_id.argtypes=[ctypes.c_char_p];name_id.restype=ctypes.c_uint32
    universe=naja.NLUniverse.create()
    views=[]
    for label,path in [('before',before),('after',after)]:
        db=naja.NLDB.create(universe)
        db.loadLibertyPrimitives([str(library)])
        db.loadVerilog([str(path)])
        view=snapshot(db.getTopDesign(),name_id)
        (out/(label+'-boundary.json')).write_text(json.dumps(view,indent=2)+'\n')
        views.append(view)
    keyed=[{(t['name'],t['bit']):t for t in v['terms']}for v in views]
    differences=[dict(port=list(k),before=keyed[0].get(k),after=keyed[1].get(k))
                 for k in sorted(set(keyed[0])|set(keyed[1]))if keyed[0].get(k)!=keyed[1].get(k)]
    record=dict(schema='block-v1-native-boundary-diagnostic/1',passed=True,
        input_sha256=inputs,liberty_sha256=file_sha(library),
        naja_version=naja.getVersion(),naja_git_hash=naja.getGitHash(),
        parser_sha256=file_sha(Path(naja.__file__)),helper_sha256=file_sha(shim),
        original_strict_formal=original,top_port_counts=[len(v['terms'])for v in views],
        top_port_differences=differences,qualified_equivalence=False,
        id_warning='Python loader library names/order may differ from installed Kepler; numeric name IDs are diagnostic, not asserted identical to its log',
        scope='Read-only actual top-port connectivity diagnosis; no waived boundaries or equivalence/physical acceptance')
    assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    (out/'native-boundary-diagnostic.json').write_text(json.dumps(record,indent=2)+'\n')


def physical(root,out,cpus,run):
    from io_slots import file_sha
    source=out.parents[2]/'block-v1-20261027-080/tasks/native-run-shared109-c'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    results=source/'flow/results/nangate45/bv1_shared109_C/base'
    inputs={}
    for label,name in [('before','1_synth.odb'),('after','6_final.odb')]:
        path=results/name;inputs[str(path)]=file_sha(path)
        assert inputs[str(path)]==receipt['outputs'][str(path.relative_to(source))]
        script='set ::env(BV1_BOUNDARY_ODB) {'+str(path)+'}\n'
        script+='source {'+str(root/'project/experiments/block_v1/native_boundary_physical.tcl')+'}\n'
        (out/(label+'.tcl')).write_text(script)
        run(['openroad','-no_init','-exit',str(out/(label+'.tcl'))],label+'.log')
    assert all(file_sha(Path(p))==digest for p,digest in inputs.items())
    record=dict(schema='block-v1-native-boundary-physical-diagnostic/1',passed=True,
                input_sha256=inputs,driver_traces={label:[line for line in(out/(label+'.log')).read_text().splitlines()
                    if line.split('\t')[0]in ('PORT','NET','DRIVER','MASTER')]for label in ['before','after']},
                qualified_equivalence=False,scope='Actual immutable synth/final ODB driver traces only; no waiver, repair, equivalence or physical acceptance')
    (out/'native-boundary-physical.json').write_text(json.dumps(record,indent=2)+'\n')
