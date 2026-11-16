"""Add heterogeneous unsaturated inputs, replay both implementation families."""
import argparse,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/block_synthesis').resolve()))
from resident_survey import reference
from verify_resident_batch import replay


def main():
    parser=argparse.ArgumentParser()
    for n in ('lane','original','ir','output'):parser.add_argument(n,type=Path)
    a=parser.parse_args();data=json.loads(a.lane.read_text());old=json.loads(a.original.read_text());ir=json.loads(a.ir.read_text())
    fixtures=list(data['fixtures']);rng=random.Random(2192402)
    inputs=sorted({(o['tensor'],o['index']) for o in data['tile']['graph']['objects'].values() if o['kind']=='external' and 'literal' not in o})
    bitwidth={(o['tensor'],o['index']):o['bits'] for o in data['tile']['graph']['objects'].values() if o['kind']=='external' and 'literal' not in o}
    for mode in range(3):
        values=[]
        for j,(tensor,index) in enumerate(inputs):
            if mode==0:v=(65537,-131071,32769,-65535,1,-1)[j%6]
            elif mode==1:v=(127,-257,513,-1025,2049,-4097)[j%6]
            else:v=rng.randrange(-(1<<23),1<<23)
            if bitwidth[(tensor,index)]==16:v=max(-32768,min(32767,v))
            values.append([tensor,index,v])
        fixtures.append({'inputs':values})
    checked=0
    for fixture in fixtures:
        values={(t,i):v for t,i,v in fixture['inputs']}
        for family in (old,data):
            tile=family['tile']
            for program in family['programs'].values():
                observed=replay(tile,program,values)['observed_native_outputs'];checked+=1
                for rr,g in enumerate(tile['graphs']):
                    for primitive,v in reference(ir['primitive_program'],g,values).items():
                        word=observed[tile['graph']['primitive_outputs'][f'{rr}:{primitive}']]&0xffffffff
                        if (word-(1<<32) if word&(1<<31) else word)!=v:raise ValueError('heterogeneous fixture differs from original integer reference')
    data['fixtures']=fixtures;data['fixture_provenance']={'additional':'signed nonuniform 17-bit, small odd, seeded 24-bit inputs','seed':2192402}
    a.output.write_text(json.dumps(data,separators=(',',':'))+'\n')
    print(json.dumps({'passed':True,'fixtures':len(fixtures),'independent_numeric_traces':checked,'note':'no plan or hardware changes'}))


if __name__=='__main__':main()
