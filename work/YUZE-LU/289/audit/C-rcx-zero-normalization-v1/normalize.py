from pathlib import Path
import pya,re,json,hashlib,collections,os
p=Path.cwd();base=Path(os.environ['C_ZERO_BASE']);report=base/'material/receipt.json';receipt=json.loads(report.read_text());assert not receipt['passed']
def sha(q):return hashlib.sha256(q.read_bytes()).hexdigest()
for n in ('before.def','after.def','layers.tsv','vias.tsv'):assert sha(base/n)==receipt['source_sha256'][str(base/n)]
width={n:int(w) for n,w in (x.split('\t') for x in (base/'layers.tsv').read_text().splitlines())};vias={};vlayers={}
for s in (base/'vias.tsv').read_text().splitlines():
 n,l,*b=s.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
 if l.startswith('metal'):vlayers.setdefault(n,set()).add(l)
source=(p/'parser-source.py').read_text();fragment=source[source.index('fmt=lambda'):source.index('rows=[];canonical={}')] ;exec(compile(fragment,'frozen_material_parser','exec'))
text=(base/'before.def').read_text();match=re.search(r'\nNETS\s+\d+\s*;(.*?)\nEND NETS',text,re.S);assert match;section=match[1];pat=re.compile(r'^\s*-\s+(\S+)\s+(.*?);\s*$',re.M|re.S);entries={m[1]:m for m in pat.finditer(section)};targets=sorted({d['net'] for d in receipt['geometry_differences']});changes=[];replacements={}
zero=re.compile(r'\(\s*(?:\*|-?\d+)\s+(?:\*|-?\d+)\s+(0)\s*\)')
for net in targets:
 assert net in entries;body=entries[net][2];original,_=parse(body)
 for m in reversed(list(zero.finditer(body))):
  trial=body[:m.start(1)]+body[m.end(1):];a,_=parse(trial)
  if a.keys()==original.keys() and all((a[l]^original[l]).is_empty() for l in a):
   changes.append(dict(net=net,original_point=m[0],body_offset=m.start(1),reason='Zero extension is union-redundant: removing it changes no actual per-layer metal/via material.'));body=trial
 a,_=parse(body);assert a.keys()==original.keys() and all((a[l]^original[l]).is_empty() for l in a);replacements[net]=body
assert changes,'No proven redundant endpoint-zero edit found; explicit alternative needed'
# Keep all unrelated body text and non-NETS sections byte-for-byte.
newsection=section
for net in sorted(replacements,key=lambda n:entries[n].start(2),reverse=True):
 m=entries[net];newsection=newsection[:m.start(2)]+replacements[net]+newsection[m.end(2):]
newtext=text[:match.start(1)]+newsection+text[match.end(1):];(p/'normalized.def').write_text(newtext)
after={m[1]:m[2] for m in pat.finditer(newsection)};assert set(after)==set(entries)
for n in entries:
 if n not in targets:assert entries[n][2]==after[n]
 else:
  a,_=parse(entries[n][2]);b,_=parse(after[n]);assert a.keys()==b.keys() and all((a[l]^b[l]).is_empty() for l in a)
v=dict(passed=True,accepted=False,scope='Input DEF normalization only, exact net connectivity and material conserved; needs new extraction and all-net before/after fixed-point check before binding SPEF.',target_nets=targets,zero_extension_edits=changes,all_other_net_bodies_exact=True,all_non_NETS_text_exact=True,net_count=len(entries),source_sha256={str(q):sha(q) for q in [base/'before.def',base/'after.def',base/'layers.tsv',base/'vias.tsv',report,p/'parser-source.py',Path(__file__),p/'normalized.def']});(p/'edit-receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
