"""Render the incremental engineering receipt without regenerating candidates."""
from pathlib import Path
import gzip,hashlib,html,io,json,os,re
from markdown_it import MarkdownIt


def run(repo):
    repo=Path(repo);source=repo/'docs/experiments/issue-126-resume-20261030.md';out=source.with_suffix('');evidence=out/'ll-corner-fill'
    q=json.loads((evidence/'execution.json').read_text());packed={}
    names=['actual_fill_edit.log','fresh_DRC.log','all_geometry_and_AP.log','RC_STA.log','checks.txt','parasitic_coverage.txt']
    names +=['actual_fill_edit.stages.tsv','fresh_DRC.stages.tsv','all_geometry_and_AP.stages.tsv','RC_STA.stages.tsv']
    for name in names:
        p=evidence/name;raw=p.read_bytes() if p.exists() else gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
        assert hashlib.sha256(raw).hexdigest()==q['files'][p.name]['sha256']
        data=io.BytesIO()
        with gzip.GzipFile(filename='',mode='wb',fileobj=data,mtime=0) as f:f.write(raw)
        dest=p.with_name(p.name+'.gz');dest.write_bytes(data.getvalue())
        packed[dest.name]={'SHA256':hashlib.sha256(dest.read_bytes()).hexdigest(),'uncompressed_native_SHA256':q['files'][p.name]['sha256']}
    (out/'evidence_packaging.json').write_text(json.dumps({'scope':'Lossless native evidence compression; exact source SHA in execution.json','files':packed},indent=2)+'\n',encoding='utf-8')
    # These derivatives can be rebuilt from the published compressed receipts.
    from summarize_native_path_types import summarize
    (out/'LL_actual_path_types.json').write_text(json.dumps(summarize(out/'stages/LL-paths'),indent=2)+'\n',encoding='utf-8')
    text=gzip.decompress((evidence/'checks.txt.gz').read_bytes()).decode();rows={'max slew':[],'max capacitance':[]};section=None
    units=json.loads((out/'actual_library_units.json').read_text());assert '(1,ff)' in re.sub(r'\s+','',units['capacitive_load_unit'])
    for line in text.splitlines():
        if line.strip() in rows:section=line.strip()
        if section and '(VIOLATED)' in line:
            p=line.split();assert len(p)==5
            rows[section].append(dict(driver=p[0],limit=float(p[1]),actual=float(p[2]),slack=float(p[3]),native_line=line))
    checks={'scope':'ACTUAL_NATIVE_FULL_CHECK_TABLE_ROWS_NOT_FUNCTIONAL_SIMULATION','source_ODB_SHA256':q['files']['routed.odb']['sha256'],
            'source_report_SHA256':q['files']['checks.txt']['sha256'],'units':{'max slew':'ns','max capacitance':'fF; actual Nangate Liberty capacitive_load_unit(1,ff)'},
            'counts':{k:len(v) for k,v in rows.items()},'worst_absolute_slack_examples':{k:sorted(v,key=lambda x:x['slack'])[:3] for k,v in rows.items()},
            'full_list':'ll-corner-fill/checks.txt.gz','qualified':False}
    (out/'LL_actual_electrical.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    body=MarkdownIt('commonmark',{'html':False}).enable('table').render(source.read_text(encoding='utf-8'))
    def link(m):
        attr,url=m.groups()
        if re.match(r'\w+:|#',url):return m[0]
        dest=(source.parent/url).resolve();assert dest.is_relative_to(repo.resolve())
        assert dest.exists(),str(dest)
        return attr+'="'+Path(os.path.relpath(dest,out)).as_posix()+'"'
    body=re.sub(r'(href|src)="([^"]+)"',link,body)
    style='body{font-family:"Microsoft YaHei",sans-serif;color:#17283c;background:#eef2f6;margin:0;line-height:1.85}main{max-width:1180px;margin:24px auto;padding:30px;background:white;border-radius:12px}h1,h2{color:#17283c;line-height:1.4}h2{margin-top:34px;border-top:1px solid #dce3eb;padding-top:22px}a{color:#0072b2}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border:1px solid #dce3eb;text-align:left}th{background:#eff5fa}code{font-size:.9em;overflow-wrap:anywhere}p,li,td{overflow-wrap:anywhere}strong{color:#25456a}@media(max-width:700px){main{padding:16px;margin:8px}table{font-size:12px}td,th{padding:5px}}'
    (out/'report.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>实际工程接续：接入修复与未完成项</title><style>'+style+'</style><main>'+body+'</main></html>\n',encoding='utf-8')
    print(json.dumps({'report':str(out/'report.html'),'native_DRC':q['fresh_DRC_count'],'setup_ns':q['setup_ns'],'min_ns':q['hold_ns'],'packed_native_files':len(packed),'candidate_analysis_recomputed':False}))
if __name__=='__main__':run(Path(__file__).resolve().parents[3])
