"""Private solver fork: associate surface samples with the nearest RC edge first.
This avoids assigning charge to a different nearby folded section merely because
its discrete node happens to be closer. Offset/mesh qualification remains required.
"""
import pathlib,json,hashlib
P=pathlib.Path;p=P(__file__).resolve().parent
src=P('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099/src/fsv')
(p/'include/fsv').mkdir(parents=True,exist_ok=True)
h=(src/'include/fsv/Solver.h').read_text();h='#include <array>\n'+h
h=h.replace('  std::vector<Vec3> partial_nodes;','  std::vector<Vec3> partial_nodes;\n  std::vector<std::array<int,2>> partial_edges;')
(p/'include/fsv/Solver.h').write_text(h)
s=(src/'src/Solver.cpp').read_text()
changes={
'const std::vector<std::vector<Vec3>>& captures)':'const std::vector<std::vector<Vec3>>& captures, const std::vector<std::array<int,2>>& edges)',
'capture_nodes_(captures)':'capture_nodes_(captures), partial_edges_(edges)',
'  std::vector<int> capture_offsets_;':'  std::vector<int> capture_offsets_;\n  const std::vector<std::array<int,2>>& partial_edges_;',
'solve_options.partial_nodes,solve_options.capture_nodes);':'solve_options.partial_nodes,solve_options.capture_nodes,solve_options.partial_edges);'}
for a,b in changes.items():assert a in s,a;s=s.replace(a,b)
a='''      for (size_t i=0;i<partial_nodes_.size();++i) {
        double d=0;
        for (int k=0;k<D;++k) d+=(p[k]-partial_nodes_[i][k])*(p[k]-partial_nodes_[i][k]);
        if (d<best) {best=d; bin=int(i);}
      }'''
b='''      if (!partial_edges_.empty()) {
        for (const auto& edge:partial_edges_) {
          const auto& a=partial_nodes_[edge[0]]; const auto& b=partial_nodes_[edge[1]];
          double dot=0,len2=0;
          for(int k=0;k<D;++k) {dot+=(p[k]-a[k])*(b[k]-a[k]);len2+=(b[k]-a[k])*(b[k]-a[k]);}
          const double t=std::clamp(dot/len2,0.0,1.0);double d=0;
          for(int k=0;k<D;++k) {const double delta=p[k]-(a[k]+t*(b[k]-a[k]));d+=delta*delta;}
          if(d<best) {best=d;bin=t<=0.5?edge[0]:edge[1];}
        }
      } else {
        for (size_t i=0;i<partial_nodes_.size();++i) {
          double d=0;
          for (int k=0;k<D;++k) d+=(p[k]-partial_nodes_[i][k])*(p[k]-partial_nodes_[i][k]);
          if (d<best) {best=d; bin=int(i);}
        }
      }'''
assert a in s;s=s.replace(a,b);(p/'Solver-edge.cpp').write_text(s)
c=(p/'node_row.cpp').read_text().replace('argc != 7','argc != 8')
c=c.replace('    opts.partial_nodes = nodes[master];','''    opts.partial_nodes = nodes[master];
    std::ifstream edges(argv[7]); int a,b; double resistance;
    while(edges >> a >> b >> resistance) {
      if(a<0 || b<0 || a==b || a>=int(nodes[master].size()) || b>=int(nodes[master].size()) || !(resistance>0)) throw std::runtime_error("invalid RC edge");
      opts.partial_edges.push_back({a,b});
    }
    if(opts.partial_edges.empty()) throw std::runtime_error("missing RC edges");''')
(p/'node_edge.cpp').write_text(c)
for key,g in json.loads((p/'graphs.json').read_text()).items():
 (p/(key+'.edges')).write_text(''.join('%d %d %.15g\n'%tuple(edge) for edge in g['resistors']))
(p/'fork-source-sha.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src/'include/fsv/Solver.h',src/'src/Solver.cpp']},indent=2))
