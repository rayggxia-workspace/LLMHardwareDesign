"""Explicit research instrumentation of the hash-verified upstream solver.

Bins integrate flux on open pieces of the Gaussian surface, not conductor
charge at finite offset. Offset convergence and independent surface-flux FV
comparison are required separately. Default solves retain the upstream path.
"""
import hashlib
import json


def patch(prefix,out):
    changes=[]
    def edit(relative,replacements):
        path=prefix/relative;before=path.read_bytes();text=before.decode()
        for old,new,count in replacements:
            assert text.count(old)==count,(relative,old,text.count(old),count)
            text=text.replace(old,new)
        after=text.encode();path.write_bytes(after)
        changes.append(dict(path=relative,before_sha256=hashlib.sha256(before).hexdigest(),
                            after_sha256=hashlib.sha256(after).hexdigest()))
    edit('src/fsv/include/fsv/Solver.h',[
        ('  double gauss_offset = 0.5;',
         '  double gauss_offset = 0.5;\n  int partial_axis = -1;\n  std::vector<double> partial_cuts;',1),
        ('  double total() const { return cap[master]; }',
         '  std::vector<std::vector<double>> partial_cap;\n  std::vector<std::vector<double>> partial_sigma;\n'
         '  double total() const { return cap[master]; }',1)])
    edit('src/fsv/src/Solver.cpp',[
        ('  explicit Tally(const int columns)\n      : sum(columns + kPad, 0.0), sum2(columns + kPad, 0.0)',
         '  std::vector<double> ps, ps2, pa, pa2;\n'
         '  explicit Tally(const int columns, const int bins = 0)\n'
         '      : sum(columns + kPad, 0.0), sum2(columns + kPad, 0.0),\n'
         '        ps(columns*bins,0.0), ps2(columns*bins,0.0), pa(bins,0.0), pa2(bins,0.0)',1),
        ('    sum_all += other.sum_all;',
         '    for (size_t i=0;i<ps.size();++i) {ps[i]+=other.ps[i]; ps2[i]+=other.ps2[i];}\n'
         '    for (size_t i=0;i<pa.size();++i) {pa[i]+=other.pa[i]; pa2[i]+=other.pa2[i];}\n'
         '    sum_all += other.sum_all;',1),
        ('         const uint64_t key)\n',
         '         const uint64_t key, const int partial_axis, const std::vector<double>& cuts)\n',1),
        ('        key_(key)\n',
         '        key_(key), partial_axis_(partial_axis), partial_cuts_(cuts)\n',1),
        ('           bool& left) const\n',
         '           bool& left, int& bin) const\n',1),
        ('    const double first_size = index_.nearest(p).dist;',
         '    bin = partial_axis_ < 0 ? -1 : int(std::ranges::upper_bound(partial_cuts_,p[partial_axis_])-partial_cuts_.begin());\n'
         '    const double first_size = index_.nearest(p).dist;',1),
        (' private:\n  // Whether the cube',
         '  int partitions() const {return partial_axis_<0?0:int(partial_cuts_.size())+1;}\n'
         ' private:\n  // Whether the cube',1),
        ('  const uint64_t key_;\n',
         '  const uint64_t key_;\n  const int partial_axis_;\n  const std::vector<double>& partial_cuts_;\n',1),
        ('    Tally tally(columns);',
         '    Tally tally(columns,walker.partitions());',1),
        ('      const int column = walker.walk(w, weight, hops, left);',
         '      int bin=-1;\n      const int column = walker.walk(w, weight, hops, left, bin);',1),
        ('      tally.sum[column] += weight;',
         '      if(bin>=0) {\n'
         '        tally.ps[bin*columns+column]+=weight; tally.ps2[bin*columns+column]+=weight*weight;\n'
         '        tally.pa[bin]+=weight; tally.pa2[bin]+=weight*weight;\n      }\n'
         '      tally.sum[column] += weight;',1),
        ('  row.window_leakage = total.left_sum / n;',
         '  row.window_leakage = total.left_sum / n;\n'
         '  const int columns=nets+1;\n'
         '  row.partial_cap.assign(total.pa.size(),std::vector<double>(columns));\n'
         '  row.partial_sigma=row.partial_cap;\n'
         '  for(size_t b=0;b<total.pa.size();++b) for(int c=0;c<columns;++c) {\n'
         '    const double beta=total.sum2_all>0?total.sum2[c]/total.sum2_all:0;\n'
         '    const double mean=(total.ps[b*columns+c]-beta*total.pa[b])/n;\n'
         '    const double second=(total.ps2[b*columns+c]*(1-2*beta)+beta*beta*total.pa2[b])/n;\n'
         '    row.partial_cap[b][c]=mean;\n'
         '    row.partial_sigma[b][c]=std::sqrt(std::max(0.0,second-mean*mean)/n);\n'
         '  }',1),
        ('  Tally total(columns);','  Tally total(columns,walker.partitions());',2),
        ('Tally(columns));','Tally(columns,walker.partitions()));',3),
        ('  checkSolveArguments(geometry, master, solve_options);',
         '  checkSolveArguments(geometry, master, solve_options);\n'
         '  if(solve_options.partial_axis < -1 || solve_options.partial_axis>=D ||\n'
         '     (solve_options.partial_axis<0 && !solve_options.partial_cuts.empty()))\n'
         '    throw std::invalid_argument("research partial axis/cuts");\n'
         '  for(size_t i=0;i<solve_options.partial_cuts.size();++i)\n'
         '    if(!std::isfinite(solve_options.partial_cuts[i]) ||\n'
         '       (i && solve_options.partial_cuts[i]<=solve_options.partial_cuts[i-1]))\n'
         '      throw std::invalid_argument("research partial cuts must increase");',1),
        ('                         k);','                         k,solve_options.partial_axis,solve_options.partial_cuts);',1)])
    record=dict(schema='block-v1-research-partial-field-patch/1',changes=changes,
        scope='Origin-position Gaussian flux bins only; no qualification of conductor charge, distributed RC or twelve-layer stitching')
    (out/'partial-field-patch.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
