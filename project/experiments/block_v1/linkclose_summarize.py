"""Produce reviewable closure tables from receipt-bound collected evidence."""
import argparse,hashlib,json,re
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def summarize(folder):
    evidence=folder/'evidence';rows=[];records={};physical={};peaks={}
    for index in sorted(evidence.glob('closure-run*/index.json')):
        manifest=json.loads(index.read_text())
        for name,r in manifest['files'].items():
            p=index.parent/name;assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
        queue=index.parent/'node-queue-state.json'
        if queue.exists():
            current=set();peak=0
            for e in json.loads(queue.read_text()).get('events',[]):
                if e['event']=='claim':current.add(e['id'])
                elif e['event']=='finish':current.discard(e['id'])
                peak=max(peak,len(current))
            assert peak<=6
            peaks[index.parent.name]=peak
    for rid in (922,923,924):
        for p in sorted((evidence/('closure-run%d'%rid)/'tasks').glob('linkclose-case-*/linkclose-result-summary.json')):
            d=json.loads(p.read_text());assert d['passed']and d['experiment_completed']and d['native_preservation']['passed']
            assert d['zero_fanout_unannotated_driver_summary']['connected_count']==0
            family='representative'if d['pair']in ('mtr','tsr')else 'native_T_fanout'if d['pair'].startswith('f')else 'fixed_repeater'
            row=dict(run=rid,task=p.parent.name,pair=d['pair'],variant=d['variant'],family=family,
                declared_model_passed=d['declared_model_passed'],counts=d['counts'],
                min_link_setup_ns=d['min_link_setup_ns'],min_link_hold_ns=d['min_link_hold_ns'],
                links_spef_sha256=d.get('links_spef_sha256'),summary_member=str(p.relative_to(evidence)).replace('\\','/'),
                native_record_counts=d['native_preservation']['records']['counts'])
            rows.append(row);records[d['pair'],d['variant']]=(p,d)
    assert len(rows)==41 and sum(r['declared_model_passed']for r in rows)==17
    for rid,kind in ((921,'bridge'),(921,'bank'),(916,'booster')):
        p=evidence/('closure-run%d'%rid)/'tasks'/('linkclose-accept-'+kind)/'linkclose-accept.json'
        d=json.loads(p.read_text());assert d['passed']and d['physical']['passed']and d['drc']['passed']and d['strict_final_lec']['passed']
        timed=d['physical']['timing']['timed_endpoints']
        physical[kind]=dict(accepted_run=rid,source=d['source'],source_receipt_sha256=d['source_receipt_sha256'],
            accepted_report_sha256=sha(p),die_um=d['physical']['die_um'],active_area_um2=d['physical']['active_area_um2'],
            physical_only_area_um2=d['physical']['physical_only_area_um2'],fixed_buf16=d['fixed_driver_count'],
            minimum_setup_ns=timed['minimum_setup_ns'],minimum_hold_ns=timed['minimum_hold_ns'],
            full_deck_items=d['drc']['full_deck']['total_items'],strict_lec=d['strict_final_lec']['counts'],
            physical_protocol_runs=d['physical_bridge_protocol_runs'])
    budgets=[]
    for pair in ('mtr','tsr'):
        measured={}
        for variant in ('opposite','guarded','length2','length4'):
            p,d=records[pair,variant]
            # A capacitance violator report contains actual native load and
            # the unmodified Liberty limit. Subtract only our added wire C.
            text=(p.parent/'electrical.rpt').read_text().split('max capacitance',1)[1].split('max fanout',1)[0]
            values={}
            for line in text.splitlines():
                m=re.match(r'^(u_\S+)\s+([\d.]+)\s+([\d.]+)\s+([-\d.]+)\s+\(VIOLATED\)',line)
                if m and float(m[2])>1:
                    pin,limit,cap,slack=m[1],*map(float,m.groups()[1:])
                    assert abs(limit-cap-slack)<.002
                    values[pin]=(limit,cap)
            for o in d['observations']:
                if o['source_driver']not in values:continue
                limit,cap=values[o['source_driver']];fixed=cap-o['new_wire_cap_ff']
                assert fixed>=-.002
                current=measured.setdefault(o['id'],dict(fixed=[],limit=limit))
                assert abs(current['limit']-limit)<.002
                current['fixed'].append(fixed)
        p,d=records[pair,'guarded'];c=d['model']['opposite_ff_per_um']*d['model']['guard']
        for o in d['observations']:
            if o['id']not in measured:continue
            m=measured[o['id']];assert max(m['fixed'])-min(m['fixed'])<.02,'Nonlinear/native cap mismatch'
            fixed=sum(m['fixed'])/len(m['fixed']);via=o['new_wire_cap_ff']-o['wire_length_um']*c
            maximum=(m['limit']-fixed-via)/c
            budgets.append(dict(pair=pair,link=o['id'],source=o['source'],sink=o['sink'],source_driver=o['source_driver'],
                liberty_cap_limit_ff=m['limit'],native_and_receiver_load_ff=fixed,available_new_wire_and_via_ff=m['limit']-fixed,
                inferred_wire_limit_um=maximum,actual_wire_um=o['wire_length_um'],via_allowance_ff=via,
                guarded_ff_per_um=c,measured_conditions=len(m['fixed']),
                scope='Capacitance limit only under the declared coupon model and exact native receiver. Not a setup/slew/hold/routability certificate or Euclidean distance bound.'))
    result=dict(experiment_completed=True,production_combination_accepted=False,full_bus_routing_accepted=False,
        manufacturing_calibrated=False,scope='Finite representative link and real branch/repeater experiment; no full array, system controller, full-width bus or manufacturing signoff.',
        new_electrical_measurements=len(rows),new_declared_model_passes=sum(r['declared_model_passed']for r in rows),
        physical_candidates=physical,rows=rows,capacitance_budgets=budgets,
        model=records['mtr','guarded'][1]['model'],queue_peak_independent_tasks=peaks)
    (folder/'closure-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(measurements=len(rows),passes=result['new_declared_model_passes'],cap_budgets=len(budgets),max_independent_tasks=max(peaks.values()))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('folder',type=Path);a=p.parse_args();summarize(a.folder)
