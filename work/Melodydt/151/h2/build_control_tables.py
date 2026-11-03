"""Emit simulation views of permanent H1 control contents; not a boot loader."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();out=a.output.resolve();assert not out.exists();out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('h1_frozen',root/'scripts/check_h1_graphs.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    data=root/'project/experiments/hybrid_control/h1/v0_1';target=json.loads((data/'target.json').read_text())
    index=dict(scope='numeric memory simulation view of permanent table interface; no manufactured ROM or boot program loader',files=[],graphs=[])
    for name in ['g1_serial_af','g2_reentry_afaf','g3_fork_select']:
        graph=json.loads((data/'graphs'/f'{name}.json').read_text());program=h.compile_graph(graph,target);raw=h.encode(program);h.verify_decode(program,raw)
        meta,image=h.metadata(graph,program);short=name[:2]
        words=[int.from_bytes(raw[i:i+16],'little') for i in range(0,len(raw),16)]
        rom='\n'.join(f'{x:032x}' for x in words+[0]*(256-len(words)))+'\n'
        start=64+len(raw);objects=image[start:start+64*len(program['objects'])]
        obj=[int.from_bytes(objects[i:i+64],'little') for i in range(0,len(objects),64)]
        for suffix,text in [('rom',rom),('meta','\n'.join(f'{x:0128x}' for x in obj+[0]*(17-len(obj)))+'\n')]:
            dst=out/f'{short}_{suffix}.hex';dst.write_bytes(text.encode('ascii'));index['files'].append(dict(path=dst.name,bytes=dst.stat().st_size,sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
        index['graphs'].append(dict(name=name,records=len(words),objects=program['objects'],image_sha256=meta['product_image_sha256'],RTL_scope='G1 first; G2/G3 remain separate acceptance gates'))
    (out/'table-index.json').write_bytes((json.dumps(index,indent=2)+'\n').encode('utf8'))
    print(json.dumps(dict(status='PASS_TABLE_VIEW_GENERATION',files=len(index['files']),output=str(out))))
if __name__=='__main__':main()
