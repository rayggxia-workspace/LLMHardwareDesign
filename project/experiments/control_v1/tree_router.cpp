// Multi-terminal negotiated M11/M12 router. Independent Python verification
// checks the returned edges, all landings and global occupancy before use.
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
struct Item {int64_t priority,cost;int node;bool operator<(const Item& q)const{return priority>q.priority;}};
int main(int argc,char**argv){try{
 if(argc!=3)throw runtime_error("input/output arguments required");
 ifstream in(argv[1]);int nx,ny,count,seed,rounds;in>>nx>>ny>>count>>seed>>rounds;
 if(!in||nx<16||ny<16||count<1||int64_t(nx)*ny*2>numeric_limits<int>::max())throw runtime_error("invalid input envelope");
 int plane=nx*ny,size=plane*2;
 auto node=[&](int x,int y,int l){return l*plane+y*nx+x;};
 auto coord=[&](int v){return array<int,3>{v%nx,(v%plane)/nx,v/plane};};
 auto inside=[&](int x,int y){return x>=4&&x<nx-4&&y>=4&&y<ny-4;};
 vector<string>names(count);vector<vector<int>>ends(count);vector<int>fixed(size,-1);
 for(int n=0;n<count;++n){int k;in>>names[n]>>k;if(!in||k<2)throw runtime_error("invalid net");
  for(int i=0;i<k;++i){int x,y;in>>x>>y;if(!in||!inside(x,y))throw runtime_error("landing outside grid");
   int v=node(x,y,0);if(fixed[v]!=-1)throw runtime_error("overlapping landing");fixed[v]=n;ends[n].push_back(v);}}
 vector<vector<vector<int>>>access(count),branches(count);
 for(int n=0;n<count;++n)for(int v:ends[n]){
  auto c=coord(v);int x=c[0],y=c[1];vector<pair<int,int>>sites;
  if((x+y)%2==0)sites={{x,y}};else sites={{x+1,y},{x-1,y},{x,y+1},{x,y-1}};
  bool found=false;for(auto xy:sites){int xx=xy.first,yy=xy.second;if(!inside(xx,yy))continue;
   vector<int>stub{v};if(xx!=x||yy!=y)stub.push_back(node(xx,yy,0));stub.push_back(node(xx,yy,1));
   bool legal=true;for(int w:stub)if(fixed[w]!=-1&&fixed[w]!=n)legal=false;if(!legal)continue;
   for(int w:stub)fixed[w]=n;access[n].push_back(stub);found=true;break;}
  if(!found)throw runtime_error("no reserved access: "+names[n]);
 }
 vector<uint32_t>usage(size),history(size),marked(size),visited(size);
 vector<int64_t>distance(size);vector<int>parent(size);uint32_t epoch=0,search=0;
 vector<vector<int>>trees(count);vector<int>order(count);iota(order.begin(),order.end(),0);mt19937 rng(seed);shuffle(order.begin(),order.end(),rng);
 bool complete=false;
 for(int iteration=0;iteration<rounds;++iteration){
  if(iteration){vector<int>congestion(count);for(int n=0;n<count;++n)for(int v:trees[n])congestion[n]+=max(0,int(usage[v])-1);
   stable_sort(order.begin(),order.end(),[&](int a,int b){return congestion[a]>congestion[b];});}
  int number=0;
  for(int n:order){
   for(int v:trees[n]){if(!usage[v])throw runtime_error("usage underflow");--usage[v];}
   ++epoch;if(!epoch)throw runtime_error("tree epoch overflow");vector<int>tree;branches[n].clear();
   auto add=[&](int v){if(marked[v]!=epoch){marked[v]=epoch;tree.push_back(v);}};
   for(int v:access[n][0])add(v);branches[n].push_back(access[n][0]);
   vector<int>todo(access[n].size()-1);iota(todo.begin(),todo.end(),1);
   while(!todo.empty()){
    int xlo=nx,xhi=0,ylo=ny,yhi=0;for(int v:tree){auto c=coord(v);xlo=min(xlo,c[0]);xhi=max(xhi,c[0]);ylo=min(ylo,c[1]);yhi=max(yhi,c[1]);}
    auto h=[&](int v){auto c=coord(v);return max({xlo-c[0],0,c[0]-xhi})+max({ylo-c[1],0,c[1]-yhi});};
    auto chosen=min_element(todo.begin(),todo.end(),[&](int a,int b){return h(access[n][a].back())<h(access[n][b].back());});
    int k=*chosen;todo.erase(chosen);int start=access[n][k].back(),goal=-1;
    ++search;if(!search)throw runtime_error("search epoch overflow");visited[start]=search;distance[start]=0;
    priority_queue<Item>q;q.push({h(start),0,start});
    while(!q.empty()){
     auto item=q.top();q.pop();int v=item.node;if(visited[v]!=search||distance[v]!=item.cost)continue;
     if(marked[v]==epoch){goal=v;break;}
     auto c=coord(v);int x=c[0],y=c[1],l=c[2];
     array<pair<int,int>,5>next{{{v-1,l==0?1:2},{v+1,l==0?1:2},{v-nx,l==1?1:2},{v+nx,l==1?1:2},{node(x,y,1-l),3}}};
     for(int i=0;i<5;++i){if(i==4&&(x+y)%2)continue;int w=next[i].first;auto cc=coord(w);
      if(w<0||w>=size||!inside(cc[0],cc[1])||(fixed[w]!=-1&&fixed[w]!=n))continue;
      int64_t alt=item.cost+next[i].second+int64_t(8+iteration*4)*usage[w]+int64_t(history[w])*4;
      if(visited[w]!=search||alt<distance[w]){visited[w]=search;distance[w]=alt;parent[w]=v;q.push({alt+h(w),alt,w});}}
    }
    if(goal<0)throw runtime_error("disconnected tree: "+names[n]);
    vector<int>path{goal};while(path.back()!=start)path.push_back(parent[path.back()]);reverse(path.begin(),path.end());
    vector<int>branch=access[n][k];branch.pop_back();branch.insert(branch.end(),path.begin(),path.end());
    for(int v:branch)add(v);branches[n].push_back(move(branch));
   }
   trees[n]=move(tree);for(int v:trees[n])++usage[v];++number;
   if(number%100==0)cout<<"{\"round\":"<<iteration<<",\"routed\":"<<number<<",\"total\":"<<count<<"}"<<endl;
  }
  uint64_t conflicts=0,excess=0;for(int v=0;v<size;++v)if(usage[v]>1){++conflicts;excess+=usage[v]-1;history[v]+=usage[v]-1;}
  cout<<"{\"round\":"<<iteration<<",\"conflict_nodes\":"<<conflicts<<",\"excess_occupancy\":"<<excess<<"}"<<endl;
  if(!conflicts){complete=true;break;}
 }
 if(!complete)throw runtime_error("negotiation did not converge");
 ofstream out(argv[2]);out<<count<<'\n';
 for(int n=0;n<count;++n){out<<names[n]<<' '<<branches[n].size()<<'\n';
  for(auto& branch:branches[n]){out<<branch.size();for(int v:branch){auto c=coord(v);out<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}out<<'\n';}}
 if(!out)throw runtime_error("cannot write complete route");return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
