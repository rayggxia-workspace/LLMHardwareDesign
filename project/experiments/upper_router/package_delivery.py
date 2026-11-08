"""Package qualified six-file output with its exact LEF/Liberty dependencies.

The package must subsequently pass real DEF loading and nominal STA replay.
No input geometry, constraint or electrical model is modified.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import tarfile
from native_inventory import sha
from check import digest


def package(delivery,index,source,out):
    read=lambda p:json.loads(Path(p).read_text())
    q=read(delivery/'qualification.json');manifest=read(delivery/'input-manifest.json')
    assert q['passed'] and q['physical_qualified'] and digest(manifest)==q['manifest_sha256']
    paths={k:Path(v) for k,v in manifest['paths'].items()}
    indexed=read(index)
    assert indexed['qualification']['sha256']==sha(delivery/'qualification.json')
    copies={}
    def add(name,path,expected):
        path=Path(path);assert sha(path)==expected,('changed package input',str(path))
        assert name not in copies;copies[name]={'path':str(path),'sha256':expected}
    for name,row in q['artifacts'].items():add(name,delivery/name,row['sha256'])
    views=read(paths['flat_views']);proof=read(paths['flat_odb'].parent/'source-proof.json')
    technology=proof['technology'];vias=proof['upper_vias']
    add('views/technology.lef',technology['path'],technology['sha256'])
    add('views/upper-vias.lef',vias['path'],vias['sha256'])
    lefs=['views/technology.lef','views/upper-vias.lef'];libs=[];dependencies=[]
    for ti,(template,group) in enumerate(sorted(views.items())):
        for kind,suffix in [('lefs','.lef'),('liberties','.lib')]:
            for i,ref in enumerate(group['views'][kind]):
                name='views/t%03d/%s/%04d%s'%(ti,kind,i,suffix)
                add(name,ref['path'],ref['sha256'])
                (lefs if kind=='lefs' else libs).append(name)
                dependencies.append({'template':template,'kind':kind,'relative_path':name,**ref})
    add('evidence/qualification.json',delivery/'qualification.json',sha(delivery/'qualification.json'))
    add('evidence/input-manifest.json',delivery/'input-manifest.json',sha(delivery/'input-manifest.json'))
    add('evidence/delivery-index.json',index,sha(index))
    out.mkdir()
    files={}
    for name,ref in copies.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ref['path'],target)
        assert sha(target)==ref['sha256'];files[name]={'sha256':ref['sha256'],'bytes':target.stat().st_size,'source':ref['path']}
    prefix=['set handoff_root [file dirname [file normalize [info script]]]']
    def local(name):return '[file join $handoff_root {'+name+'}]'
    loads=prefix+['read_lef '+local(name) for name in lefs]
    counts=['set block [[ord::get_db] getChip]','set block [$block getBlock]',
        'set f [open [file join $handoff_root $count_file] w]',
        'puts $f "instances\t[llength [$block getInsts]]"',
        'puts $f "nets\t[llength [$block getNets]]"',
        'puts $f "ports\t[llength [$block getBTerms]]"','close $f']
    scripts={
        'load_odb.tcl':prefix+['read_odb '+local('design.odb'),'set count_file reference-counts.tsv']+counts,
        'load_def.tcl':loads+['read_def '+local('design.def'),'set count_file physical-counts.tsv']+counts,
        'load_timing.tcl':loads+['read_liberty '+local(name) for name in libs]+[
            'read_verilog '+local('design.v'),'link_design routed_resource_assembly',
            'read_sdc '+local('design.sdc'),'read_spef '+local('design.spef'),
            'set_propagated_clock [all_clocks]',
            'report_worst_slack -max -digits 9 > '+local('timing-summary.rpt'),
            'report_worst_slack -min -digits 9 >> '+local('timing-summary.rpt'),
            'report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 9 >> '+local('timing-summary.rpt'),
            'sta::find_timing','set f [open '+local('timing-counts.tsv')+' w]',
            'puts $f "setup\t[sta::endpoint_violation_count max]"',
            'puts $f "hold\t[sta::endpoint_violation_count min]"',
            'foreach kind {capacitance slew fanout} {puts $f "$kind\t[sta::max_${kind}_violation_count]"}',
            'close $f']}
    for name,lines in scripts.items():
        (out/name).write_text('\n'.join(lines)+'\n');files[name]={'sha256':sha(out/name),'bytes':(out/name).stat().st_size}
    result={'schema_version':'upper-router-portable-package/1',
        'replay_required':True,'replay_receipt':'package-replay.json',
        'qualification_sha256':sha(delivery/'qualification.json'),'coverage':q['coverage'],
        'dependencies':dependencies,'files':files,
        'source_archive':{'path':str(source),'sha256':sha(source)},
        'nominal_reference':next(v for v in q['timing_variants'] if v['variant']=='distributed-coupling-1'),
        'scope':q['qualification'],'not_claimed':q['not_claimed']}
    (out/'package.json').write_text(json.dumps(result,indent=2)+'\n');return result


def verify(out):
    meta=json.loads((out/'package.json').read_text())
    for name,ref in meta['files'].items():assert sha(out/name)==ref['sha256'],('changed packaged artifact',name)
    assert sha(out/'evidence/qualification.json')==meta['qualification_sha256']
    read_counts=lambda p:{k:int(v) for k,v in (s.split() for s in p.read_text().splitlines())}
    physical=read_counts(out/'physical-counts.tsv');reference=read_counts(out/'reference-counts.tsv')
    assert set(physical)=={'instances','nets','ports'} and physical==reference
    for name in ('load-odb.log','load-def.log','load-timing.log'):
        assert not re.search(r'\[ERROR |STA-0366|STA-0450|STA-0471|STA-0432',(out/name).read_text()),name
    violations=read_counts(out/'timing-counts.tsv')
    assert set(violations)=={'setup','hold','capacitance','slew','fanout'} and not any(violations.values())
    slack={k:float(v) for k,v in re.findall(r'worst slack (max|min) (-?[\d.]+)',(out/'timing-summary.rpt').read_text())}
    assert set(slack)=={'max','min'} and min(slack.values())>=0
    assert all(abs(slack[k]-meta['nominal_reference']['slack_ns'][k])<=1e-8 for k in slack)
    result={'passed':True,'qualification_sha256':meta['qualification_sha256'],
        'package_manifest_sha256':sha(out/'package.json'),'physical_counts':physical,
        'nominal_violations':violations,'nominal_slack_ns':slack,
        'scope':'exact qualified six files plus alias LEF/Liberty/technology; real DEF reload and nominal STA replay'}
    (out/'package-replay.json').write_text(json.dumps(result,indent=2)+'\n')
    archive=out.with_suffix('.tar.gz')
    with tarfile.open(archive,'x:gz',compresslevel=1) as stream:
        for path in sorted(out.rglob('*')):
            if path.is_file():stream.add(path,arcname=path.relative_to(out).as_posix(),recursive=False)
    summary={'passed':True,'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,
        'package_replay':{'path':str(out/'package-replay.json'),'sha256':sha(out/'package-replay.json')}}
    with archive.with_suffix(archive.suffix+'.json').open('x') as stream:json.dump(summary,stream,indent=2);stream.write('\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    build=s.add_parser('build')
    for name in ('delivery','index','source','output'):build.add_argument(name,type=Path)
    replay=s.add_parser('verify');replay.add_argument('output',type=Path);a=p.parse_args()
    result=package(a.delivery,a.index,a.source,a.output) if a.command=='build' else verify(a.output)
    print(json.dumps({'command':a.command,'passed':result.get('passed',False),'output':str(a.output)}))
