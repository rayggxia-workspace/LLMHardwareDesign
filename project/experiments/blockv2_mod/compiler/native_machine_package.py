"""Compile a selected native call DAG to MC v3 images and descriptor bytes."""
import json,struct
from pathlib import Path
from hashlib import sha256
from native_completion import attach
from native_mother_dag import actions,verify_actions
from native_local_kernel import encode as local_kernel
from native_deployment import recipe as deployment_recipe
from emit_native_mother import repeated_groups,PM_INSTRUCTIONS,MotherProgramCapacityError
import assemble_cases as assembler
from compile_scope_loops import expand

def encode_actions(action_rows,descriptor_base,topology):
    tokens=[('C',a['target']) if a['op']=='CALL' else ('W',a['mask']) for a in action_rows]
    registers=[descriptor_base&0xffffffff,descriptor_base>>32,0x00010080,0x02510001,topology,0x02500002,0]
    program=[('MOVI',i,0,0,v) for i,v in enumerate(registers)]
    steps=len(program)+1
    for pattern,count in repeated_groups(tokens):
        if count>1:program.append(('MOVI',7,0,0,count))
        start=len(program)
        for kind,value in pattern:
            if kind=='C':program.extend([assembler.call(value),('ADDI64',0,0,0,128)])
            else:program.append(assembler.wait(value))
        if count>1:
            program.append(('LOOP',7,0,0,start))
            steps+=1+count*(len(program)-start)
        else:steps+=len(program)-start
        if len(program)>=PM_INSTRUCTIONS:raise MotherProgramCapacityError('selected native DAG exceeds single MC PM')
    program.append(assembler.END)
    expanded,actual_steps=expand(program,steps+1)
    expected=[{'target':a['target'],'token':a['target'],'reference':descriptor_base+128*i}
              for i,a in enumerate(a for a in action_rows if a['op']=='CALL')]
    if expanded!=expected or actual_steps!=steps:raise ValueError('independent MC instruction expansion mismatch')
    data=bytearray(assembler.image(program,max_steps=steps+1))
    struct.pack_into('<I',data,64,topology)
    return bytes(data),program,steps

