"""Relabel proven native boxes in the accepted scene without changing geometry."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct

HEADER=struct.Struct('<8sIQd');RECORD=struct.Struct('<ii6d')
BASE=Path('/public/home/yuzelu/PingyangHuang')
SCENE=BASE/'issue-222-coupling-DuSb4uk1/job-100170/result'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def read_header(f):
    raw=f.read(HEADER.size);magic,n,count,eps=HEADER.unpack(raw);assert magic==b'NATIVE22'
    names=[];flags=[];parts=[raw]
    for i in range(n):
        lb=f.read(4);ln=struct.unpack('<I',lb)[0];name=f.read(ln);flag=f.read(1)
        names.append(name.decode());flags.append(flag[0]);parts += [lb,name,flag]
    return names,flags,count,eps,b''.join(parts)


def make_header(names,flags,count,eps):
    data=[HEADER.pack(b'NATIVE22',len(names),count,eps)]
    for name,flag in zip(names,flags):
        s=name.encode();data += [struct.pack('<I',len(s)),s,bytes([flag])]
    return b''.join(data)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probes',type=Path,nargs='+',required=True)
    p.add_argument('--base-scene',type=Path)
    p.add_argument('--out',type=Path,default=Path(os.environ.get('LOWER_OUT','.')))
    a=p.parse_args();a.out.mkdir()
    meta=json.loads((SCENE/'scene.json').read_text())
    refs=json.loads((BASE/'issue-215-top-pex-zOz2uxIr/route-206.json').read_text())
    previous=json.loads((a.base_scene/'scene.json').read_text()) if a.base_scene else None
    if previous:assert previous['exact_box_matches'] and previous['conductor_coordinates_order_and_ownership_unchanged']
    source_file=a.base_scene/'with-upper.bin' if previous else SCENE/'scene.bin'
    lower_file=a.base_scene/'without-upper.bin' if previous else SCENE/'lower-only.bin'
    expected_source_sha=previous['files']['with-upper.bin']['sha256'] if previous else meta['scene_sha256']
    with source_file.open('rb') as f:names,flags,full_count,eps,source_header=read_header(f)
    with lower_file.open('rb') as f:ln,lf,lower_count,le,_=read_header(f)
    assert (ln,lf,le)==(names,flags,eps)
    upper_count=full_count-lower_count;assert upper_count>0
    instances=sorted(refs['native_masks']);old_groups={n:2491+i for i,n in enumerate(instances)}
    rename={};expected=Counter();selected=[];inputs={}
    for folder in a.probes:
        proof=json.loads((folder/'probe.json').read_text());kind=proof['kind']
        assert sha(folder/'selected-boxes.bin')==proof['selected_boxes_sha256']
        assert sha(folder/'targets.json')==proof['targets_sha256']
        inputs[str(folder)]=dict(probe_sha256=sha(folder/'probe.json'),**proof)
        targets=json.loads((folder/'targets.json').read_text())
        local={};geometry={}
        for inst in meta['sources'][kind]['instances']:
            for target in targets:
                nid=len(names);names.append('LOWER_'+inst+'_'+proof.get('inventory_kind',kind)+'_T'+str(proof['minimum_highest_metal'])+'_'+str(target['local_id']));flags.append(0)
                local[(inst,target['local_id'])]=nid
                selected.append(dict(id=nid,name=names[-1],instance=inst,kind=kind,target=target))
        with (folder/'selected-boxes.bin').open('rb') as f:
            while True:
                raw=f.read(RECORD.size*65536)
                if not raw:break
                for local_id,owner,*box in RECORD.iter_unpack(raw):
                    assert owner==1
                    for inst in meta['sources'][kind]['instances']:
                        ox,oy=refs['positions_um'][inst]
                        coords=[box[0]+ox,box[1]+oy,box[2],box[3]+ox,box[4]+oy,box[5]]
                        key=(old_groups[inst],struct.pack('<6d',*coords));nid=local[(inst,local_id)]
                        assert key not in rename,('Duplicate requested conductor box',inst,local_id)
                        rename[key]=nid;expected[nid]+=1
    assert selected and len(expected)==len(selected)
    assert len(names)==len(set(names)),'Duplicate electrode labels'
    source_hash=hashlib.sha256();source_hash.update(source_header)
    hashes={n:hashlib.sha256() for n in ['with-upper.bin','without-upper.bin']};seen=Counter();processed=0
    with source_file.open('rb') as source,(a.out/'with-upper.bin').open('xb') as full,(a.out/'without-upper.bin').open('xb') as lower:
        source.seek(len(source_header))
        for name,file,count in [('with-upper.bin',full,full_count),('without-upper.bin',lower,lower_count)]:
            header=make_header(names,flags,count,eps);file.write(header);hashes[name].update(header)
        while True:
            original=source.read(RECORD.size*65536)
            if not original:break
            assert len(original)%RECORD.size==0;source_hash.update(original);data=bytearray(original)
            for offset in range(0,len(data),RECORD.size):
                old,owner=struct.unpack_from('<ii',data,offset)
                if 2491<=old<2501:
                    nid=rename.get((old,original[offset+8:offset+RECORD.size]))
                    if nid is not None:
                        assert owner==1
                        struct.pack_into('<i',data,offset,nid);seen[nid]+=1
            full.write(data);hashes['with-upper.bin'].update(data)
            skip=min(len(data)//RECORD.size,max(0,upper_count-processed))
            tail=data[skip*RECORD.size:];lower.write(tail);hashes['without-upper.bin'].update(tail)
            processed+=len(data)//RECORD.size
            if processed%(65536*128)==0:print('RELABELED',processed,full_count,sum(seen.values()),flush=True)
    assert processed==full_count and source_hash.hexdigest()==expected_source_sha
    differences={names[i]:dict(expected=expected[i],observed=seen[i]) for i in expected if seen[i]!=expected[i]}
    (a.out/'label-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('Exact native-box identity incomplete',len(differences),list(differences.items())[:5])
    (a.out/'targets.json').write_text(json.dumps(selected,indent=2)+'\n')
    (a.out/'masters.txt').write_text('\n'.join(str(r['id']) for r in selected)+'\n')
    all_ids=(previous['master_ids'] if previous else [])+[r['id'] for r in selected]
    result=dict(source_scene_sha256=source_hash.hexdigest(),source_metadata_sha256=sha(SCENE/'scene.json'),
        inputs=inputs,selected_electrodes=len(all_ids),newly_selected_electrodes=len(selected),reassigned_boxes=sum(seen.values()),
        exact_box_matches=True,conductor_coordinates_order_and_ownership_unchanged=True,
        with_upper_boxes=full_count,without_upper_boxes=lower_count,
        files={n:dict(sha256=h.hexdigest(),bytes=(a.out/n).stat().st_size) for n,h in hashes.items()},
        targets_sha256=sha(a.out/'targets.json'),electrode_count=len(names),master_ids=all_ids,
        previous_scene=str(a.base_scene) if previous else None,previous_scene_metadata_sha256=sha(a.base_scene/'scene.json') if previous else None,
        scope='Selected native electrodes split from quiet aggregate labels. Unselected electrodes stay quiet; no physical conductor, PG boundary or original source file changed.')
    (a.out/'scene.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['inputs','master_ids']}),flush=True)


if __name__=='__main__':main()
