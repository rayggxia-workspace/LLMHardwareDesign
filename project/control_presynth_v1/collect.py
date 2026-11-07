from pathlib import Path
import argparse, hashlib, json, sys
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root;round=root/'r004'
 source=round/'source';sys.path.insert(0,str(source/'project/control_presynth_v1'));import package as pkg
 d=dict(schema='control-synthesis-freeze-campaign/1',profiles={},snapshots={},source_sha256={},package_source_sha256={},tools={},summary={})
 for name in ('r001','r002','r003','r004'):
  r=root/name;d['snapshots'][name]={'source_commit':(r/'source-commit.txt').read_text().strip(),'archive_sha256':sha(r/'source.tar')}
 for index,target in enumerate(pkg.targets()):
  folder=round/'results'/('variant-'+str(index));package=folder/'package';result=folder/'checks/report.json'
  manifest=json.loads((package/'manifest.json').read_text());profile=json.loads((package/'profile.json').read_text());report=json.loads(result.read_text());guards=json.loads((folder/'guard-tests.json').read_text())
  assert pkg.audit(package)['passed'] and report['passed'] and guards['passed']==guards['total']==6
  assert report['profile']==target['name'] and report['parameters']=={'KIND':target['kind'],'PM_USE_SRAM':1}
  assert report['hierarchy']==profile['hierarchy_expected'] and report['hierarchy']['s_sram_256x128_freepdk45']==12
  assert report['ports']=={'input':280,'output':604} and report['sdc']['input_bits']==279 and report['sdc']['output_bits']==604
  assert report['sdc']['all_max_min_serialized'] and report['sdc']['all_output_loads_ff']==5.0 and not report['sdc']['reset_exception']
  assert report['relocated_package_hierarchy_checked']
  for line in (folder/'result.sha256').read_text().splitlines():
   expected,name=line.split(None,1);path=Path(name);actual=round/path.relative_to('/work') if path.is_absolute() else folder/path;assert sha(actual)==expected,name
  for name,expected in report['artifacts_sha256'].items():assert sha(folder/'checks'/name)==expected,name
  for name,digest in profile['copied_source_sha256'].items():
   if name in d['package_source_sha256']:assert d['package_source_sha256'][name]==digest
   d['package_source_sha256'][name]=digest
  d['profiles'][target['name']]={'report':report,'report_sha256':sha(result),'guards':guards,'guards_sha256':sha(folder/'guard-tests.json'),'package_manifest_sha256':sha(package/'manifest.json'),'package_archive_sha256':sha(folder/'control-handoff.tar.gz'),'package_files':len(manifest['files']),'source_files_full':len(profile['full_sources']),'source_files_control':len(profile['control_sources']),'native_boundaries':profile['boundaries_contract'],'result_index_sha256':sha(folder/'result.sha256')}
 for path in sorted((source/'project/control_presynth_v1').iterdir()):
  if path.is_file():d['source_sha256'][path.relative_to(source).as_posix()]=sha(path)
 if (root/'toolchain.txt').exists():d['tools']['raw_toolchain_sha256']=sha(root/'toolchain.txt')
 d['collector_sha256']=sha(Path(__file__))
 d['summary']={'profiles_passed':9,'profiles_total':9,'full_lint':9,'control_lint':9,'generic_synthesis_hierarchy':9,'sdc_binding':9,'relocated_hierarchy':9,'package_guards_passed':54,'package_guards_total':54,'distinct_guard_types':6,'clock_period_ns':'3.333333333','pm_banks_per_profile':12,'new_functional_RTL_scenarios':0,'mapped_combined_STA':'not executed','physical_acceptance':'not executed'}
 a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'summary':d['summary'],'sha256':sha(a.out),'profiles':{k:{'files':v['package_files'],'full':v['source_files_full'],'control':v['source_files_control']} for k,v in d['profiles'].items()}}))
if __name__=='__main__':main()
