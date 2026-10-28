"""Exact per-net rectangle-multiset comparison of three actual routed versions.

Equal representations prove equal exported routing boxes. Unequal ones may
reflect segmentation/duplication, not a change in geometric union or RC.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import csv,datetime,gzip,hashlib,itertools,json,os,sys,traceback
from run_exports import ROOT,sha

DRIVER=Path(__file__).resolve().parent


def read_geometry(directory):
    receipt=directory/'execution.json';r=json.loads(receipt.read_text());p=directory/'whole_access.tsv.gz'
    assert r.get('completed_utc') and sha(p)==r['files'][p.name]['sha256']
    hashes={};total=0
    with gzip.open(str(p),'rt') as f:
        for name,group in itertools.groupby(csv.DictReader(f,delimiter='\t'),key=lambda q:q['net']):
            assert name not in hashes
            boxes=[]
            for q in group:
                if q['kind'] not in ['WIRE','VIA']:continue
                boxes.append((q['kind'],q['layer'])+tuple(int(q[k]) for k in ['x0','y0','x1','y1']))
            digest=hashlib.sha256(json.dumps(sorted(boxes),separators=(',',':')).encode()).hexdigest()
            hashes[name]=(digest,len(boxes));total+=len(boxes)
    assert len(hashes)==268637
    return hashes,{'receipt':str(receipt),'receipt_SHA256':sha(receipt),'actual_geometry':str(p),
      'actual_geometry_SHA256':sha(p),'routing_box_rows_with_duplicates':total,'actual_multiterminal_nets':len(hashes)}


def run(revision):
    assert int(os.environ['SLURM_CPUS_PER_TASK'])>=3
    out=ROOT/'route_representation_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    source=[ROOT/'antenna_diode_eco/r01/gemm-C',ROOT/'diode_cap_eco/r01/gemm-C',ROOT/'antenna_incremental_eco/r01/gemm-C']
    record={'scope':'EXACT_ROUTING_RECTANGLE_MULTISET_COMPARISON_NOT_UNION_LENGTH_RC_OR_QUALIFICATION',
      'full_qualification':False,'link_serials_and_terminal_geometry_excluded':True,'wire_and_expanded_via_boxes_included':True,
      'duplicate_rectangles_retained':True,'scheduler_job':os.environ['SLURM_JOB_ID'],
      'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip()}
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:items=list(pool.map(read_geometry,source))
        original=json.loads((ROOT/'antenna_netmap/r02/unique_correlated_native_nets.json').read_text());assert len(set(original))==636
        missing=json.loads((ROOT/'post_diode_netmap/cap-r01/correlation_summary.json').read_text())['mapped_nets_without_existing_real_diode'];assert len(set(missing))==22
        assert not set(original)&set(missing)
        record['source_versions']=[meta for _,meta in items];record['comparisons']=[]
        for a,b,label in [(0,1,'636diode_to_two_sizes'),(1,2,'two_sizes_to_22_more_diodes')]:
            x,y=items[a][0],items[b][0];assert set(x)==set(y)
            counts=Counter();groups=Counter()
            with gzip.open(str(out/(label+'.tsv.gz')),'wt',newline='') as f:
                w=csv.writer(f,delimiter='\t');w.writerow(['native_net','same_routing_box_multiset','before_sha256','after_sha256','before_rows','after_rows','group'])
                for net in sorted(x):
                    same=x[net]==y[net];kind='previous_636_diode_net' if net in original else 'new_22_diode_net' if net in missing else 'other_original_net'
                    counts['identical' if same else 'different_representation']+=1
                    groups[kind+':'+('identical' if same else 'different_representation')]+=1
                    w.writerow([net,same,x[net][0],y[net][0],x[net][1],y[net][1],kind])
            record['comparisons'].append({'comparison':label,'actual_nets':len(x),'counts':dict(counts),'by_target_group':dict(groups),
              'not_a_claim_only_target_nets_rerouted':True})
        record['all_closed_source_geometry_and_receipts_unchanged']=all(sha(Path(q['receipt']))==q['receipt_SHA256'] and sha(Path(q['actual_geometry']))==q['actual_geometry_SHA256'] for q in record['source_versions'])
    except Exception:record['actual_failure']=traceback.format_exc()
    record['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if 'actual_failure' not in record and record.get('all_closed_source_geometry_and_receipts_unchanged') else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
