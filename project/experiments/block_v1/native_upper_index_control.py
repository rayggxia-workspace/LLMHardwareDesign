"""Compare the indexed contact audit with the exhaustive geometry oracle."""
import collections
import hashlib
import json
from pathlib import Path
import random
import sys
from native_escape_audit import upper_shorts,geometry
from native_upper_index import audit


def contacts(result):
    return collections.Counter(tuple(sorted([(r['net'],r['layer'],tuple(r['box'])),
                                             (r['other'],r['other_layer'],tuple(r['other_box']))]))for r in result['shorts'])


def verify(data):
    reference=upper_shorts(data);expected=contacts(reference);checks=[]
    for pitch in [513,1600,6400]:
        actual=audit(data,pitch)
        assert contacts(actual)==expected and actual['passed']==reference['passed']
        assert actual['shape_count']==reference['shape_count']and actual['net_count']==reference['net_count']
        checks.append(dict(cell_dbu=pitch,pairs=actual['exact_candidate_pair_checks']))
    return dict(shapes=reference['shape_count'],contact_shape_pairs=sum(expected.values()),checks=checks)


def main(folder,destination):
    assert not destination.exists();rows=[]
    for policy in ['a','c']:
        for stage in ['before','after']:
            path=folder/('upper159-'+policy+'-'+stage+'.tsv');result=verify(geometry(path))
            assert (result['contact_shape_pairs']==0)==(stage=='after')
            rows.append(dict(policy=policy,stage=stage,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**result))
    rng=random.Random(163);generated=[]
    for case in range(12):
        data=collections.defaultdict(list)
        for i in range(160):
            x,y=[rng.randrange(-80,81)*160 for _ in range(2)];w,h=[rng.choice([1,160,513,1600,6400,20000])for _ in range(2)]
            data['net'+str(rng.randrange(7))].append((rng.choice(['metal8','metal9','via9','metal10']),'declared',(x,y,x+w,y+h)))
        generated.append(verify(data))
    boundary={'a':[('metal10','declared',(-6400,-1600,0,0)),('metal9','declared',(513,0,6400,1600))],
              'b':[('via9','declared',(0,-1600,513,0)),('metal10','declared',(513,0,6400,1600))]}
    edge=verify(boundary);assert edge['contact_shape_pairs']>0
    isolated={'a':[('metal9','declared',(0,0,6400,6400))],'b':[('metal10','declared',(0,0,6400,6400))]}
    assert verify(isolated)['contact_shape_pairs']==0
    destination.write_text(json.dumps(dict(passed=True,actual_routed_cases=rows,declared_random_cases=generated,
        exact_negative_coordinate_and_bucket_edges=edge,uncut_different_metal_layers_do_not_short=True,
        scope='Indexed versus exhaustive contact-pair identity on four SHA-bound real geometry files and declared controls; not full physical qualification'),indent=2)+'\n')


if __name__=='__main__':main(Path(sys.argv[1]),Path(sys.argv[2]))
