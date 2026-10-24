"""Independent diagnostic-output audit. Never imports producer implementation."""
import hashlib, json, math, subprocess, time
from pathlib import Path
from fractions import Fraction
import numpy as np

HERE=Path(__file__).resolve().parent
INPUT=HERE.parent/'returned-output'
REPO=Path('D:/Projects/LLMHardwareDesign-blockv2')
LLAMA=Path('D:/Projects/Codex/llama-downscale-20261023')
PROFILES={'Y8_cal_max':(8,-1,False),'Y8_original_2xcal':(8,0,False),
          'Y8_4xcal':(8,1,False),'Y16_original_same_range':(16,-8,False),
          'Y16_4xcal_range':(16,-7,False),'Y8_integer_row_delta':(8,0,True)}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rational(x,u,e):
    step=int(u)-int(e)
    return Fraction(int(x)*(1<<step),1) if step>=0 else Fraction(int(x),1<<-step)
def rn(x,u,e):return round(rational(x,u,e))
def delta_oracle(acc,unit,base):
    offsets=[]; trials=terms=0
    for a,u in zip(acc,unit):
        if all(int(t)==0 for t in a):offsets.append(0);continue
        for d in range(-16,17):
            trials+=1;terms+=len(a)
            # Exact Fraction; uses no producer shift, output code, or FP reference.
            if all(-128<=rn(x,v,int(e)+d)<=127 for x,v,e in zip(a,u,base)):
                offsets.append(d);break
        else:raise AssertionError('no admissible frozen offset')
    return np.asarray(offsets,dtype=np.int8),trials,terms
def oracle_codes(acc,unit,base,bits,off,delta):
    lo,hi=(-128,127) if bits==8 else(-32768,32512)
    out=np.empty(acc.shape,dtype=np.int64);sat=0
    for i,j in np.ndindex(acc.shape):
        v=rn(acc[i,j],unit[i,j],int(base[j])+off+int(delta[i]))
        sat+=v<lo or v>hi;out[i,j]=max(lo,min(hi,v))
    return out,int(sat)
