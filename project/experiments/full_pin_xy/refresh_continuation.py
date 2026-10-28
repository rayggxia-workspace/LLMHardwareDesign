"""Refresh only the additive continuation section and its artifact hashes.

Original ABC plots/data and previous physical publication namespaces remain.
Use build_deliverables.py for a full report rebuild.
"""
from pathlib import Path
import argparse,hashlib,json
from continuation_report import render


def refresh(root,out):
    out=Path(out);p=out/'report.html';text=p.read_text(encoding='utf-8')
    start=text.index('<section class="card" id="continuation">');end=text.index('<section class="card" id="coverage">',start)
    text=text[:start]+render(Path(root),out)+text[end:]
    text=text.replace('两者实际路由继续，尚无独立终态DRC/连通/系统时序通过证据。','两者均已终态失败：openTPU r07独立native11项，llaccel ll-r01在GRT拥塞失败；后续RC/STA物理门槛阻止执行。')
    p.write_text(text,encoding='utf-8',newline='\n')
    index={q.relative_to(out).as_posix():{'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in sorted(out.rglob('*')) if q.is_file() and q.name!='artifact_index.json'}
    (out/'data/artifact_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('CONTINUATION_REFRESHED',len(index),'file hashes; original ABC retained; no physical qualification inferred')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args();refresh(a.root,a.out)
