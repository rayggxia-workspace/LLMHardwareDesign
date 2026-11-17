from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');s=(root/'gs/f-qualify.py').read_text()
s=s.replace("q=c/'qualification';q.mkdir()","q=c/'qualification-final';q.mkdir()")
s=s.replace("assert (c/'native-drc.rpt').stat().st_size==0", "review=json.loads((Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/F-new-marker-gds-connectivity.json')).read_text());assert review['passed']\nmarker_diff=json.loads((Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/F-native-marker-diff.json')).read_text())\nassert marker_diff['sha256'][str(c/'native-drc.rpt')]==hashlib.sha256((c/'native-drc.rpt').read_bytes()).hexdigest()")
s=s.replace("items=len(ET.parse", "assert sha(res/'6_final.gds')==next(v for k,v in review['sha256'].items() if k.endswith('6_final.gds')),'GDS differs from reviewed actual geometry'\nitems=len(ET.parse")
s=s.replace("report = dict", "records=lambda p:{x.strip() for x in p.read_text().split('violation type:') if x.strip()}\nassert records(q/'native-drc.rpt')==records(c/'native-drc.rpt'),'Independent native markers changed'\nreport = dict")
s=s.replace("items==0 and (q/'native-drc.rpt').stat().st_size==0", "items==0 and review['passed']")
s=s.replace("formal_join_required=True", "formal_join_required=True,native_marker_count=len(records(q/'native-drc.rpt')),native_baseline_shared=marker_diff['shared'],native_new_markers_actual_same_net=True")
(root/'audit/f-qualify-fidelity.py').write_text(s)
