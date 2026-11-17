from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=root/'audit/f-final-resume.py';s=p.read_text();head=s[:s.index("body='set_thread_count")];tail=s[s.index('independent=dict'):]
checks="records=lambda p:{x.strip() for x in p.read_text().split('violation type:') if x.strip()}\nassert records(q/'native-drc.rpt')==records(c/'native-drc.rpt'),'Native marker set differs'\nassert (q/'cfj_group_f.lib').stat().st_size>0 and (q/'cfj_group_f.lef').stat().st_size>0\n"
(root/'audit/f-final-aggregate.py').write_text(head+checks+tail)
