"""Server-only software candidate-profile campaign, not RTL/numerical proof."""
import argparse,copy,json,pathlib,sys
import images,model,check,cohort


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True,type=pathlib.Path); a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    params=[5,9,7,3,101,2,1,2]; cases=[]
    for kind in ['P','U','F','J']:
        for iterations,optional,outer,stall in [(1,1,1,False),(3,1,2,True),(2,0,1,True)]:
            ps=list(params); ps[5:8]=[iterations,optional,outer]
            cases.append(dict(name=kind+'_k'+str(iterations)+'_path'+str(optional),kind=kind,parameters=ps,env=dict(stall=stall,hold_result=stall),
                expected=dict(services=iterations*(1+optional)*outer)))
    ps=list(params); ps[5:8]=[1,1,1]
    for name,env,expected in [
        ('state_commit',dict(stall=True,hold_result=True),dict(services=8,published=True,root=9,generation=8)),
        ('update_error',dict(error_service=0),dict(status=9,services=1)),
        ('update_error_after_write',dict(error_service=0,error_after_effect=True),dict(status=9,services=1)),
        ('consumer_error',dict(error_service=3,stall=True),dict(status=9)),
        ('publish_error',dict(error_service=7),dict(status=9,services=8)),
        ('publish_error_after_commit',dict(error_service=7,error_after_effect=True),dict(status=9,services=8,published=True,root=9,generation=8)),
        ('lost_publish_ACK',dict(lost_publish_ACK=True),dict(poison=True,services=8,published=True,root=9,generation=8)),
        ('missing_update',dict(missing_service=0),dict(poison=True,services=1)),
        ('cancel_after_next',dict(cancel_when='next_write',stall=True),dict(status=11,services=1)),
        ('cancel_two_consumers',dict(cancel_when='two_consumers',stall=True),dict(status=11)),
        ('cancel_owed_publish',dict(cancel_when='publish_offer',stall=True),dict(status=11,services=8,published=True,root=9,generation=8))]:
        cases.append(dict(name=name,kind='C',state=True,parameters=ps,env=env,expected=expected))
    cases.append(dict(name='cancel_owed_compute',kind='P',parameters=params,env=dict(cancel_when='command_offer',stall=True),expected=dict(status=11,services=1)))
    zero=list(params); zero[5]=0; zero[7]=1
    cases.append(dict(name='zero_local_loop',kind='P',parameters=zero,env={},expected=dict(status=7,services=2)))
    zero=list(params); zero[7]=0
    cases.append(dict(name='zero_mother_loop',kind='P',parameters=zero,env={},expected=dict(status=7,services=4)))
    reports={}; artifacts={}; results=[]; models={}
    def record(c,files,kinds,m):
        report=m.run(); f=out/(c['name']+'.json'); f.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        verdict=check.verify(report,files,kinds,c['expected']); reports[c['name']]=report; artifacts[c['name']]=(files,kinds,c); models[c['name']]=m
        results.append(dict(case=c,checker=verdict,ticks=report['ticks'],report_sha256=images.sha(f.read_bytes()),
            images_sha256={n:images.sha(b) for n,b in files.items()},outcome=report['outcome'],poison=report['poison']))
        print(c['name'],'PASS',report['ticks'],'model ticks',flush=True)
        return report
    for c in cases:
        files,kinds=images.build(c['kind'],c.get('state',False)); m=model.Model(files,kinds,c['parameters'],c['env']); record(c,files,kinds,m)
    files,kinds,c=artifacts['state_commit']; mutants=check.mutations(reports['state_commit'],files,kinds,c['expected'])
    for name,previous,ps,expect in [
        ('state_second_job_no_reset','state_commit',[9,13,8,3,102,1,1,1],dict(services=8,published=True,root=13,generation=9,initial_sequences={0:2,1:1,2:1})),
        ('state_after_error_no_reset','update_error',[5,13,7,3,103,1,1,1],dict(services=8,published=True,root=13,generation=8,initial_sequences={0:1,1:0,2:0}))]:
        m=models[previous]; m.install_job(ps,8); m.env={}; record(dict(name=name,expected=expect,no_reset=True),files,kinds,m)
    replay=dict(files); p=[dict(op='G_PARAM',a=i,x=i) for i in range(8)]+[dict(op='G_CALL',a=0,b=0,c=1),dict(op='G_WAIT',x=1),dict(op='G_END')]
    replay['mother']=images.assemble('mother',p,{},901)
    ps=[5,9,7,3,101,1,1,1]; m=model.Model(replay,kinds,ps,{},reports['lost_publish_ACK']['state'])
    record(dict(name='idempotent_publish_replay',expected=dict(services=1,published=True,root=9,generation=8)),replay,kinds,m)
    resets=[]
    for label,fs,ks,state in [('C_committed_unknown',files,kinds,reports['lost_publish_ACK']['state']),
                              ('C_uncommitted',files,kinds,reports['update_error_after_write']['state'])]:
        r=cohort.campaign(fs,ks,state,101); resets.append(dict(name=label,report=r))
    for kind in ['P','U','F','J']:
        fs,ks=images.build(kind); resets.append(dict(name=kind,report=cohort.campaign(fs,ks,dict(root=5,generation=7,store={5:0x12345678},journal={}),101)))
    post=resets[0]['report']; ps=[9,13,8,3,104,1,1,1]; m=model.Model(files,kinds,ps,dict(job=9,epoch=2),post['state'])
    record(dict(name='after_cohort_reset_query_reload',expected=dict(services=8,published=True,root=13,generation=9)),files,kinds,m)
    for name,delta in [('ADDI_overflow',1),('ADDI_negative',-1),('small_step_budget',0),('skip_mother_branch',0)]:
        fs,ks=images.build('P'); ps=[5,9,7,3,101,1,1,1]; raw=bytearray(fs['local0']); parsed=images.parse(bytes(raw),'P')
        expected=dict(services=2)
        if name=='ADDI_overflow': raw[128+2*16:128+3*16]=images.codec.encode_instruction(dict(op='L_MOVI',a=7,x=0xffffffff),'local').to_bytes(16,'little'); expected['status']=7
        elif name=='ADDI_negative':
            pc=next(i for i,ins in enumerate(parsed['program']) if ins['op']=='L_ADDI'); raw[128+pc*16:128+(pc+1)*16]=images.codec.encode_instruction(dict(op='L_ADDI',a=7,x=0xffffffff),'local').to_bytes(16,'little')
        elif name=='small_step_budget':
            h=parsed['header']; h['max_steps']=5; raw[:128]=images.codec.pack_record('image_header',h); expected.update(status=12,services=1)
        else: ps[4]=0; expected['services']=0
        fs['local0']=bytes(raw); images.parse(fs['local0'],'P'); m=model.Model(fs,ks,ps); record(dict(name=name,expected=expected),fs,ks,m)
    admission=[]
    for kind in images.SPEC['profiles']:
        fs,ks=images.build(kind,kind=='C'); data=fs['local0']; parsed=images.parse(data,ks[0]); h=parsed['header']
        variants={}
        raw=bytearray(data); raw[68]^=1; variants['wrong_ABI']=bytes(raw)
        raw=bytearray(data); raw[56]^=1; variants['wrong_profile_mask']=bytes(raw)
        raw=bytearray(data); raw[127]=1; variants['reserved_header_bits']=bytes(raw)
        raw=bytearray(data); raw[h['execution_offset']+4:h['execution_offset']+6]=(0xdead).to_bytes(2,'little'); variants['unknown_native_service']=bytes(raw)
        raw=bytearray(data); raw[h['task_offset']+4:h['task_offset']+8]=h['instruction_count'].to_bytes(4,'little'); variants['entry_out_of_bounds']=bytes(raw)
        raw=bytearray(data); r=images.RES['N'] if kind=='P' else images.RES['M']; raw[h['execution_offset']+2]=r; variants['unreachable_resource']=bytes(raw)
        for label,bad in variants.items():
            try: images.parse(bad,ks[0])
            except ValueError: admission.append(dict(profile=kind,name=label,rejected=True,input_sha256=images.sha(bad))); continue
            raise ValueError('accepted bad candidate image '+kind+' '+label)
    (out/'cohort_report.json').write_text(json.dumps(resets,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=dict(schema='candidate-five-control-profile-runs/0.1',results=results,mutation_checks=mutants,rtl_tested=False,deployable=False,
        negative_admission=admission,cohort_campaigns=len(resets),cohort_checks=sum(len(x['report']['results']) for x in resets),
        cohort_report_sha256=images.sha((out/'cohort_report.json').read_bytes()),
        ticks_are_hardware_cycles=False,native_numerical_operations_tested=False,full_Block_tested=False,physical_tested=False,python=sys.version)
    (out/'profiles_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(results),'candidate profile runs;',len(mutants),'mutations rejected',flush=True)


if __name__=='__main__': main()
