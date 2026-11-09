"""Independently recheck every immutable cold tile against original arithmetic."""
import argparse,hashlib,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from native_pointwise import execute
from resident_survey import reference
from verify_resident_batch import replay


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('ir',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    read=lambda f:json.loads(f.read_text(encoding='utf-8'))
    receipt=read(a.directory/'receipt.json')
    for name,meta in receipt['recovered'].items():
        if hashlib.sha256((a.directory/name).read_bytes()).hexdigest()!=meta['sha256']:raise ValueError('recovered evidence differs')
    slurm=(a.directory/'slurm.psv').read_text()
    if f"{receipt['job']}|COMPLETED|0:0|" not in slurm:raise ValueError('batch survey is not terminal success')
    summary=read(a.directory/'generated/summary.json');ir=read(a.ir);rng=random.Random(220212);rows=[];traces=0
    for row in summary['rows']:
        file=a.directory/'generated'/row['program_file'];data=read(file);tile=data['tile'];programs=data['programs']
        for trial in range(4):
            values={}
            for o in tile['graph']['objects'].values():
                if o['kind']!='external' or 'literal' in o:continue
                v=(-2147483648,2147483647,0)[trial] if trial<3 else rng.randrange(-(1<<31),1<<31)
                if o['bits']==16:v=max(-32768,min(32767,v))
                values[(o['tensor'],o['index'])]=v
            for name,program in programs.items():
                result=replay(tile,program,values);observed=result['observed_native_outputs'];traces+=1
                for rr,g in enumerate(tile['graphs']):
                    gold=execute(g,values)
                    for primitive,record in g['primitive_outputs'].items():
                        key=tile['graph']['primitive_outputs'][f'{rr}:{primitive}']
                        if observed[key]!=gold[record]:raise ValueError('native row differs')
                    for primitive,v in reference(ir['primitive_program'],g,values).items():
                        key=tile['graph']['primitive_outputs'][f'{rr}:{primitive}'];word=observed[key]&0xffffffff
                        if (word-(1<<32) if word&(1<<31) else word)!=v:raise ValueError('original integer graph differs')
        for name,program in programs.items():
            for key in ('total_ticks','copy_ticks','native_service_ticks','external_words','expanded'):
                if row['plans'][name][key]!=program[key]:raise ValueError('survey summary differs')
        strongest=min((p for n,p in programs.items() if 'greedy' in n),key=lambda p:p['total_ticks'])
        dp=programs['batch_dp'];gain=1-dp['total_ticks']/strongest['total_ticks']
        if abs(gain-row['dp_vs_strongest_greedy_fraction'])>1e-15:raise ValueError('wrong comparison denominator')
        rows.append({'region':row['primitives'][0],'rows':row['rows'],'dp_gain_fraction':gain,
                     'file_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    result={'passed':True,'job':receipt['job'],'cold_tiles':len(rows),'plans':sum(len(read(a.directory/'generated'/r['program_file'])['programs']) for r in summary['rows']),
        'independent_numeric_traces':traces,'rows':rows,'ir_sha256':hashlib.sha256(a.ir.read_bytes()).hexdigest(),
        'scope':'synthetic edge/random cold tiles with original arithmetic; actual weights/full-loop/batch RTL/system excluded'}
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))


if __name__=='__main__':main()
