"""Compare real parent/old leaf/costed leaf metal around the actual MXU M6 marker."""
from pathlib import Path
import csv,datetime,json,os,re,sys
from run_exports import ROOT,sha
from run_escape_fixture import execute

DRIVER=Path(__file__).resolve().parent


def run(revision):
    parent=ROOT/'escape_fixtures/mxu-r01/mxu-C';p=json.loads((parent/'execution.json').read_text())
    assert p.get('completed_utc') and p['native_route_returncode']==0 and p['independent_DRC_count']==2
    errors=(parent/'independent.drc').read_text().split('violation type:')[1:]
    error=next(s for s in errors if 'net:act_data[12]' in s and 'on Layer metal6' in s)
    m=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)',error);assert m
    marker=list(map(float,m.groups()));dx,dy=p['parent_R0_translation_um'];cx=(marker[0]+marker[2])/2;cy=(marker[1]+marker[3])/2
    old=ROOT/'finalized/access-r03/mxu-C';original=json.loads((old/'execution.json').read_text())
    assert original['clean_odb_sha256']==p['source_clean_ODB_SHA'] and original['independent_DRC_count']==0
    current=ROOT/'eco_views/r02/mxu-C';costed=json.loads((current/'execution.json').read_text())
    assert costed['native_export_returncode']==0 and costed['all_original_signal_and_PG_pins_and_size_exactly_preserved']
    out=ROOT/'parent_region_audit'/revision;out.mkdir(parents=True,exist_ok=False)
    common=['singularity','exec','--cleanenv','--bind',str(ROOT/'tmp')+':/tmp','--home',str(ROOT/'home'),'--pwd',str(out)]
    rec={'scope':'BOUNDED_REAL_HIERARCHICAL_M6_OWNERSHIP_AUDIT_NOT_FULL_DRC_OR_PARENT_QUALIFICATION',
      'actual_parent_DRC_marker_um':marker,'original_source_leaf_DRC':0,'parent_native_DRC':2,
      'full_qualification':False,'sources':{},'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'scheduler_job':os.environ['SLURM_JOB_ID']}
    sources=[('parent',parent/'routed.odb',0.,0.),('leaf_before_ECO',old/'clean.odb',dx,dy),('leaf_costed_ECO',current/'clean.odb',dx,dy)]
    expected={'parent':p['files']['routed.odb']['sha256'],'leaf_before_ECO':original['clean_odb_sha256'],'leaf_costed_ECO':costed['source_geometry_sha256']}
    for label,odb,tx,ty in sources:
        before=sha(odb);assert before==expected[label],(label,'Actual physical source changed')
        region=[cx-tx-1.5,cy-ty-1.5,cx-tx+1.5,cy-ty+1.5]
        target=out/(label+'.tsv');env='PINXY_AUDIT_ODB={},PINXY_AUDIT_BOX={},PINXY_AUDIT_PIN=act_data[12],PINXY_AUDIT_OUT={}'.format(odb,' '.join(str(round(v*2000)) for v in region),target)
        rc=execute(common,DRIVER/'audit_parent_region.tcl',out/(label+'.log'),env,threads=1)
        data=[]
        if target.exists():
            with target.open() as f:data=list(csv.DictReader(f,delimiter='\t'))
        rec['sources'][label]={'ODB':str(odb),'ODB_SHA':before,'source_unchanged':sha(odb)==before,
          'native_returncode':rc,'local_window_um':region,'to_parent_translation_um':[tx,ty],
          'exported_shape_rows':len(data),'M6_rows':sum(q['layer']=='metal6' for q in data),
          'unchecked_macro_transform_rows':sum(q['kind']=='UNCHECKED_MACRO_TRANSFORM' for q in data),
          'full_rule_and_route_check':'NOT_EXECUTED_BY_THIS_LOCAL_READ_ONLY_AUDIT'}
    rec['all_sources_unchanged']=all(q['source_unchanged'] for q in rec['sources'].values())
    rec['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    rec['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file()}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')
    return 0 if rec['all_sources_unchanged'] and all(q['native_returncode']==0 for q in rec['sources'].values()) else 1


if __name__=='__main__':sys.exit(run(sys.argv[1]))