def wire_bytes(n):
    result=0
    while n:
        payload=min(1984,n);result+=64+((payload+63)//64)*64;n-=payload
    return result
def rel(a,b):return float(np.linalg.norm(a-b)/max(float(np.linalg.norm(b.astype(np.float64))),1e-30))
def same_float(a,b):return math.isclose(float(a),float(b),rel_tol=1e-13,abs_tol=1e-15)
def same_dict(a,b):
    assert a.keys()==b.keys(),(a.keys(),b.keys())
    for k in a:
        if isinstance(a[k],float):assert same_float(a[k],b[k]),(k,a[k],b[k])
        else:assert a[k]==b[k],(k,a[k],b[k])
def verify_hash(p,m):
    count=0
    for name,r in m['artifacts'].items():
        q=p/name;assert q.stat().st_size==r['bytes'];assert sha(q)==r['sha256'];count+=1
    return count

def main():
    started=time.monotonic();runs=[];baseline_checks=0;llama_checked=False
    original={};llama=np.load(LLAMA/'numeric04/integers.npz',allow_pickle=False)
    llama_rows=json.loads((LLAMA/'numeric04/numeric.json').read_text())
    cm=json.loads((LLAMA/'capture02/manifest.json').read_text())
    qm=json.loads((LLAMA/'numeric04/manifest.json').read_text())
    assert sha(LLAMA/'numeric04/integers.npz')==qm['artifacts']['integers.npz']['sha256']
    assert sha(LLAMA/'capture02/capture.npz')==cm['artifacts']['capture.npz']['sha256']
    raw=np.load(LLAMA/'capture02/capture.npz',allow_pickle=False)
    for row in llama_rows:
        if row['profile'] in ('dynamic_none_max_128_128','dynamic_none_max_128_8192'):
            k='llama.layer0.down_proj.'+row['profile']+'.'+row['text']+'.'+row['phase'];original[k]=row
    for folder in ('output01','output02'):
        root=INPUT/folder;m=json.loads((root/'manifest.json').read_text());verified=verify_hash(root,m)
        blob=subprocess.run(['git','show',m['source_commit']+':project/experiments/block_decisions/output.py'],cwd=REPO,check=True,capture_output=True).stdout
        assert hashlib.sha256(blob).hexdigest()==m['source_sha256']
        z=np.load(root/'outputs.npz',allow_pickle=False);metrics=json.loads((root/'metrics.json').read_text());summaries=json.loads((root/'summary.json').read_text())
        keys=sorted(k[:-4] for k in z.files if k.endswith('.acc'))
        assert len(keys)==180==m['fixed_encoded_cases'];assert len(metrics)==1080==m['output_conditions']
        mm={(r['model']+'.'+r['linear']+'.'+r['case'],r['Y_profile']):r for r in metrics}
        assert len(mm)==len(metrics)
        values=delta_values=baseline=trials_all=terms_all=0;metadata_packets=0;negative=None
        expected_metrics=[];pre_err={};expected_delta={}
        for key in keys:
            a=z[key+'.acc'];u=z[key+'.units'];b=z[key+'.base'];ref=z[key+'.reference'];rows,n=a.shape
            assert a.dtype==np.int64 and u.shape==a.shape and b.shape==(n,) and ref.shape==a.shape
            d,trials,terms=delta_oracle(a,u,b);delta_values+=rows;trials_all+=trials;terms_all+=terms;expected_delta[key]=d
            real=a.astype(np.float64)*np.exp2(u.astype(np.float64));pre_err[key]=rel(real,ref)
            if key in original:
                row=original[key];prior=row['key']
                assert np.array_equal(a,llama[prior+'.acc']) and np.array_equal(u,llama[prior+'.e0'])
                assert np.array_equal(b,llama['Y_e'])
                prior_ref=raw[row['text']+'.Y'][:32] if row['phase']=='prefill' else raw[row['text']+'.Y'][32:]
                assert np.array_equal(ref,prior_ref)
            for name,(bits,off,dynamic) in PROFILES.items():
                mr=mm[(key,name)];delta=d if dynamic else np.zeros(rows,dtype=np.int8)
                expected,sat=oracle_codes(a,u,b,bits,off,delta);actual=z[key+'.'+name+'.codes']
                assert actual.dtype==np.dtype('int8' if bits==8 else 'int16')
                assert np.array_equal(expected,actual),(folder,key,name)
                if dynamic:assert np.array_equal(d,z[key+'.'+name+'.delta'])
                if negative is None:
                    forged=actual.copy();forged.flat[0]=int(forged.flat[0])+1 if int(forged.flat[0])<127 else int(forged.flat[0])-1
                    assert not np.array_equal(expected,forged)
                    negfile=HERE/('forged-rehashed-outputs-'+folder+'.npz')
                    copies={name:z[name] for name in z.files};copies[key+'.'+name+'.codes']=forged
                    np.savez_compressed(negfile,**copies)
                    forgehash=sha(negfile)
                    with np.load(negfile,allow_pickle=False) as forged_file:
                        assert not np.array_equal(expected,forged_file[key+'.'+name+'.codes'])
                    negative={'case':key,'profile':name,'mutant_path':str(negfile),'sha256_updated_to':forgehash,'status':'REJECTED by Fraction code oracle despite matching recomputed SHA'}
                values+=actual.size
                if name=='Y8_original_2xcal':
                    baseline+=actual.size
                    if key in original:assert np.array_equal(actual,llama[original[key]['key']+'.out']);baseline_checks+=actual.size
                ey=b.astype(np.int16)[None,:]+off+delta.astype(np.int16)[:,None]
                physical=expected.astype(np.float64)*np.exp2(ey.astype(np.float64))
                err=rel(physical,ref);sizes=[1]*rows if mr['case'].endswith('.decode') else [rows]
                explicit=sum(wire_bytes(r*n*(bits//8)+n+32+(r if dynamic else 0)) for r in sizes)
                reused=sum(wire_bytes(r*n*(bits//8)+n+32) for r in sizes)
                derived={'rows':rows,'outputs':n,'Y_bits':bits,'scale_offset':off,
                    'dynamic_row_delta_min':int(d.min()) if dynamic else None,
                    'dynamic_row_delta_max':int(d.max()) if dynamic else None,
                    'before_RQ_relative_rmse':pre_err[key],'after_RQ_relative_rmse':err,
                    'RQ_added_relative_rmse':rel(physical,real),'output_saturation':sat,
                    'local_diagnostic_screen':err<=.05 and sat==0,'Y_payload_bytes':rows*n*(bits//8),
                    'Y_static_exponent_bytes':n,'Y_dynamic_delta_bytes':rows if dynamic else 0,
                    'causal_packet_wire_explicit_delta_bytes':explicit,
                    'causal_packet_wire_delta_in_existing_header_bytes':reused,
                    'complete_output_acc64_tile_bytes':rows*n*8,
                    'one_row_acc64_units_base_and_output_buffer_bytes':n*(8+2+1+bits//8),
                    'dynamic_delta_candidate_trials':trials if dynamic else 0,
                    'dynamic_delta_RNE_compare_terms':terms if dynamic else 0,
                    'range_guard_coefficients_U32_bytes':((mr['K']+127)//128)*n*4,
                    'downstream_S8_matrix_products_per_W8_A_MAC':3 if bits==16 else 1}
                same_dict(derived,{x:mr[x] for x in derived});metadata_packets+=2
                expected_metrics.append(mr)
        assert values==410112==m['independent_Fraction_RNE_values'];assert baseline==68352==m['baseline_codes_exact']
        rebuilt=[]
        for model,label,profile in sorted({(r['model'],r['linear'],r['Y_profile']) for r in metrics}):
            rr=[r for r in expected_metrics if (r['model'],r['linear'],r['Y_profile'])==(model,label,profile)]
            rebuilt.append({'model':model,'linear':label,'Y_profile':profile,'conditions':len(rr),
                'worst_before_RQ':max(r['before_RQ_relative_rmse'] for r in rr),
                'worst_after_RQ':max(r['after_RQ_relative_rmse'] for r in rr),
                'saturations':sum(r['output_saturation'] for r in rr),
                'all_local_diagnostic_screen':all(r['local_diagnostic_screen'] for r in rr),
                'maximum_Y_delta_payload_bytes':max(r['Y_dynamic_delta_bytes'] for r in rr),
                'max_delta_terms_per_case':max(r['dynamic_delta_RNE_compare_terms'] for r in rr)})
        assert len(rebuilt)==len(summaries)
        for a,b in zip(rebuilt,summaries):same_dict(a,b)
        runs.append({'run':folder,'source_commit':m['source_commit'],'source_sha256':m['source_sha256'],
             'artifact_hashes_verified':verified,'cases':len(keys),'conditions':len(metrics),
             'Fraction_output_values':values,'independent_dynamic_delta_rows':delta_values,
             'dynamic_delta_fraction_candidate_trials':trials_all,'dynamic_delta_fraction_terms':terms_all,
             'metric_fields_and_packet_variants_verified':metadata_packets,'summary_groups':len(summaries),
             'artifacts':m['artifacts'],'input_manifest_bindings':m['input_manifests'],
             'negative_rehashed_code':negative,
             'llama_readout':[r for r in summaries if r['model']=='llama']})
    for n in ('metrics.json','summary.json','outputs.npz'):
        assert sha(INPUT/'output01'/n)==sha(INPUT/'output02'/n)
    manifest1=json.loads((INPUT/'output01/manifest.json').read_text());manifest2=json.loads((INPUT/'output02/manifest.json').read_text())
    manifest1.pop('seconds');manifest2.pop('seconds');assert manifest1==manifest2
    receipt={'status':'PASS','audit_script_sha256':sha(Path(__file__)),'seconds':time.monotonic()-started,
       'independence':'No producer imports; Fraction ties-to-even at every element and independent per-row offset search, metric and packet recomputation.',
       'two_round_science_files_identical':True,'manifests_equal_except_runtime_seconds':True,
       'Llama_original_encoded_cases_exact':len(original),'Llama_original_baseline_codes_exact_across_two_runs':baseline_checks,
       'Llama_original_encoded_npz_sha256':sha(LLAMA/'numeric04/integers.npz'),
       'Llama_original_capture_npz_sha256':sha(LLAMA/'capture02/capture.npz'),
       'scope_limits':['Three server upstream A/W/partial arrays not redownloaded/reproved in this audit; provenance SHA bound to original manifests.',
          'Llama prior A/W/partial not recomputed here; acc, units, base, FP diagnostic reference and original Y8 output matched original files for all 12 included cases.',
          'Llama approximately 4.93% is reused previously observed diagnostic evidence, not a new independent model-quality acceptance.',
          'Packets and minimum buffer/metadata plus base-product multiplier are accounting assumptions, not full next-S8/residual/norm scheduling, cycles, RTL or PPA.'],
       'runs':runs}
    (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('status','seconds','two_round_science_files_identical','Llama_original_encoded_cases_exact','Llama_original_baseline_codes_exact_across_two_runs')}))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--llama',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('refuse existing audit output')
    args.out.mkdir(parents=True)
    INPUT,REPO,LLAMA,HERE=args.input,args.repo,args.llama,args.out
    main()
