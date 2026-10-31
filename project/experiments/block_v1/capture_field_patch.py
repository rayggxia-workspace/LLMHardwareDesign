"""Research terminal-node flux instrumentation; compose after graph patch.

The walk, net potentials and conductor geometry are unchanged. Joint bins use
the actual terminal position, never a length split or a product of marginals.
Finite-offset/local accuracy needs independent boundary-patch FV acceptance.
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
        ('  std::vector<Vec3> partial_nodes;',
         '  std::vector<Vec3> partial_nodes;\n  std::vector<std::vector<Vec3>> capture_nodes;', 1),
        ('  std::vector<std::vector<double>> partial_sigma;',
         '  std::vector<std::vector<double>> partial_sigma;\n'
         '  std::vector<std::vector<double>> joint_cap, joint_sigma;', 1)])
    edit('src/fsv/src/Solver.cpp', [
        ('  explicit Tally(const int columns, const int bins = 0)',
         '  std::vector<double> js, js2, dest2;\n'
         '  explicit Tally(const int columns, const int bins = 0, const int destinations = 0)', 1),
        ('pa(bins,0.0), pa2(bins,0.0)',
         'pa(bins,0.0), pa2(bins,0.0), js(bins*destinations,0.0),\n'
         '        js2(bins*destinations,0.0), dest2(destinations,0.0)', 1),
        ('    sum_all += other.sum_all;',
         '    for(size_t i=0;i<js.size();++i) {js[i]+=other.js[i]; js2[i]+=other.js2[i];}\n'
         '    for(size_t i=0;i<dest2.size();++i) dest2[i]+=other.dest2[i];\n'
         '    sum_all += other.sum_all;', 1),
        ('const std::vector<Vec3>& nodes)',
         'const std::vector<Vec3>& nodes, const std::vector<std::vector<Vec3>>& captures)', 1),
        ('partial_nodes_(nodes)\n  {\n  }',
         '''partial_nodes_(nodes), capture_nodes_(captures)
  {
    if (!captures.empty()) {
      capture_offsets_.push_back(0);
      for (const auto& group:captures)
        capture_offsets_.push_back(capture_offsets_.back()+std::max(1,int(group.size())));
      capture_offsets_.push_back(capture_offsets_.back()+1); // ground
    }
  }''', 1),
        ('bool& left, int& bin) const', 'bool& left, int& bin, int& destination) const', 1),
        ('    left = false;', '    left = false;\n    destination = -1;', 1),
        ('          return geometry_.netCount();',
         '          if(!capture_offsets_.empty()) destination=capture_offsets_[geometry_.netCount()];\n'
         '          return geometry_.netCount();', 1),
        ('        return geometry_.grounded(net) ? geometry_.netCount() : net;',
         '''        const int column=geometry_.grounded(net)?geometry_.netCount():net;
        if(!capture_offsets_.empty()) {
          int nearest=0;
          double best=std::numeric_limits<double>::infinity();
          if(column<geometry_.netCount()) {
            const auto& nodes=capture_nodes_[column];
            for(size_t i=0;i<nodes.size();++i) {
              double d=0;
              for(int k=0;k<D;++k) d+=(p[k]-nodes[i][k])*(p[k]-nodes[i][k]);
              if(d<best) {best=d; nearest=int(i);}
            }
          }
          destination=capture_offsets_[column]+nearest;
        }
        return column;''', 1),
        (' private:\n  // Whether the cube',
         '  int destinations() const {return capture_offsets_.empty()?0:capture_offsets_.back();}\n'
         ' private:\n  // Whether the cube', 1),
        ('  const std::vector<Vec3>& partial_nodes_;',
         '  const std::vector<Vec3>& partial_nodes_;\n'
         '  const std::vector<std::vector<Vec3>>& capture_nodes_;\n'
         '  std::vector<int> capture_offsets_;', 1),
        ('Tally tally(columns,walker.partitions());',
         'Tally tally(columns,walker.partitions(),walker.destinations());', 1),
        ('Tally total(columns,walker.partitions());',
         'Tally total(columns,walker.partitions(),walker.destinations());', 2),
        ('Tally(columns,walker.partitions()));',
         'Tally(columns,walker.partitions(),walker.destinations()));', 3),
        ('      int bin=-1;\n      const int column = walker.walk(w, weight, hops, left, bin);',
         '      int bin=-1,destination=-1;\n'
         '      const int column = walker.walk(w, weight, hops, left, bin, destination);', 1),
        ('      tally.sum[column] += weight;',
         '''      if(destination>=0) {
        const int count=int(tally.dest2.size());
        tally.js[bin*count+destination]+=weight;
        tally.js2[bin*count+destination]+=weight*weight;
        tally.dest2[destination]+=weight*weight;
      }
      tally.sum[column] += weight;''', 1),
        ('  row.partial_sigma=row.partial_cap;',
         '''  row.joint_cap.assign(total.pa.size(),std::vector<double>(total.dest2.size()));
  row.joint_sigma=row.joint_cap;
  for(size_t b=0;b<total.pa.size();++b) for(size_t c=0;c<total.dest2.size();++c) {
    const double beta=total.sum2_all>0?total.dest2[c]/total.sum2_all:0;
    const size_t i=b*total.dest2.size()+c;
    const double mean=(total.js[i]-beta*total.pa[b])/n;
    const double second=(total.js2[i]*(1-2*beta)+beta*beta*total.pa2[b])/n;
    row.joint_cap[b][c]=mean;
    row.joint_sigma[b][c]=std::sqrt(std::max(0.0,second-mean*mean)/n);
  }
  row.partial_sigma=row.partial_cap;''', 1),
        ('  checkSolveArguments(geometry, master, solve_options);',
         '''  checkSolveArguments(geometry, master, solve_options);
  if(!solve_options.capture_nodes.empty()) {
    if(D!=3 || solve_options.partial_nodes.empty()
       || solve_options.capture_nodes.size()!=size_t(geometry.netCount())
       || !solve_options.capture_nodes[master].empty())
      throw std::invalid_argument("capture bins require 3D origin nodes and an unsplit master");
    for(const auto& group:solve_options.capture_nodes) for(size_t i=0;i<group.size();++i) {
      for(double v:group[i]) if(!std::isfinite(v))
        throw std::invalid_argument("nonfinite capture node");
      for(size_t j=0;j<i;++j) if(group[i]==group[j])
        throw std::invalid_argument("duplicate capture node");
    }
  }''', 1),
        ('k,solve_options.partial_axis,solve_options.partial_cuts,solve_options.partial_nodes);',
         'k,solve_options.partial_axis,solve_options.partial_cuts,solve_options.partial_nodes,solve_options.capture_nodes);', 1)])
    record = dict(schema='block-v1-research-capture-field-patch/1', changes=changes,
                  scope='Actual terminal-position joint flux bins; no independent local-accuracy, full-block or stitching qualification')
    (out / 'capture-field-patch.json').write_text(json.dumps(record, indent=2) + '\n')
    return record
