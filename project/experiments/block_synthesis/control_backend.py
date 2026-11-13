"""Lower a declared compact U service subset into real MC/LC images.

This backend consumes the ordinary imported model and an explicit placement
constraint. It is an integration gate, not whole-LLM control-image coverage.
Arithmetic service costs exclude controller fetch; hardware replay measures it.
"""
from copy import deepcopy
import hashlib
import json
import re

from leaf_catalog import duration
from loop_dp import optimize
from verify_loop_dp import verify


def capabilities(source,reference):
    """Bind a deliberately small supported subset to the actual target RTL."""
    index=json.loads((source/'index.json').read_text())
    for path,row in index['files'].items():
        if hashlib.sha256((source/path).read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('control source changed: '+path)
    s=(source/'project/rtl/s_sram/local_s_base.sv').read_text()
    width=int(re.search(r'\[(\d+):0\]\s+req_addr',s).group(1))+1
    adapter=(reference/'design/ucf_native_service.sv').read_text()
    catalog=json.loads((reference/'staged/sources.json').read_text())['rtl_sha256']
    core={}
    for name in ('mc_min_controller.sv','lc_min_controller.sv'):
        path='project/control_rtl_min_v0_1/'+name
        actual=hashlib.sha256((reference/'staged'/path).read_bytes()).hexdigest()
        if actual!=catalog[path]:raise ValueError('accepted control core changed: '+name)
        core[path]=actual
    expected={'COMMAND':0x100,'SEND':0x101,'RECEIVE':0x102,'RESERVE':0x103}
    for name,op in expected.items():
        if not re.search(r'OP_'+name+r"\s*=\s*16'h"+format(op,'x'),adapter):
            raise ValueError('native service opcode changed: '+name)
    if 'native0[3:2]>2' not in adapter or 'native0[31:20]!=0' not in adapter:
        raise ValueError('native operand/address limit changed')
    # controlled.py validates the exact #195 core and adapter hashes before
    # applying the accepted #214 identity/compact-fetch transformations.
    return {'profile':'pr214-u64-native-subset','source':index,
        'adapter_sha256':hashlib.sha256(adapter.encode()).hexdigest(),
        'reference_core_sha256':core,'block_type':0,'instruction_bits':64,'image_version':2,'pm_bus_bits':128,
        'local_words':1<<width,'address_bits':width,'max_native_sources':2,
        'max_execution_descriptors':32,'max_instructions':256,
        'operations':{'Add':{'e_op':0,'shift':0},'Mul':{'e_op':2,'shift':0}},
        'operation_scope':'compiler qualified subset; not the complete target ISA',
        'record':{'bits':16,'exponent':0,'lanes':8},'native_opcodes':expected,
        'lc_instructions':['L_EXEC','L_WAIT','L_END'],
        'mc_instructions':['G_CALL','G_WAIT','G_END'],
        'transport':'one reserved word; source held until destination SRAM commit ACK',
        'system_timing_qualified':False}


def compile_control(model,hardware,cap,profile):
    h=deepcopy(hardware);groups=h['control_groups'];names=list(groups)
    if len(names)!=2 or len({g['block_id'] for g in groups.values()})!=2:
        raise ValueError('this control integration profile needs two distinct local IDs')
    if any(not 0<=g['block_id']<2 for g in groups.values()):
        raise ValueError('two-target MC fixture supports local IDs 0 and 1')
    if not 0<h['topology_id']<2**32:raise ValueError('invalid topology ID')
    if any(h['sites'][g['site']]['words']!=cap['local_words'] for g in groups.values()):
        raise ValueError('capacity differs from selected control RTL')
    if len(model['outputs'])!=1:raise ValueError('one declared output required by current export gate')
    owner={};address={};next_addr={g:40 for g in groups};program={g:[] for g in groups};moves=[];tasks=[]
    produced={v:t['id'] for t in model['tasks'] for v in t['outputs']}
    for name,row in model['values'].items():
        if row.get('shape')!=[8] or row.get('format')!=cap['record'] or row.get('dtype')!='INT16':
            raise ValueError('unregistered control record: '+name)
    def allocate(value,group):
        key=(value,group)
        if key not in address:
            if next_addr[group]>=cap['local_words']:raise ValueError('control S address overflow')
            address[key]=next_addr[group];next_addr[group]+=1
        return address[key]
    initial={}
    for name in model['inputs']:
        group=h['initial_placement'][name]
        if group not in groups:raise ValueError('unknown initial owner')
        owner[name]=group;allocate(name,group);initial[name]={'group':group,'address':address[name,group]}
    def transfer(value,src,dst,reason):
        a,b=allocate(value,src),allocate(value,dst);ops=cap['native_opcodes']
        program[dst].append({'native_op':ops['RESERVE'],'native0':b})
        program[src].append({'native_op':ops['SEND'],'native0':a|(b<<10)})
        program[dst].append({'native_op':ops['RECEIVE']})
        moves.append({'value':value,'src':src,'dst':dst,'source_address':a,'destination_address':b,
                      'reason':reason,'net':src+'->'+dst})
    for node in model['tasks']:
        if (node['op'] not in cap['operations'] or node.get('attributes') or node.get('domain')!='llmhardware.native' or
            len(node['inputs'])!=2 or len(node['outputs'])!=1):
            raise ValueError('operation outside compiler qualified control subset: '+node['op'])
        target=h['placement_constraints'][node['id']]
        if target not in groups:raise ValueError('unknown constrained target')
        for value in node['inputs']:
            if value not in owner:raise ValueError('control graph must be topologically ordered')
            if owner[value]!=target:transfer(value,owner[value],target,'operand')
        output=node['outputs'][0]
        if output in owner:raise ValueError('multiple control producers')
        owner[output]=target;dst=allocate(output,target)
        src=[allocate(v,target) for v in node['inputs']];op=cap['operations'][node['op']]
        program[target].append({'native_op':cap['native_opcodes']['COMMAND'],
            'native0':2<<2|1<<4|dst<<5,'native1':src[0]|src[1]<<10,
            'native2':op['e_op']|(op['shift']<<4)})
        local=groups[target];nets=[target+'.E.read',target+'.E.write']
        nets += [m['net'] for m in moves if m['value'] in node['inputs']]
        ticks=duration(profile,'E',op=op['e_op'],shift=op['shift'])+3*local['s_io_ticks']
        binding={'id':target+'.E','site':local['site'],'ticks':ticks,'nets':sorted(set(nets)),
            'resources':[target+'.E',target+'.LC',target+'.S.IO'],'scratch_words':next_addr[target],
            'external_read_words':0,'external_write_words':0}
        tasks.append({'id':node['id'],'after':sorted({produced[v] for v in node['inputs'] if v in produced}),
                      'bindings':[binding]})
    output=model['outputs'][0];sink=h['output_placement'][output]
    if output not in owner or sink not in groups:raise ValueError('unknown output/placement')
    if owner[output]!=sink:transfer(output,owner[output],sink,'output')
    # Explicit verification export reads the committed sink word through the
    # real SEND path. It is visible in descriptors, traffic and connections.
    if h.get('verification_echo'):
        peer=next(g for g in groups if g!=sink);transfer(output,sink,peer,'verification_export')
    demanded={n for t in tasks for b in t['bindings'] for n in b['nets']}|{m['net'] for m in moves}
    for n in demanded:
        if n not in h['nets']:raise ValueError('unregistered control connection: '+n)
    # The echo/output-only paths are part of the same frozen topology, even
    # though they do not have an arithmetic consumer in the scheduling DAG.
    tasks[-1]['bindings'][0]['nets']=sorted(set(tasks[-1]['bindings'][0]['nets'])|{m['net'] for m in moves})
    plan=optimize(tasks,h,width=8)
    if plan['status']!='planned':raise ValueError('no legal static control topology')
    audit=verify(tasks,h,plan)
    for rows in program.values():
        if len(rows)>cap['max_execution_descriptors'] or 2*len(rows)+1>cap['max_instructions']:
            raise ValueError('control program exceeds selected controller limits')
    connections=[]
    for net in sorted({m['net'] for m in moves}):
        src,dst=net.split('->')
        connections.append({'id':net,'src':src,'dst':dst,'fields':[
            {'name':'data','bits':128,'direction':'forward'},
            {'name':'address','bits':10,'direction':'forward'},
            {'name':'valid','bits':1,'direction':'forward'},
            {'name':'ready','bits':1,'direction':'reverse'},
            {'name':'stored_ack','bits':1,'direction':'reverse'},
            {'name':'ack_ready','bits':1,'direction':'forward'}],
            'physical_status':'simulation connection requirement; no M11/M12 qualification'})
    return {'model':model,'hardware':h,'capabilities':cap,'tasks':tasks,'plan':plan,'audit':audit,
        'program':program,'initial':initial,'addresses':[
            {'value':v,'group':g,'address':a} for (v,g),a in address.items()],
        'moves':moves,'connections':connections,
        'preconnected_demands':sorted(n for n in demanded if h['nets'][n].get('fixed')),
        'control_links':{'distribution':'MC task_valid/ready/target/packet to the two LCs; LC return_valid/ready/packet to MC',
                         'binding':'actual tb_network MC/LC port declarations and target gating in the frozen fixture'},
        'schedule_scope':'dependency/placement/native service cost; LC/PM and transfer timing measured by replay',
        'coverage':'two constrained U groups; real MC/LC binary for selected E/S transport subset'}


def images(compiled,assemble,compact_image):
    """Use the pinned official assembler; no independent guessed ISA encoding."""
    h=compiled['hardware'];cap=compiled['capabilities'];result={}
    mother=[{'op':'G_CALL','a':0,'b':2,'c':0},{'op':'G_CALL','a':1,'b':3,'c':0},
            {'op':'G_WAIT','x':12},{'op':'G_END'}]
    result['mother']=compact_image(assemble('mother',mother,{},19300,0,h['abi_id'],h['topology_id']))
    for group,rows in compiled['program'].items():
        block=h['control_groups'][group]['block_id'];instructions=[];descriptors=[]
        for i,row in enumerate(rows):
            instructions.extend([{'op':'L_EXEC','a':0,'b':0,'c':i},{'op':'L_WAIT','x':1}])
            descriptors.append({**row,'resource':0,'service':0,'native_abi_id':h['abi_id']})
        instructions.append({'op':'L_END'})
        task={'block_type':cap['block_type'],'entry_pc':0,'max_steps':len(instructions),
            'required_resources':1,'program_image_id':19301+block,'topology_id':h['topology_id'],
            'native_abi_id':h['abi_id']}
        result['local'+str(block)]=compact_image(assemble('local',instructions,
            {'task':[task],'execution':descriptors},19301+block,1,h['abi_id'],h['topology_id']))
    if len(result['mother'])>4736 or any(len(v)>8320 for k,v in result.items() if k!='mother'):
        raise ValueError('fixture PM byte capacity exceeded')
    return result
