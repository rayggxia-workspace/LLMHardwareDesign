"""Failure-only native ground-cap plus optimistic upper-wire lower bound."""
import hashlib,json,math,re
from pathlib import Path


def inspect(config_path,manifest_path,graph_path,out,inputs,sha):
    def read(path):
        path=Path(path);inputs[str(path)]=sha(path);return json.loads(path.read_text())
    config=read(config_path)
    assert set(config)=={'native_sta','placements'} and config['placements']
    folder=Path(config['native_sta']);receipt=read(folder/'receipt.json')
    assert receipt['execution_passed'] and receipt['typed_native_timing_passed']
    for path in [manifest_path,graph_path]:
        assert receipt['inputs'][str(path)]==sha(path);inputs[str(path)]=sha(path)
    audit=read(folder/'native-system-audit.json');assert audit['passed']
    proof=read(folder/'native-stitch.json')
    assert proof['passed'] and proof['mode']=='native-access-plus-ideal-upper-diagnostic'
    manifests=read(manifest_path)
    assert proof['inputs']=={r['final_files']['6_final.spef']['path']:r['final_files']['6_final.spef']['sha256']for r in manifests['leaves'].values()}
    reports=[];wanted=set()
    for placement in config['placements']:
        placement=Path(placement);r=read(placement/'receipt.json');assert r['passed']
        p=placement/'wire-cap-lower-bound.json';assert r['outputs'][p.name]==sha(p)
        d=read(p);assert d['executed']and d['research_model'];reports.append((str(placement),d))
        wanted.update(row['net']for row in d['rows'])
    spef=Path(proof['output']);assert receipt['inputs'][str(spef)]==proof['output_sha256']
    names={};ground={};counts={};phase=None;current=None;unit=False;header=True;digest=hashlib.sha256()
    with spef.open('rb')as stream:
        for raw in stream:
            digest.update(raw)
            if header:
                if raw.startswith(b'*C_UNIT '):assert raw.split()==[b'*C_UNIT',b'1',b'PF'];unit=True
                match=re.fullmatch(rb'(\*\d+) (net_\d+)\r?\n',raw)
                if match and match[2].decode()in wanted:names[match[1]]=match[2].decode()
                if not raw.startswith(b'*D_NET '):continue
                header=False;assert unit
            if raw.startswith(b'*D_NET '):
                current=names.get(raw.split()[1]);phase=None
                if current is not None:assert current not in ground;ground[current]=0.;counts[current]=0
            elif current is not None:
                line=raw.strip()
                if line in (b'*CONN',b'*CAP',b'*RES'):phase=line
                elif line==b'*END':current=None
                elif phase==b'*CAP'and line:
                    fields=line.split();assert len(fields)in (3,4)
                    value=float(fields[-1]);assert math.isfinite(value)and value>=0
                    if len(fields)==3:ground[current]+=1000*value;counts[current]+=1
    assert digest.hexdigest()==proof['output_sha256'];inputs[str(spef)]=digest.hexdigest()
    assert set(ground)==wanted,'Missing exact native boundary capacitance'
    summaries=[]
    for placement,d in reports:
        rows=[]
        for r in d['rows']:
            net=r['net'];limit=r['physical_driver']['max_capacitance_ff'];native=ground[net]
            totals={v:native+c for v,c in r['wire_capacitance_lower_bound_ff'].items()}
            rows.append(dict(net=net,driver=r['driver'],max_capacitance_ff=limit,native_ground_cap_ff=native,
                native_ground_entries=counts[net],optimistic_total_ff=totals,
                violates={v:c>limit+1e-9 for v,c in totals.items()}))
        summaries.append(dict(placement=placement,violations={v:sum(r['violates'][v]for r in rows)for v in ['low','base','high']},rows=rows))
    result=dict(passed=True,diagnostic_executed=True,whole_system_qualified=False,placements=summaries,
        scope='Failure-only exact joined native ground CAP entries plus source-bound optimistic upper HPWL capacitance. Coupling, all pin loads, upper detours and vias omitted conservatively. Zero violations never grants physical or timing qualification.')
    (out/'native-cap-residual.json').write_text(json.dumps(result,indent=2)+'\n');return result
