"""Validate pinned real tensor ABI, compile C++17, run bounded layer0 numeric gate.

Standard library only. This launches numerical C++, never RTL. Root schedules
this command in the authorized server directory; this file does not SSH/Slurm.
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

REVISION='c1899de289a04d12100db370d81485cdf75e47ca'
TENSORS={
 'input_norm':('model.layers.0.input_layernorm.weight',[1024]),
 'post_norm':('model.layers.0.post_attention_layernorm.weight',[1024]),
 'q_norm':('model.layers.0.self_attn.q_norm.weight',[128]),
 'k_norm':('model.layers.0.self_attn.k_norm.weight',[128]),
 'q_proj':('model.layers.0.self_attn.q_proj.weight',[2048,1024]),
 'k_proj':('model.layers.0.self_attn.k_proj.weight',[1024,1024]),
 'v_proj':('model.layers.0.self_attn.v_proj.weight',[1024,1024]),
 'o_proj':('model.layers.0.self_attn.o_proj.weight',[1024,2048]),
 'gate_proj':('model.layers.0.mlp.gate_proj.weight',[3072,1024]),
 'up_proj':('model.layers.0.mlp.up_proj.weight',[3072,1024]),
 'down_proj':('model.layers.0.mlp.down_proj.weight',[1024,3072])}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            block=f.read(1048576)
            if not block:break
            h.update(block)
    return h.hexdigest()


def resolve(root,relative):
    p=(root/relative).resolve()
    if p!=root and root not in p.parents:raise ValueError('input path escapes data directory')
    if any(c in str(p) for c in '\t\r\n'):raise ValueError('TSV control byte in path')
    return p


def check_tensor(root,entry,expected_shape):
    if entry['shape']!=expected_shape or entry['source_dtype']!='BF16':raise ValueError('tensor ABI shape/dtype')
    count=1
    for n in expected_shape:count*=n
    bf=resolve(root,entry['bf16le_file']);fp=resolve(root,entry['f32le_file'])
    for path,key,nbytes in [(bf,'bf16le',count*2),(fp,'f32le',count*4)]:
        if path.stat().st_size!=nbytes or entry[key+'_bytes']!=nbytes or sha(path)!=entry[key+'_sha256']:
            raise ValueError('data SHA/length mismatch '+str(path))
    # Full independent bit expansion verification, not sample-only checking.
    b16=memoryview(bf.read_bytes()).cast('H');b32=memoryview(fp.read_bytes()).cast('I')
    if not all((int(a)<<16)==int(b) for a,b in zip(b16,b32)):raise ValueError('BF16->F32 bit expansion mismatch')
    return fp,count


def index_rtl_exports(out):
    """Bind exported real rows to canonical native-F1024 request-order streams."""
    profiles={};fixtures=[]
    for line in (out/'rtl-export-rows.tsv').read_text(encoding='utf-8').splitlines():
        a=line.split('\t')
        if len(a)!=13:raise ValueError('RTL export row ABI')
        profile,fixture,case,kind=a[:4];pos,sat,xf,nf,wg,wu,wd,epsilon,input_clip=map(int,a[4:])
        base=out/'rtl_exports'/profile
        if profile not in profiles:
            blobs=[(base/(name+'.s8')).read_bytes() for name in ['gate','up','down']]
            if [len(b) for b in blobs]!=[3145728]*3:raise ValueError('RTL export matrix byte length')
            stream=base/'weights-stream.bin';digest=hashlib.sha256();count=0
            with stream.open('wb') as f:
                for group in range(384):
                    for matrix in [0,1]:
                        raw=blobs[matrix];K=1024
                        for chunk in range(32):
                            payload=b''.join(raw[(group*8+n)*K+chunk*32+tile*8:(group*8+n)*K+chunk*32+tile*8+8]
                              for tile in range(4) for n in range(8))
                            if len(payload)!=256:raise ValueError('native chunk packing')
                            f.write(payload);digest.update(payload);count+=256
                raw=blobs[2];K=3072
                for group in range(128):
                    for chunk in range(96):
                        payload=b''.join(raw[(group*8+n)*K+chunk*32+tile*8:(group*8+n)*K+chunk*32+tile*8+8]
                          for tile in range(4) for n in range(8))
                        f.write(payload);digest.update(payload);count+=len(payload)
            if count!=9437184:raise ValueError('RTL canonical stream length')
            profiles[profile]={'X_Fin':xf,'norm_gamma_Fin':nf,'gate_up_mid_Fin':10,
                'weights_Fin':[wg,wu,wd],'M_READ_right_shift':[nf+wg-10,nf+wu-10,10+wd-xf],
                'M_factor':1,'M_left_shift':0,'epsilon_code':epsilon,
                'current_top_compatible':profile=='current_Fin10_WFin7',
                'requires_new_static_top_profile':profile!='current_Fin10_WFin7',
                'weights_stream_file':str(stream.relative_to(out)).replace('\\','/'),
                'weights_stream_bytes':count,'weights_stream_sha256':digest.hexdigest(),
                'weight_requests':36864,'weight_beats':589824,
                'source_weights':[{'file':str((base/(n+'.s8')).relative_to(out)).replace('\\','/'),
                   'bytes':len(blobs[i]),'sha256':sha(base/(n+'.s8'))} for i,n in enumerate(['gate','up','down'])]}
        stages={}
        for stage,nwords in [('input',128),('norm',128),('gate',384),('up',384),('mid',384),('down',128),('output',128)]:
            binary=base/fixture/(stage+'.s16le');hexfile=base/fixture/(stage+'.hex')
            lines=hexfile.read_text(encoding='ascii').splitlines()
            if len(lines)!=nwords or any(len(s)!=32 for s in lines):raise ValueError('stage hex word count')
            if b''.join(int(s,16).to_bytes(16,'little') for s in lines)!=binary.read_bytes():raise ValueError('stage hex/binary mismatch')
            stages[stage]={'hex_file':str(hexfile.relative_to(out)).replace('\\','/'),'words128':nwords,'sha256':sha(hexfile)}
        gamma=base/'gamma.hex'
        if len(gamma.read_text(encoding='ascii').splitlines())!=128:raise ValueError('gamma128 words')
        fd=base/fixture
        (fd/'gamma.hex').write_bytes(gamma.read_bytes())
        (fd/'expected-output.hex').write_bytes((fd/'output.hex').read_bytes())
        (fd/'expected-saturated.hex').write_bytes((str(sat)+'\n').encode('ascii'))
        one={'id':fixture,'case':case,'split':kind,'position':pos,'profile':profile,
          'expected_native_done_saturated':bool(sat),'offline_input_quant_clips':input_clip,
          'stages':stages,'gamma_hex_file':str(gamma.relative_to(out)).replace('\\','/'),
          'gamma_hex_sha256':sha(gamma),'X_Fin':xf,'norm_gamma_Fin':nf,
          'weights_Fin':[wg,wu,wd],'M_GATE_SHIFT':nf+wg-10,'M_UP_SHIFT':nf+wu-10,
          'M_DOWN_SHIFT':10+wd-xf,'N_EPSILON':epsilon,
          'weight_stream_relative_file':'../weights-stream.bin',
          'weights_stream_bytes':profiles[profile]['weights_stream_bytes'],
          'weights_stream_sha256':profiles[profile]['weights_stream_sha256'],
          'expected_saturated_hex_file':'expected-saturated.hex',
          'static_profile_binding':{'H':1024,'I':3072,'N_EPSILON':epsilon,
             'M_GATE_SHIFT':nf+wg-10,'M_UP_SHIFT':nf+wu-10,'M_DOWN_SHIFT':10+wd-xf,
             'G_Fin':10},
          'scope':'integer fixture expectation,not FP32 quality acceptance'}
        (fd/'fixture.json').write_bytes((json.dumps(one,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        fixtures.append(one)
    result={'schema_version':1,'profiles':profiles,'fixtures':fixtures,
      'packing':'128bit hex, lane0 low16; canonical weight tile-major/n-major/k8,16beats/chunk',
      'selection':'baseline plus cal-only selected candidate;last token from every cal/eval prefix',
      'status':'PREPARED_REAL_DATA_RTL_FIXTURES_NOT_RTL_EXECUTED'}
    (out/'rtl-fixture-index.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--engine-source',type=Path,default=Path(__file__).with_name('qwen_layer0_numeric.cpp'))
    p.add_argument('--threads',type=int,default=8);a=p.parse_args()
    if sys.byteorder!='little':raise ValueError('little-endian verification required')
    if not 1<=a.threads<=8:raise ValueError('threads must be1..8 within assigned resource')
    root=a.data_dir.resolve();out=a.output.resolve()
    if out.exists():raise FileExistsError('immutable result directory already exists: '+str(out))
    out.mkdir(parents=True,exist_ok=False)
    manifest_path=root/'manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['repo']!='Qwen/Qwen3-0.6B' or manifest['revision']!=REVISION:raise ValueError('unpinned model data')
    if manifest.get('status')!='COMPLETE_SELECTED_TENSORS_AND_ROWS':raise ValueError('incomplete selected model data manifest')
    receipt={'status':'RUNNING_NUMERICAL_DIAGNOSTIC_NOT_RTL','engine_source_sha256':sha(a.engine_source),
       'runner_sha256':sha(Path(__file__)),'manifest_sha256':sha(manifest_path),'repo':manifest['repo'],
       'revision':manifest['revision'],'threads':a.threads,'commands':[],'inputs':[]}
    try:
        config_path=resolve(root,manifest['config_file']);config=json.loads(config_path.read_text(encoding='utf-8'))
        for key,value in {'hidden_size':1024,'intermediate_size':3072,'num_attention_heads':16,
          'num_key_value_heads':8,'head_dim':128,'rms_norm_eps':1e-6,'rope_theta':1000000,
          'attention_bias':False,'hidden_act':'silu'}.items():
            if config.get(key)!=value:raise ValueError('unexpected config '+key)
        entries={v['name']:v for v in manifest['tensors']};tsv=[];verified_values=0
        for label,(name,shape) in TENSORS.items():
            fp,count=check_tensor(root,entries[name],shape);verified_values+=count
            rows=shape[0] if len(shape)==2 else 1;cols=shape[1] if len(shape)==2 else shape[0]
            tsv.append('\t'.join([label,str(fp),str(rows),str(cols)]))
            receipt['inputs'].append({'name':name,'shape':shape,'f32le_sha256':sha(fp)})
        embeddings={int(v['token_id']):v for v in manifest['embedding_rows']}
        casepath=resolve(root,manifest['token_sequences_file']);case_data=json.loads(casepath.read_text(encoding='utf-8'))
        cases=case_data['token_sequences'];seenids=set();seen_sequences={};case_lines=[];used=set();splits={'cal':0,'eval':0}
        for case in cases:
            name=case['id'];kind=case['split'];ids=case['token_ids']
            if kind not in splits or not 1<=len(ids)<=16 or len(ids)!=len(case['pieces']):raise ValueError('bounded case ABI')
            if not name or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for ch in name):raise ValueError('unsafe case ID')
            if name in seenids:raise ValueError('duplicate case ID')
            seq=tuple(ids)
            if seq in seen_sequences and seen_sequences[seq]!=kind:raise ValueError('same exact sequence crosses cal/eval')
            seenids.add(name);seen_sequences[seq]=kind;splits[kind]+=1
            if any(type(t)!=int or not 0<=t<151936 or t not in embeddings for t in ids):raise ValueError('invalid/missing token row')
            used.update(ids);case_lines.append('\t'.join([name,kind,','.join(map(str,ids))]))
        if not all(splits.values()):raise ValueError('cal/eval both required')
        for token in sorted(used):
            fp,count=check_tensor(root,embeddings[token],[1024]);verified_values+=count
            tsv.append('\t'.join(['embedding_'+str(token),str(fp),'1','1024']))
        (out/'tensor-map.tsv').write_bytes(('\n'.join(tsv)+'\n').encode('utf-8'))
        (out/'cases.tsv').write_bytes(('\n'.join(case_lines)+'\n').encode('utf-8'))
        receipt['BF16_to_F32_values_bit_verified']=verified_values
        receipt['token_sequences_sha256']=sha(casepath);receipt['config_sha256']=sha(config_path)
        receipt['cases']=[{'id':c['id'],'split':c['split'],'token_ids':c['token_ids'],'pieces':c['pieces']} for c in cases]
        environment=os.environ.copy();environment['OMP_NUM_THREADS']=str(a.threads)
        engine=out/'qwen-layer0-numeric'
        commands=[('compiler-version',['g++','--version']),
          ('compile',['g++','-std=c++17','-O2','-ffp-contract=off','-fopenmp',str(a.engine_source.resolve()),'-o',str(engine)]),
          ('self-test',[str(engine),'--self-test']),
          ('numeric',[str(engine),str(out/'tensor-map.tsv'),str(out/'cases.tsv'),str(out)])]
        for label,cmd in commands:
            log=out/(label+'.log')
            with log.open('wb') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=environment)
            receipt['commands'].append({'label':label,'argv':cmd,'exit_code':result.returncode,'log':log.name,'sha256':sha(log)})
            if result.returncode:raise RuntimeError(label+' failed; see '+str(log))
        summary=json.loads((out/'numeric-summary.json').read_text(encoding='utf-8'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON '+x)))
        profiles=summary['profiles'];selected=min(profiles,key=lambda v:v['metrics']['cal']['output']['relative_L2'])
        if selected['id']!=summary['selected_candidate']:raise ValueError('selection not cal metric minimum')
        for v in profiles:
            if v['gate_up_mid_Fin']!=10 or not all(0<=s<=63 for s in v['M_READ_right_shift']):raise ValueError('unsupported numeric candidate')
            if not 1<=v['epsilon_code']<=0xffffffff:raise ValueError('native epsilon invalid')
            if not {'cal','eval'}.issubset(v['metrics']):raise ValueError('split metrics missing')
        exported=index_rtl_exports(out)
        receipt['RTL_exported_profiles']=list(exported['profiles']);receipt['RTL_exported_rows']=len(exported['fixtures'])
        receipt['selected_candidate']=summary['selected_candidate'];receipt['status']='PASS_SELECTED_LAYER0_NUMERICAL_DIAGNOSTIC_NOT_RTL_OR_FULL_MODEL_QUALITY'
        receipt['outputs']=[{'path':str(q.relative_to(out)).replace('\\','/'),'bytes':q.stat().st_size,'sha256':sha(q)}
          for q in sorted(out.rglob('*')) if q.is_file() and q!=engine and q.name!='numeric-run-receipt.json']
    except Exception as e:
        receipt['status']='FAIL_NUMERICAL_DIAGNOSTIC';receipt['error']=str(e)
        raise
    finally:
        (out/'numeric-run-receipt.json').write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('PASS_QWEN_LAYER0_DIAGNOSTIC selected='+receipt['selected_candidate'])


if __name__=='__main__':main()
