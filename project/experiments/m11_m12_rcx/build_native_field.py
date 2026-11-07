"""Add explicit geometry-owner origin bins in a new local solver build.

The accepted solver source/objects stay read-only. Origin bins change reporting,
not geometry, dielectric, random walks, net potentials or total capacitance.
"""
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = Path('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(out, reuse=None):
    root = SOURCE / 'src/fsv'
    out.mkdir()
    include = out / 'include/fsv'
    include.mkdir(parents=True)
    header = (root / 'include/fsv/Solver.h').read_text()
    assert sha(root / 'include/fsv/Solver.h') == '09050c70f91ca154b207d959991dc3762968c62a06870573346fb10d421333d3'
    header = header.replace('  std::vector<Vec3> partial_nodes;',
        '  std::vector<Vec3> partial_nodes;\n  std::vector<int> origin_box_groups;')
    (include / 'Solver.h').write_text(header)
    source = (root / 'src/Solver.cpp').read_text()
    changes = []

    def edit(old, new):
        nonlocal source
        assert source.count(old) == 1, (old, source.count(old))
        source = source.replace(old, new)
        changes.append(old)

    edit('const std::vector<std::vector<Vec3>>& captures)',
         'const std::vector<std::vector<Vec3>>& captures, const std::vector<int>& origin_groups)')
    edit('capture_nodes_(captures)\n', 'capture_nodes_(captures), origin_groups_(origin_groups)\n')
    edit('    const double first_size = index_.nearest(p).dist;', '''    const auto origin = index_.nearest(p);
    if (!origin_groups_.empty()) {
      if (origin.box < 0) throw std::runtime_error("origin captured by ground plane");
      bin = origin_groups_.at(origin.box);
      // Prefer original upper geometry at shared M10 metal volume. This
      // assigns the physical union once instead of double-counting its pins.
      if (bin != 0) {
        AlignedBox<D> query;
        for (int k=0;k<D;++k) {
          query.lo[k]=p[k]-origin.dist-1e-12;
          query.hi[k]=p[k]+origin.dist+1e-12;
        }
        index_.forEachOverlapping(query,[&](int i) {
          if (origin_groups_[i]==0 && Frame::shapeNet(geometry_,i)==Frame::shapeNet(geometry_,origin.box)
              && linfDistance<D>(p,Frame::shapes(geometry_)[i])<=origin.dist+1e-12) bin=0;
        });
      }
    }
    const double first_size = origin.dist;''')
    edit('int partitions() const {return !partial_nodes_.empty()?',
         'int partitions() const {if(!origin_groups_.empty())return 2;return !partial_nodes_.empty()?')
    edit('  const std::vector<Vec3>& partial_nodes_;',
         '  const std::vector<Vec3>& partial_nodes_;\n  const std::vector<int>& origin_groups_;')
    edit('k,solve_options.partial_axis,solve_options.partial_cuts,solve_options.partial_nodes,solve_options.capture_nodes);',
         'k,solve_options.partial_axis,solve_options.partial_cuts,solve_options.partial_nodes,solve_options.capture_nodes,solve_options.origin_box_groups);')
    edit('  checkSolveArguments(geometry, master, solve_options);', '''  checkSolveArguments(geometry, master, solve_options);
  if(!solve_options.origin_box_groups.empty()) {
    if(solve_options.origin_box_groups.size()!=Frame::shapes(geometry).size()
       || !solve_options.partial_nodes.empty() || solve_options.partial_axis!=-1
       || !solve_options.capture_nodes.empty()) throw std::invalid_argument("origin geometry bin contract");
  }''')
    patched = out / 'Solver.cpp'
    patched.write_text(source)
    surface=(root/'src/GaussianSurface.cpp').read_text()
    old='''  double gap = box.lo[D - 1];
  for (int b = 0; b < static_cast<int>(boxes.size()); b++) {
    if (box_net(b) != master) {
      gap = std::min(gap, linfGap(box, boxes[b]));
    }
  }'''
    new='''  double min_extent=std::numeric_limits<double>::max();
  for(int k=0;k<D;++k) min_extent=std::min(min_extent,box.hi[k]-box.lo[k]);
  double gap=box.lo[D-1];
  if(dielectric.shells().empty()) {
    // With no conformal shell faces, only gaps smaller than twice the
    // desired offset can affect min(gap/2, desired). Query exactly those.
    gap=std::min(gap,2*offset_frac*min_extent);
    AlignedBox<D> query;
    for(int k=0;k<D;++k) {query.lo[k]=box.lo[k]-gap;query.hi[k]=box.hi[k]+gap;}
    conductors.forEachOverlapping(query,[&](int b) {
      if(box_net(b)!=master) gap=std::min(gap,linfGap(box,boxes[b]));
    });
  } else {
    for(int b=0;b<static_cast<int>(boxes.size());++b)
      if(box_net(b)!=master) gap=std::min(gap,linfGap(box,boxes[b]));
  }'''
    assert surface.count(old)==1
    surface=surface.replace(old,new)
    old='''double boxOffset(const AlignedBox<D>& box,
                 const std::vector<AlignedBox<D>>& boxes,
                 const std::function<int(int)>& box_net,'''
    assert surface.count(old)==1
    surface=surface.replace(old,old+'\n                 const SpatialIndex<D>& conductors,')
    old='''                                    box_net,
                                    dielectric,'''
    assert surface.count(old)==1
    surface=surface.replace(old,'''                                    box_net,
                                    conductors,
                                    dielectric,''')
    (out/'GaussianSurface.cpp').write_text(surface)
    flags = ['-std=c++20', '-O3', '-pthread', '-I'+str(out/'include'),
             '-I'+str(root/'include'), '-I'+str(root/'src')]
    with (out / 'compile.log').open('xb') as log:
        if reuse:
            import shutil
            assert (reuse/'Solver.cpp').read_bytes() == patched.read_bytes()
            assert (reuse/'include/fsv/Solver.h').read_bytes() == (include/'Solver.h').read_bytes()
            shutil.copyfile(reuse/'Solver.o',out/'Solver.o')
        else:
            subprocess.run(['g++', *flags, '-c', str(patched), '-o', str(out/'Solver.o')],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['g++',*flags,'-c',str(out/'GaussianSurface.cpp'),'-o',str(out/'GaussianSurface.o')],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
        objects = sorted(p for p in SOURCE.glob('*.o')
                         if p.stem not in ('Solver','GaussianSurface','Structures','fsv_client','partial_field_client','graph_field_client','capture_field_client'))
        assert len(objects) == 14, [p.name for p in objects]
        subprocess.run(['g++', *flags, str(Path(__file__).with_name('native_field.cpp')),
                        str(out/'Solver.o'),str(out/'GaussianSurface.o'), *map(str, objects), '-o', str(out/'native_field')],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    report = dict(source_solver_sha256=sha(root/'src/Solver.cpp'),
                  patched_solver_sha256=sha(patched), binary_sha256=sha(out/'native_field'),
                  unchanged_objects={p.name:sha(p) for p in objects},
                  origin_report_only=True, replacement_count=len(changes),
                  exact_uniform_clearance_index=True,
                  source_surface_sha256=sha(root/'src/GaussianSurface.cpp'),
                  patched_surface_sha256=sha(out/'GaussianSurface.cpp'),
                  reused_solver_object=str(reuse) if reuse else None)
    (out / 'build.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1]),Path(sys.argv[2]) if len(sys.argv)>2 else None)))