def package(plan,out,topology,product_wiring=None):
    modern=plan.get('schema')=='macro-native-selected-plan/1'
    calls=[dict(c) for c in plan['calls']]
    if product_wiring is not None:
        from native_product_binding import validate
        if not modern:raise ValueError('product binding requires a macro-native plan')
        validate(product_wiring,plan['plan_sha256'],plan['hardware'])
    if modern:
        from check_pr185_control_admission import validate as admit_controls
        admit_controls(plan['hardware'])
        semantic={k:v for k,v in plan.items() if k!='plan_sha256'}
        actual=sha256(json.dumps(semantic,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if actual!=plan['plan_sha256']:raise ValueError('selected plan content hash mismatch')
        targets={t['id']:t for t in plan['hardware']['native_dispatch_overlay']['targets']}
        for call in calls:
            raw=bytes.fromhex(call['descriptor_hex'])
            schema,size,op,abi,bound_topology=struct.unpack_from('<IHHII',raw)
            if size!=128 or bound_topology!=topology or call['target'] not in targets:
                raise ValueError('selected call/base mismatch')
            if not any((r['schema'],r['abi'],r['opcode'])==(schema,abi,op)
                       for r in targets[call['target']]['routes']):
                raise ValueError('selected call has no declared RTL route')
    else:
        calls=attach({'calls':calls})['calls']
    wait_policy='predicted_first' if plan.get('search_plan',{}).get('stage_resources') else 'all'
    stream,cuts=actions(calls,wait_policy=wait_policy);proof=verify_actions(calls,stream)
    proof['wait_policy']=wait_policy
    descriptor_base=(plan['storage']['end_address']+127)//128*128
    order=[a['call_index'] for a in stream if a['op']=='CALL']
    descriptors=b''.join(bytes.fromhex(calls[i]['descriptor_hex']) for i in order)
    pages=[]
    try:
        data,program,steps=encode_actions(stream,descriptor_base,topology)
        pages=[{'data':data,'program':program,'steps':steps,'first_action':0,'action_count':len(stream),'first_call':0,'call_count':len(order)}]
    except MotherProgramCapacityError:
        # Only split when no LC is live. Never strand a streamed P scope.
        begin=0;first_call=0;cut_index=0
        while begin<len(stream):
            address=descriptor_base+first_call*128
            cache={}
            def probe(index):
                if index in cache:return cache[index]
                end=cuts[index]
                try:
                    data,program,steps=encode_actions(stream[begin:end],address,topology)
                    cache[index]=(end,data,program,steps)
                except MotherProgramCapacityError:cache[index]=None
                return cache[index]
            if probe(cut_index) is None:raise ValueError('one live-scope interval exceeds MC PM')
            best_index=cut_index;stride=1;high=len(cuts)
            while best_index+stride<len(cuts):
                trial=best_index+stride
                if probe(trial) is None:high=trial;break
                best_index=trial;stride*=2
            lo=best_index+1;hi=high-1
            while lo<=hi:
                mid=(lo+hi)//2
                if probe(mid) is not None:best_index=mid;lo=mid+1
                else:hi=mid-1
            end,data,program,steps=probe(best_index)
            count=sum(a['op']=='CALL' for a in stream[begin:end])
            pages.append({'data':data,'program':program,'steps':steps,'first_action':begin,'action_count':end-begin,'first_call':first_call,'call_count':count})
            begin=end;first_call+=count;cut_index=best_index+1
    out.mkdir(parents=True,exist_ok=False)
    payloads={}
    def write(name,data):
        (out/name).write_bytes(data);payloads[name]={'bytes':len(data),'sha256':sha256(data).hexdigest()}
    write('descriptors.bin',descriptors)
    write('local-kernel.bin',local_kernel(topology=topology))
    page_rows=[];deployment_pages=[]
    for i,page in enumerate(pages):
        name=f'mother-{i:04d}.bin'
        data=page.pop('data');write(name,data)
        deployment_pages.append({'file':name,'data':data,**{k:v for k,v in page.items() if k!='program'}})
        program=page.pop('program')
        write(f'mother-{i:04d}.json',(json.dumps(program)+'\n').encode())
        page_rows.append({'file':name,**page,'descriptor_base':descriptor_base+128*page['first_call']})
    call_rows=[{'index':j,'source_call':i,'target':calls[i]['target'],'address':descriptor_base+128*j,
                'sha256':sha256(bytes.fromhex(calls[i]['descriptor_hex'])).hexdigest()} for j,i in enumerate(order)]
    deployment=deployment_recipe(local_kernel(topology=topology),deployment_pages,
                                 sorted({c['target'] for c in calls}),call_rows,topology)
    for name,data in [('deployment.json',deployment),('calls.json',call_rows),('control-actions.json',stream),('candidate-wiring.json',product_wiring if product_wiring is not None else plan['wiring']),
                      ('storage.json',plan['storage']),('hardware.json',plan['hardware'] if modern else plan['search_hardware']),('control-verification.json',proof)]:
        write(name,(json.dumps(data,indent=2)+'\n').encode())
    if product_wiring is not None:
        write('selected-compute-requirements.json',(json.dumps(plan['wiring'],indent=2)+'\n').encode())
    manifest={'schema':'native-whole-graph-machine-package/1','plan_sha256':plan['plan_sha256'],
              'graph_sha256':plan['graph_sha256'],'topology':topology,'descriptor_base':descriptor_base,
              'native_calls':len(calls),'mother_pages':page_rows,'payloads':payloads,
              'local_program_lifetime':'one fixed kernel per target deployment',
              'rtl_wiring_complete':product_wiring is not None,
              'control_verification':proof,'delivery_accepted':False,
              'pending':([] if product_wiring is not None else ['complete selected SRAM/DDR/control wiring'])+['joined execution','runtime asset realization or explicit timing-only inputs','PR260 fast TLM'],
              'mother_page_runtime_requirement':'execute deployment.json ready/valid recipe; RTL replay not yet validated'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {k:v for k,v in manifest.items() if k not in ('payloads','mother_pages')}|{'mother_page_count':len(pages)}
