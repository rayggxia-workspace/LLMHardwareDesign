"""Real-route measured node C -> SPEF -> independent native node/edge readback.

Totals alone cannot detect reassigned node charge or resistor values. Preserve
those totals in actual import controls and require rejection by node identity.
OpenDB API reference: https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbCapNode.html
and classodb_1_1dbRSeg.html; installed-tool execution is required separately.
"""
import json
import math
from pathlib import Path


def receive(folder,expected_caps,expected_edges):
    caps={};edges={}
    for line in(folder/'nodes.tsv').read_text().splitlines():
        key,value=line.split('\t');assert key not in caps
        caps[key]=float(value)
    for line in(folder/'edges.tsv').read_text().splitlines():
        a,b,value=line.split('\t');key=tuple(sorted((a,b)))
        assert a!=b and key not in edges
        edges[key]=float(value)
    values=list(map(float,(folder/'totals.tsv').read_text().split()))
    assert len(values)==3
    def equal(a,b):return math.isfinite(b)and abs(a-b)<=2e-5*max(1,abs(a))
    checks=dict(exact_nodes=set(caps)==set(expected_caps),exact_edges=set(edges)==set(expected_edges),
        every_node_charge=all(k in caps and equal(v,caps[k])for k,v in expected_caps.items()),
        every_edge_resistance=all(k in edges and equal(v,edges[k])for k,v in expected_edges.items()),
        resistance_total=equal(sum(expected_edges.values()),values[0]),
        capacitance_total=equal(sum(expected_caps.values()),values[1]),zero_coupling=equal(0,values[2]))
    return dict(passed=all(checks.values()),checks=checks,nodes=caps,
        edges=[dict(a=k[0],b=k[1],ohm=v)for k,v in edges.items()],totals=values)


READBACK=r'''
proc node_key {node} {
  if {$node eq "NULL" || $node eq ""} {error "Unresolved resistor node"}
  if {[$node isITerm]} {
    set term [$node getITerm]
    return "I:[[$term getInst] getName]/[[$term getMTerm] getName]"
  }
  if {[$node isBTerm]} {return "P:[[$node getBTerm] getName]"}
  return "N:[$node getNode]"
}
set net [[ord::get_db_block] findNet link]
set stream [open nodes.tsv w]
foreach node [$net getCapNodes] {
  # Installed Tcl SWIG rejects uint32_t's explicit integer overload. The
  # documented no-argument overload selects the same default corner zero.
  puts $stream "[node_key $node]\t[$node getCapacitance]"
}
close $stream
set stream [open edges.tsv w]
foreach edge [$net getRSegs] {
  puts $stream "[node_key [$edge getSourceCapNode]]\t[node_key [$edge getTargetCapNode]]\t[$edge getResistance]"
}
close $stream
set stream [open totals.tsv w]
puts $stream "[$net getTotalResistance]\t[$net getTotalCapacitance]\t[$net getTotalCouplingCap]"
close $stream
'''


