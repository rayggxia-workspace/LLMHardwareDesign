from pathlib import Path
p=Path('project/experiments/control_v1');f=p/'tree_router.cpp';s=f.read_text();lines=s.splitlines();lines=[l.replace('\\\\"','\\"')if 'pin_policy=="all"){auto r='in l else l for l in lines];s='\n'.join(lines)+'\n';f.write_bytes(s.encode())
f=p/'pin_access_reservation.h';s=f.read_text();s=s.replace(' ofstream out(path);out<<',' if(!path.empty()){ofstream out(path);out<<',1).replace('out.close();\n if(require_complete','out.close();}\n if(require_complete',1)
s+=r'''
// Independent exhaustive assignment oracle on small random pin neighbourhoods.
// The oracle enumerates resource subsets; it does not reuse the matcher.
inline int pin_access_self_test(){
 mt19937 random(0x162849U);int checks=0;const int nx=20,ny=20,plane=400;
 for(int trial=0;trial<200;++trial){
  vector<vector<int>>ends(6);vector<int>fixed(2*plane,-1);vector<uint32_t>usage(2*plane);
  vector<int>pool;for(int y=6;y<12;++y)for(int x=6;x<12;++x)pool.push_back(y*nx+x);
  shuffle(pool.begin(),pool.end(),random);
  for(int n=0;n<6;++n){ends[n]={pool[n]};fixed[pool[n]]=n;}
  for(int j=0;j<25;++j){int v=(6+random()%6)*nx+6+random()%6+(random()%2)*plane;if(fixed[v]<0)fixed[v]=99;}
  auto before=fixed;vector<vector<int>>legal(6);int direct=0;
  for(int n=0;n<6;++n){int pin=ends[n][0],x=pin%nx,y=pin/nx;
   if((x+y)%2==0){if(before[pin+plane]<0||before[pin+plane]==n)++direct;continue;}
   for(int site:{pin-1,pin+1,pin-nx,pin+nx})if((before[site]<0||before[site]==n)&&(before[site+plane]<0||before[site+plane]==n))legal[n].push_back(site);
  }
  // Odd neighbours may not consume an even landing's reserved M12 point.
  for(int n=0;n<6;++n)for(int m=0;m<6;++m){int pin=ends[m][0];if((pin%nx+pin/nx)%2==0)
   legal[n].erase(remove(legal[n].begin(),legal[n].end(),pin),legal[n].end());}
  set<int>used;function<int(int)>enumerate=[&](int n){if(n==6)return 0;int best=enumerate(n+1);
   for(int site:legal[n])if(used.insert(site).second){best=max(best,1+enumerate(n+1));used.erase(site);}return best;};
  int expected=direct+enumerate(0);auto got=reserve_pin_access(nx,ny,0,ends,fixed,usage,trial,"",false);
  if(got.assigned!=expected||got.terminals!=6)throw runtime_error("pin matching disagrees with independent exhaustive oracle");
  for(size_t v=0;v<fixed.size();++v)if(before[v]>=0&&fixed[v]!=before[v])throw runtime_error("pin matching overwrote foreign fixed owner");
  ++checks;
 }
 return checks;
}
''';f.write_bytes(s.encode())
f=p/'tree_router.cpp';s=f.read_text();s=s.replace('int maze_checks=zero_maze_self_test();','int maze_checks=zero_maze_self_test();int pin_checks=pin_access_self_test();',1);a='<<maze_checks<<"}"<<endl;return 0;';assert s.count(a)==1;s=s.replace(a,'<<maze_checks<<",\\\"independent_pin_access_matching_checks\\\":"<<pin_checks<<"}"<<endl;return 0;',1);f.write_bytes(s.encode())
f=p/'tree_router_cpp.py';s=f.read_text();s=s.replace("    assert oracle['independent_zero_maze_checks']==800","    assert oracle['independent_pin_access_matching_checks']==200\n    assert oracle['independent_zero_maze_checks']==800",1);f.write_bytes(s.encode())
