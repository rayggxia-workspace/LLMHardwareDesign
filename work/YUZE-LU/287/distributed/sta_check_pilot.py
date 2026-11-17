import pathlib,csv,json
p=pathlib.Path(__file__).resolve().parent
def read(case):
 rows=list(csv.DictReader((p/'sta'/case/'crossing.tsv').open(),delimiter='\t'));assert len(rows)==256,(case,len(rows))
 assert all(r['startpoint'].startswith('C/') and r['endpoint'].startswith('U/') for r in rows),case
 return {mode:min(float(r['slack']) for r in rows if r['mode']==mode) for mode in ['max','min']}
before=read('control-zero-before-200');after=read('control-zero-after-200');old=read('control-p50-200')
assert all(abs(before[m]-after[m])<1e-8 for m in before),(before,after)
assert abs(before['max']-2.079750)<1e-5,before
assert abs(old['max']-1.573235)<1e-5,old
out={'passed':True,'zero_before':before,'zero_after':after,'old_p50':old,'new_200':read('A-n14653-200'),'new_300':read('A-n14653-300')}
(p/'sta-pilot-validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
