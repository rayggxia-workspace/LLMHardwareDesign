"""Complete ownership and exact module-local bit-to-bit frontier inventory.

Reuses frozen structural partition certificates. Does not invent peer layers or SRAMs.
"""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,csv,gzip,json,re

def load(p):
    p=Path(p);raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes();return json.loads(raw)
def save(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_csv(p,rows,fields=None):
    rows=list(rows);fields=fields or list(rows[0]);
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def owner(name,case):
    if name=='hpy_auxiliary':return case+'_aux'
    for part in ['act','mxu','gemm','vec']:
        if name.endswith('u_'+part):return 'vector' if part=='vec' else part
    raise ValueError((case,'unassigned parent cell',name))
def pin_names(name,port):
    n=len(port['bits']);offset=port.get('offset',0)
    return [name if n==1 else f'{name}[{offset+k}]' for k in range(n)]

FUNCTIONS={
'opentpu':[
 ('u_slice.u_act','act','Activation/scale SRAM and ACT addressing'),
 ('u_slice.u_mxu','mxu','Matrix execution, local FIFOs, FP postprocessing, load control'),
 ('u_slice.u_vpu','opentpu_aux','Vector arithmetic, reduction, function pipeline and local state'),
 ('u_slice.u_tmem','opentpu_aux','Shared tensor SRAM, banking and access state'),
 ('u_slice.u_seq','opentpu_aux','Instruction memory, sequencer and task scheduling'),
 ('u_slice.u_quant','opentpu_aux','Quantization, row buffers and ACT write preparation'),
 ('u_slice.u_dma','opentpu_aux','DRAM/TMEM transfer, local buffers and request state'),
 ('g_coll.u_coll','opentpu_aux','Collective gather/communication control'),
 ('TOP_REMAINDER','opentpu_aux','ASIC/slice arbitration, port mux, status and remaining glue')],
'llaccel':[
 ('u_gemm','gemm','Matrix, accumulation, epilogue, output FIFO and request state'),
 ('u_vec','vector','Vector arithmetic, walkers, splitters, reduction/division and queues'),
 ('u_attn','llaccel_aux','Attention, Q/S buffers, normalization and KV write/output queues'),
 ('u_cp','llaccel_aux','Instruction fetch, command queues, scheduling and synchronization'),
 ('u_dma','llaccel_aux','SRAM/DRAM transfer and outstanding request/response FIFOs'),
 ('u_xbar','llaccel_aux','Atomic bank mask grant, write selection and read gather'),
 ('u_arb','llaccel_aux','DRAM request arbitration and response-tag FIFO'),
 ('u_perf','llaccel_aux','Performance accounting and public status'),
 ('TOP_REMAINDER','llaccel_aux','Top connections, status/queue aggregation and remaining glue')]}

def main(root):
    root=Path(root).resolve();src=root/'partition-r02';out=root/'inventory';out.mkdir(exist_ok=True)
    interfaces=[];connections=[];functional=[];summaries={};pin_maps={};matrices=Counter()
    for case in ['opentpu','llaccel']:
        graph=load(src/f'{case}_partition_graph.json.gz');top=graph['top_module'];bits=defaultdict(list)
        hierarchy=[]
        with gzip.open(src/f'{case}_hierarchy_instances.jsonl.gz','rt',encoding='utf-8') as f:
            for line in f:hierarchy.append(json.loads(line))
        allpaths={'.'.join(r['instance_path']) for r in hierarchy}
        inv=load(src/f'{case}_partition_inventory.json')
        assert set(inv['leaf_owner_counts'])==set(['act','mxu','opentpu_aux'] if case=='opentpu' else ['gemm','vector','llaccel_aux'])
        for path,block,purpose in FUNCTIONS[case]:
            assert path=='TOP_REMAINDER' or path in allpaths,(case,path)
            functional.append({'design':case,'instance_path':path,'physical_owner':block,'purpose':purpose,
                               'separate_hard_macro':False if path=='TOP_REMAINDER' or block.endswith('_aux') else True,
                               'source_partition_sha256':graph['source_partition_sha256']})
        for name,p in top['ports'].items():
            for k,(pn,b) in enumerate(zip(pin_names(name,p),p['bits'])):
                role='driver' if p['direction']=='input' else 'sink' if p['direction']=='output' else 'inout'
                bits[b].append({'block':'TOP_IO','pin':pn,'bus':name,'bit_index':k,'direction':p['direction'],'role':role})
        cell_owners={};casepin={}
        for cell_name,cell in top['cells'].items():
            block=owner(cell_name,case);cell_owners[cell_name]=block
            module=graph['frontier'][cell['type']]
            assert set(module['ports'])==set(cell['connections'])
            rows=[]
            for name,p in module['ports'].items():
                con=cell['connections'][name];assert len(con)==len(p['bits'])
                interfaces.append({'design':case,'block':block,'instance':cell_name,'module':cell['type'],'port':name,
                                   'width':len(con),'direction':p['direction'],'offset':p.get('offset',0),'upto':p.get('upto',0),
                                   'source_partition_sha256':graph['source_partition_sha256']})
                for k,(pn,b) in enumerate(zip(pin_names(name,p),con)):
                    row={'block':block,'pin':pn,'bus':name,'bit_index':k,'direction':p['direction'],
                         'role':'sink' if p['direction']=='input' else 'driver' if p['direction']=='output' else 'inout'}
                    bits[b].append(row);rows.append((pn,b))
            assert len({pn for pn,b in rows})==len(rows)
            casepin[block]=dict(rows)
        for b,terms in bits.items():
            drivers=[t for t in terms if t['role']=='driver'];sinks=[t for t in terms if t['role']=='sink']
            if isinstance(b,str):
                assert b in ['0','1','x','z'];drivers=[{'block':'CONSTANT','pin':b,'bus':b,'bit_index':0}]
            for source in drivers:
                for dest in sinks:
                    if source['block']==dest['block']:continue
                    row={'design':case,'parent_module_bit':str(b),'source_block':source['block'],'source_pin':source['pin'],
                         'source_bus':source['bus'],'sink_block':dest['block'],'sink_pin':dest['pin'],'sink_bus':dest['bus'],
                         'source_pin_layer':'UNBOUND','sink_pin_layer':'UNBOUND','parent_route_handoff_layer':'UNKNOWN',
                         'layer_status':'peer pin layers bind only after exact physical port-set match; original parent route not inferred'}
                    connections.append(row);matrices[case,source['block'],dest['block']]+=1
        # Every pin gets a complete list of logical peers plus a canonical real bus alias.
        aliases=defaultdict(list)
        for name,p in top.get('netnames',{}).items():
            for k,b in enumerate(p.get('bits',[])):
                aliases[b].append({'bus':name,'bit_index':k,'width':len(p['bits'])})
        for block,mp in casepin.items():
            pin_maps[block]={}
            for pn,b in mp.items():
                own=[q for q in bits[b] if q['block']==block and q['pin']==pn];assert len(own)==1
                peers=[q for q in bits[b] if not(q['block']==block and q['pin']==pn)]
                if block.endswith('_aux'):
                    candidates=[q for q in peers if q['block']=='TOP_IO']+[q for q in peers if q['block']!='TOP_IO']
                    if candidates:best=sorted(candidates,key=lambda q:(q['block']!='TOP_IO',q['bus'],q['bit_index']))[0];semantic={k:best[k] for k in ['bus','bit_index']}
                    elif aliases[b]:semantic=sorted(aliases[b],key=lambda q:(-q['width'],len(q['bus']),q['bus']))[0]
                    else:semantic={'bus':'UNALIASED_'+pn,'bit_index':0}
                else:semantic={'bus':own[0]['bus'],'bit_index':own[0]['bit_index']}
                pin_maps[block][pn]={'parent_bit':b,'original_direction':own[0]['direction'],'logical_peers':peers,
                                    'semantic_bus':semantic['bus'],'semantic_bit':semantic['bit_index'],
                                    'bus_evidence':'actual parent port/connection alias; not an inferred bank or lane',
                                    'parent_route_handoff_layer':'UNKNOWN'}
        summaries[case]={'top':graph['top'],'physical_cells':cell_owners,'source_partition_sha256':graph['source_partition_sha256'],
                         'raw_leaf_counts':inv['leaf_owner_counts'],'state_memory_counts':inv['state_or_memory_owner_counts'],
                         'storage_macro_counts':inv['original_storage_blackbox_counts'],'unassigned_leaves':0,
                         'parameters':load(src/f'{case}_input_manifest.json')['parameters'],
                         'parameter_evidence_note':'Original JSON metadata not exported for some child parameters; source/-G/default evidence retained from Issue55, not fabricated.',
                         'top_infrastructure':'No functional logic silently left in a free top block: TOP_IO is external ports/clock source, all actual glue belongs to SYSTEM.',
                         'external_scope':'DRAM device, package and host are external. llaccel_core exposes SRAM bank ports; llaccel_top behavioral SRAM banks are outside this frozen top.'}
    write_csv(out/'functional_ownership.csv',functional);write_csv(out/'interfaces.csv',interfaces)
    write_csv(out/'connections.csv',connections)
    write_csv(out/'connection_matrix.csv',[{'design':c,'source':s,'sink':d,'bit_connections':n} for (c,s,d),n in sorted(matrices.items())])
    save(out/'partition_summary.json',summaries);save(out/'pin_logical_mapping.json',pin_maps)
    print('COMPLETE_OWNERSHIP_INVENTORY',len(summaries),'designs',len(pin_maps),'physical blocks',len(functional),'functional ownership entries',len(connections),'logical bit connections')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();main(a.root)
