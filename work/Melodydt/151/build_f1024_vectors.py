"""Independent full-dimension fixtures and optional canonical server mirrors."""
import argparse,json,hashlib
from pathlib import Path
from f1024_integer_reference import f1024,canonical_weight_stream,prior,weight,REFERENCE_DEPENDENCIES

NORMAL={'input':256,'S':888076,'S_write':739084,'S_read':148992,'M':40448,
 'M_EXEC':36864,'N_native':258,'G_services':384,'G_pairs':1536,'E_services':128,
 'loader':36864,'wide_reads':294912,'A_beats':147456,'B_beats':147456,
 'weight_requests':36864,'weight_beats':589824,'weight_bytes':9437184,
 'T_words':128,'T_release':1}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--weight-directory',type=Path);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    if a.weight_directory:a.weight_directory.mkdir(parents=True,exist_ok=True)
    f=prior(a.root)
    tables={'G':f.validate_native_table((a.root/'project/rtl/block_v2/block_v2_g_tables.svh').read_text(encoding='utf-8'))}
    defs=[('dense',37,0x1234,[((29*i+17)%4093)-2046 for i in range(1024)],
           [512+((17*i+5)%1537) for i in range(1024)]),
          ('gamma0',91,0x4321,[((59*i+11)%65521)-32760 for i in range(1024)],[0]*1024)]
    vectors=[];direct_checks=[]
    for index,(name,seed,version,x,gamma) in enumerate(defs):
        result=f1024(a.root,x,gamma,seed)
        # Independent ungrouped full-K dots verify the period reduction itself.
        for matrix_no,source,names,key in [
          (0,result['norm'],[0,1,7,250,251,511,1023,3071],'gate_raw'),
          (1,result['norm'],[0,1,7,250,251,511,1023,3071],'up_raw'),
          (2,result['mid'],[0,1,7,127,250,251,511,1023],'down_raw')]:
            for n in names:
                direct=sum(value*weight(matrix_no,n,k,seed) for k,value in enumerate(source))
                assert direct==result[key][n]
                direct_checks.append({'fixture':name,'matrix':matrix_no,'n':n,
                  'full_K':len(source),'ungrouped_raw':direct,'matches_grouped':True})
        path=a.weight_directory/('weights-'+name+'.bin') if a.weight_directory else None
        stream=canonical_weight_stream(seed,path)
        vectors.append({'index':index,'id':name,'seed':seed,'weights_version':version,
          'X':x,'gamma':gamma,'expected':result,'canonical_weight_stream':stream})
        print(name,'sat',result['done_saturated'],'weightSHA',stream['sha256'])
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result={'schema_version':1,'status':'INDEPENDENT_FULL_DIMENSION_INTEGER_EXPECTATIONS_NOT_RTL_EXECUTION',
      'research_parent':'75d99a5ba01adba1e978db3933a41e1d43c49c30',
      'native_source':'707878621b2add4ed218b8c43df2e95c9a56e2ba',
      'reference_sha256':sha(Path(__file__).with_name('f1024_integer_reference.py')),
      'reference_dependencies':[{'path':x,'sha256':sha(a.root/x)} for x in REFERENCE_DEPENDENCIES],
      'weight_recipe':'((13*n+7*k+seed+41*matrix)%251)-125; matrix gate0/up1/down2',
      'stream_order':'gate32chunks,up32chunks for group0..383;then down96chunks for group0..127;tile-major n-major k-minor;16beats/chunk',
      'normal_counts':NORMAL,'table_validation':tables,'selected_ungrouped_full_dot_checks':direct_checks,'vectors':vectors,
      'quality_scope':'selected fixture integer profile,not trained Qwen3 epsilon/quantization/checkpoint/model quality'}
    (a.directory/'f1024-contract-vectors.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    index={'status':'EXPECTED_CANONICAL_INPUT_STREAMS_NOT_OBSERVED_RTL',
      'streams':[dict(v['canonical_weight_stream'],fixture=v['id'],seed=v['seed'],
         binary_filename='weights-'+v['id']+'.bin') for v in vectors]}
    (a.directory/'f1024-weight-stream-index.json').write_bytes((json.dumps(index,indent=2)+'\n').encode('utf-8'))
    print('PASS_F1024_MATH_VECTORS fixtures=2;noRTLrun')


if __name__=='__main__':main()
