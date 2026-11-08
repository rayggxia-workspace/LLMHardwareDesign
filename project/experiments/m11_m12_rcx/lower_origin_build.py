"""Fix source-origin attribution at nearest-neighbor ties, not field physics."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from native_scene import write

BASE=Path('/public/home/yuzelu/PingyangHuang')
OLD=BASE/'issue-222-merge-fix-OLZaDNeN/job-100237/build'
SOURCE=Path('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reuse-build',type=Path);args=parser.parse_args()
    out=Path(os.environ['LOWER_OUT']);out.mkdir();include=out/'include/fsv';include.mkdir(parents=True)
    src=Path(__file__).resolve().parent;proof=json.loads((OLD/'build.json').read_text());assert proof['bidirectional_interval_merge']
    assert sha(OLD/'Solver.cpp')==proof['patched_solver_sha256']
    source=(OLD/'Solver.cpp').read_text()
    def edit(old,new):
        nonlocal source
        assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
    edit('const std::vector<int>& origin_groups)', 'const std::vector<int>& origin_groups, const int source_master)')
    edit('origin_groups_(origin_groups)\n','origin_groups_(origin_groups), source_master_(source_master)\n')
    edit('''    if (!captures.empty()) {''','''    if(!origin_groups_.empty()) origin_partitions_=*std::max_element(origin_groups_.begin(),origin_groups_.end())+1;
    if (!captures.empty()) {''')
    begin=source.index('    if (!origin_groups_.empty()) {\n      if (origin.box < 0)')
    end=source.index('    const double first_size = origin.dist;',begin)
    source=source[:begin]+'''    if (!origin_groups_.empty()) {
      // A Gaussian face capped at half a gap can be equidistant from the
      // source and a different quiet net. The nearest quiet net is not a
      // source-origin label. Search only boxes belonging to the source.
      double radius=origin.dist+1e-9;
      double best=std::numeric_limits<double>::infinity();
      int source_box=-1;
      for(int attempt=0;attempt<8 && source_box<0;++attempt) {
        AlignedBox<D> query;
        for(int k=0;k<D;++k){query.lo[k]=p[k]-radius;query.hi[k]=p[k]+radius;}
        index_.forEachOverlapping(query,[&](int i) {
          if(Frame::shapeNet(geometry_,i)!=source_master_)return;
          double d=linfDistance<D>(p,Frame::shapes(geometry_)[i]);
          // Shared/upper geometry wins identical same-source overlap,
          // retaining the original single-ownership landing contract.
          int rank=origin_groups_[i];
          if(source_box<0 || d<best-1e-12 || (std::abs(d-best)<=1e-12 && rank<origin_groups_[source_box])) {
            source_box=i;best=d;
          }
        });
        radius=2*radius+1e-9;
      }
      if(source_box<0)throw std::runtime_error("Gaussian face has no source conductor identity");
      bin=origin_groups_.at(source_box);
    }
''' +source[end:]
    edit('if(!origin_groups_.empty())return 2;','if(!origin_groups_.empty())return origin_partitions_;')
    edit('  const std::vector<int>& origin_groups_;','  const std::vector<int>& origin_groups_;\n  const int source_master_;\n  int origin_partitions_=0;')
    edit('solve_options.capture_nodes,solve_options.origin_box_groups);','solve_options.capture_nodes,solve_options.origin_box_groups,master);')
    (out/'Solver.cpp').write_text(source);shutil.copyfile(OLD/'include/fsv/Solver.h',include/'Solver.h')
    root=SOURCE/'src/fsv';flags=['g++','-std=c++20','-O3','-pthread','-I'+str(out/'include'),'-I'+str(root/'include'),'-I'+str(root/'src')]
    objects=[OLD/'GaussianSurface.o']+[SOURCE/n for n in proof['unchanged_objects']]
    assert all(sha(SOURCE/n)==v for n,v in proof['unchanged_objects'].items())
    if args.reuse_build:
        assert (args.reuse_build/'Solver.cpp').read_bytes()==(out/'Solver.cpp').read_bytes()
        assert (args.reuse_build/'include/fsv/Solver.h').read_bytes()==(include/'Solver.h').read_bytes()
        for name in ['Solver.o','native_field','lower_split_field','compile.log']:shutil.copy2(args.reuse_build/name,out/name)
    else:
        with (out/'compile.log').open('xb') as f:
            subprocess.run([*flags,'-c',str(out/'Solver.cpp'),'-o',str(out/'Solver.o')],stdout=f,stderr=subprocess.STDOUT,check=True)
            for client,name in [('native_field.cpp','native_field'),('lower_split_field.cpp','lower_split_field')]:
                subprocess.run([*flags,str(src/client),str(out/'Solver.o'),*map(str,objects),'-o',str(out/name)],stdout=f,stderr=subprocess.STDOUT,check=True)
    controls=OLD.parent/'controls';masters=out/'masters.txt';masters.write_text('0\n');checked=[]
    for name in ['split-one','split-many','single-owner','separate-neighbors','common-potential','disjoint-near-equal-coordinates']:
        target=out/(name+'.jsonl')
        if args.reuse_build:
            shutil.copyfile(args.reuse_build/(name+'.jsonl'),target);shutil.copyfile(args.reuse_build/(name+'.log'),out/(name+'.log'))
        else:
            with target.open('xb') as stdout,(out/(name+'.log')).open('xb') as stderr:
                subprocess.run([str(out/'native_field'),str(controls/(name+'.bin')),str(masters),'1' if name=='split-one' else '4','262144','.125','99991'],stdout=stdout,stderr=stderr,check=True)
        old=json.loads((controls/(name+'.jsonl')).read_text());new=json.loads(target.read_text())
        assert old==new,('Original golden result changed',name)
        checked.append(name)
    fixture=out/'nearest-quiet-source-owner.bin'
    write(fixture,['native_target','quiet_upper_neighbor'],[(1,0,[2.125,0,2,4.125,2,4]),(0,1,[0,0,2,2,2,4])])
    regression={}
    for name,binary in [('old',OLD/'native_field'),('fixed',out/'native_field')]:
        target=out/('nearest-'+name+'.jsonl')
        with target.open('xb') as stdout,(out/('nearest-'+name+'.log')).open('xb') as stderr:
            subprocess.run([str(binary),str(fixture),str(masters),'4','262144','.5','77771'],stdout=stdout,stderr=stderr,check=True)
        regression[name]=json.loads(target.read_text())
    old,new=regression['old'],regression['fixed']
    assert all(old[k]==new[k] for k in ['walks','hops','total_ff','sigma_ff','ground'])
    assert [[v[0],v[1]] for v in old['values']]==[[v[0],v[1]] for v in new['values']]
    assert abs(old['values'][0][2])>1e-6,'Regression failed to expose old attribution error'
    assert all(abs(v[2])<1e-12 for v in new['values']),'Native-only source wrongly assigned to upper'
    report=dict(source_solver=str(OLD/'Solver.cpp'),source_solver_sha256=sha(OLD/'Solver.cpp'),patched_solver_sha256=sha(out/'Solver.cpp'),
        original_solver_binary_sha256=proof['binary_sha256'],binary_sha256={n:sha(out/n) for n in ['native_field','lower_split_field']},
        linked_objects={str(p):sha(p) for p in objects},golden_controls_exact=checked,
        source_net_restricted_origin=True,dynamic_origin_partition_count=True,field_walks_and_whole_matrix_unchanged=True,
        regression_old_false_upper_source_ff=old['values'][0][2],regression_fixed_false_upper_source_ff=new['values'][0][2],
        all_controls_passed=True,scope='Fixes source charge attribution only. Uncorrected source-partition results require replacement; whole field matrices remain valid.')
    report['reused_build']=str(args.reuse_build) if args.reuse_build else None
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
