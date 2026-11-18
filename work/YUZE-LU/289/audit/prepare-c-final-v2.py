from pathlib import Path
p=Path(__file__).parent
s=(p/'c-final-v1.py').read_text().replace('c-final-v1.py','c-final-v2.py')
s=s.replace("for key in ['gate','config','odb','provenance']:","for key in ['gate','config','odb','provenance','fixture_catalog']:")
at="model=p/'model-run';"
insert="""catalog_path=Path(manifest['fixture_catalog'])
catalog=json.loads(catalog_path.read_text());assert catalog['passed']
for source,digest in catalog['all_source_sha256'].items():assert h(source)==digest,source
covered=set(catalog['covered_masters'])
assert covered==set(catalog['master_to_fixture']) and 'OAI221_X4' not in covered
preliminary=set(re.findall(r'^\\s*([A-Z][A-Z0-9]*_X\\d+)\\s+\\S+\\s*\\(',Path(manifest['gate']).read_text(),re.M))
assert preliminary and 'OAI221_X4' not in preliminary
missing=sorted(preliminary-covered)
dump('preflight-master-fixtures.json',dict(passed=not missing,preliminary_master_types=sorted(preliminary),uncovered=missing,catalog_sha256=h(catalog_path),scope='Lexical preflight only; authoritative post-parse actual inventory is independently checked.'))
assert not missing,('Missing original full-deck fixtures BEFORE formal run',missing)
"""
s=s.replace(at,insert+at)
s=s.replace("list(map(Path,manifest['fixture_receipts']))","list(map(Path,catalog['all_source_sha256']))+[catalog_path]")
start=s.index('covered=set()\nfor f in manifest[');end=s.index('missing=sorted(set(actual)-covered)',start)
s=s[:start]+s[end:]
s=s.replace("fixture_receipts={f:h(f) for f in manifest['fixture_receipts']}","fixture_catalog={str(catalog_path):h(catalog_path)},actual_master_to_fixture={n:catalog['master_to_fixture'][n] for n in actual if n in covered}")
(p/'c-final-v2.py').write_text(s)
b=(p/'c-final-v1.sbatch').read_text().replace('c-final-v1.py','c-final-v2.py').replace('yzl-C-final-lec','yzl-C-final-v2')
(p/'c-final-v2.sbatch').write_text(b)
