"""Research-only nearest-graph-node Gaussian flux partition.

Apply after the recorded plane-bin patch. Only the partition assignment changes;
the field walk and net capture stay upstream. Conductor-local charge requires
independent face-flux and offset convergence, never total-C conservation alone.
"""
import hashlib
import json


def patch(prefix, out):
    changes = []
    def edit(relative, replacements):
        path = prefix / relative
        before = path.read_bytes()
        text = before.decode()
        for old, new, count in replacements:
            assert text.count(old) == count, (relative, old, text.count(old), count)
            text = text.replace(old, new)
        after = text.encode()
        path.write_bytes(after)
        changes.append(dict(path=relative, before_sha256=hashlib.sha256(before).hexdigest(),
                            after_sha256=hashlib.sha256(after).hexdigest()))
    edit('src/fsv/include/fsv/Solver.h', [
        ('  std::vector<double> partial_cuts;',
         '  std::vector<double> partial_cuts;\n  std::vector<Vec3> partial_nodes;', 1)])
    edit('src/fsv/src/Solver.cpp', [
        ('const int partial_axis, const std::vector<double>& cuts)',
         'const int partial_axis, const std::vector<double>& cuts, const std::vector<Vec3>& nodes)', 1),
        ('partial_axis_(partial_axis), partial_cuts_(cuts)',
         'partial_axis_(partial_axis), partial_cuts_(cuts), partial_nodes_(nodes)', 1),
        ('    const double first_size = index_.nearest(p).dist;',
         '''    if (!partial_nodes_.empty()) {
      double best=std::numeric_limits<double>::infinity();
      for (size_t i=0;i<partial_nodes_.size();++i) {
        double d=0;
        for (int k=0;k<D;++k) d+=(p[k]-partial_nodes_[i][k])*(p[k]-partial_nodes_[i][k]);
        if (d<best) {best=d; bin=int(i);}
      }
    }
    const double first_size = index_.nearest(p).dist;''', 1),
        ('int partitions() const {return partial_axis_<0?0:int(partial_cuts_.size())+1;}',
         'int partitions() const {return !partial_nodes_.empty()?int(partial_nodes_.size()):(partial_axis_<0?0:int(partial_cuts_.size())+1);}', 1),
        ('  const std::vector<double>& partial_cuts_;',
         '  const std::vector<double>& partial_cuts_;\n  const std::vector<Vec3>& partial_nodes_;', 1),
        ('  checkSolveArguments(geometry, master, solve_options);',
         '''  checkSolveArguments(geometry, master, solve_options);
  if(!solve_options.partial_nodes.empty()) {
    if(D!=3 || solve_options.partial_axis!=-1 || !solve_options.partial_cuts.empty())
      throw std::invalid_argument("research graph bins cannot mix with plane bins");
    for(size_t i=0;i<solve_options.partial_nodes.size();++i) {
      for(double v:solve_options.partial_nodes[i]) if(!std::isfinite(v))
        throw std::invalid_argument("nonfinite graph node");
      for(size_t j=0;j<i;++j) if(solve_options.partial_nodes[i]==solve_options.partial_nodes[j])
        throw std::invalid_argument("duplicate graph node");
    }
  }''', 1),
        ('k,solve_options.partial_axis,solve_options.partial_cuts);',
         'k,solve_options.partial_axis,solve_options.partial_cuts,solve_options.partial_nodes);', 1)])
    record = dict(schema='block-v1-research-graph-field-patch/1', changes=changes,
        scope='Nearest 3D origin-node Gaussian flux bins only; net capture is unchanged, general node-pair capacitance and distributed RC remain unqualified')
    (out / 'graph-field-patch.json').write_text(json.dumps(record, indent=2) + '\n')
    return record
