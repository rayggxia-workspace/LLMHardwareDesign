import pathlib,json,csv
p=pathlib.Path(__file__).resolve().parent;results=[]
for key in ['control-zero-before-200','control-p50-200','A-n14653-200','A-n14653-300']:
 old=list(csv.DictReader((p/'sta'/key/'crossing.tsv').open(),delimiter='\t'));new=list(csv.DictReader((p/'fast-pilot'/key/'crossing.tsv').open(),delimiter='\t'))
 assert len(old)==256 and len(new)==2
 for mode in ['max','min']:
  a=min(float(r['slack']) for r in old if r['mode']==mode);b=next(float(r['slack']) for r in new if r['mode']==mode)
  assert abs(a-b)<1e-8,(key,mode,a,b)
  results.append(dict(case=key,mode=mode,per_bit_min_ns=a,union_query_ns=b))
(p/'fast-pilot-validation.json').write_text(json.dumps({'passed':True,'comparisons':results},indent=2));print('Fast union query matches all eight per-bit extrema')