def verify(root,out,cpus,run):
    from io_slots import file_sha
    import sys
    base=out.parents[2]
    source=base/'block-v1-20261027-096/tasks/routed-graph-field'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']is True
    path=source/'routed-graph-field.json';assert file_sha(path)==receipt['outputs'][path.name]
    result=json.loads(path.read_text());assert result['passed']is True
    original=base/'block-v1-20261027-009/tasks/route-probe'
    bound=json.loads((original/'receipt.json').read_text());assert bound['passed']is True
    odb=original/'probe/routed.odb';assert file_sha(odb)==bound['outputs']['probe/routed.odb']
    nodes=result['nodes'];physical=[tuple(n['physical'])for n in nodes]
    assert len(nodes)==8 and len(set(physical))==8
    # bench_read_spef calls collapseInternalCapNum: its counter starts at
    # one, advances for every cap node (including terminals), then assigns
    # that number to internal nodes. Emit canonical labels in that same
    # CAP creation order, rather than assuming original labels survive.
    # Source: OpenROAD 6ea4ca2 src/odb/src/db/dbNet.cpp:687-698.
    assert physical[:2]==[('metal10',68800,68800),('metal10',273600,273600)]
    ids={p:'*1:%d'%(i+2)for i,p in enumerate(physical)}
    keys={p:'N:%d'%(i+2)for i,p in enumerate(physical)}
    for p,index in [(('metal10',68800,68800),2),(('metal10',273600,273600),3)]:
        ids[p]='*%d:p'%index;keys[p]='I:U%d/p'%(index-2)
    charges=result['local_ground_ff'];assert len(charges)==8 and all(math.isfinite(v)and v>0 for v in charges)
    expected_caps={keys[p]:v for p,v in zip(physical,charges)}
    edges=result['edges'];resistance=[e['resistance_ohm']for e in edges]
    expected_edges={tuple(sorted((keys[tuple(e['a'])],keys[tuple(e['b'])]))):r for e,r in zip(edges,resistance)}
    assert len(expected_edges)==7
    variants={};observed={}
    child='import os,sys;os.chdir(sys.argv[1]);os.execvp("openroad",["openroad","-no_init","-exit","receive.tcl"])'
    for mode in ['actual','wrong-cap-unit','permuted-node-charge','permuted-edge-resistance']:
        caps=charges[:];res=resistance[:]
        if mode=='permuted-node-charge':
            i,j=min(range(8),key=caps.__getitem__),max(range(8),key=caps.__getitem__)
            assert caps[j]-caps[i]>1e-4;caps[i],caps[j]=caps[j],caps[i]
        if mode=='permuted-edge-resistance':
            i,j=min(range(7),key=res.__getitem__),max(range(7),key=res.__getitem__)
            assert res[j]-res[i]>1e-4;res[i],res[j]=res[j],res[i]
        assert math.isclose(sum(caps),sum(charges),rel_tol=1e-12)
        assert math.isclose(sum(res),sum(resistance),rel_tol=1e-12)
        folder=out/mode;folder.mkdir()
        unit='PF'if mode=='wrong-cap-unit'else'FF'
        text='*SPEF "IEEE 1481-1998"\n*DESIGN "landing_probe"\n*DATE "2026-10-27"\n*VENDOR "LLMHardwareDesign"\n*PROGRAM "routed-graph-node-view"\n*VERSION "1"\n'
        text+='*DESIGN_FLOW "MEASURED_ORIGIN_NODE_C_SINGLE_NET_CANDIDATE"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 '+unit+'\n*R_UNIT 1 OHM\n*L_UNIT 1 UH\n'
        text+='*NAME_MAP\n*1 link\n*2 U0\n*3 U1\n\n*D_NET *1 %.17g\n*CONN\n*I *2:p O\n*I *3:p I\n*CAP\n'%sum(caps)
        text+=''.join('%d %s %.17g\n'%(i+1,ids[p],v)for i,(p,v)in enumerate(zip(physical,caps)))
        text+='*RES\n'+''.join('%d %s %s %.17g\n'%(i+1,ids[tuple(e['a'])],ids[tuple(e['b'])],v)for i,(e,v)in enumerate(zip(edges,res)))+'*END\n'
        (folder/'candidate.spef').write_text(text)
        script='set_thread_count %d\nread_db {%s}\nbench_read_spef candidate.spef\n'%(cpus,odb)+READBACK
        (folder/'receive.tcl').write_text(script)
        run([sys.executable,'-c',child,str(folder)],mode+'.log')
        observed[mode]=receive(folder,expected_caps,expected_edges)
        assert observed[mode]['passed']==(mode=='actual'),(mode,observed[mode])
        if mode.startswith('permuted'):
            assert observed[mode]['checks']['resistance_total']and observed[mode]['checks']['capacitance_total']
        variants[mode]=dict(spef_sha256=file_sha(folder/'candidate.spef'),script_sha256=file_sha(folder/'receive.tcl'))
    assert file_sha(odb)==bound['outputs']['probe/routed.odb']
    record=dict(schema='block-v1-routed-graph-view/1',passed=True,
        node_identity=[dict(physical=list(p),spef_label=ids[p],native_key=keys[p])for p in physical],
        native_internal_numbering='collapseInternalCapNum: CAP creation rank plus one; terminals retain real instance/pin identity',
        measured_source_sha256=file_sha(path),source_receipt_sha256=file_sha(source/'receipt.json'),
        source_odb_sha256=file_sha(odb),variants=variants,readback_and_negatives=observed,
        independent_local_fv_on_this_route=False,qualified_node_pair_coupling=False,qualified_full_block=False,
        scope='Single real-route measured node-C and DC-edge SPEF identity/units readback only; local accuracy, multi-net coupling and full distributed extraction remain separate')
    (out/'routed-graph-view.json').write_text(json.dumps(record,indent=2)+'\n')
