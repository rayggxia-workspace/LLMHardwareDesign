// Fixed-macro sequence-pair search with actual pin/driver-capacitance costs.
// This is placement only. Python independently verifies every candidate cost.
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <stdexcept>
#include <vector>
using namespace std;
struct End {int id;double x,y;};
struct Net {double budget;bool external;vector<End> ends;};
struct Cost {double energy,wire,w,h,ratio;int violations;};
int main(int argc,char**argv){try{
 if(argc!=4)throw runtime_error("input output seed required");
 ifstream in(argv[1]);int n,k,iterations,rotate;double gap;in>>n>>k>>iterations>>gap>>rotate;
 string extra;getline(in,extra);double capacity_target=0,local_weight=0;
 if(extra.find_first_not_of(" \t\r")!=string::npos){istringstream options(extra);vector<double>values;double v;while(options>>v)values.push_back(v);if(!options.eof()||values.empty()||values.size()>2)throw runtime_error("invalid capacity objective");capacity_target=values[0];if(values.size()==2)local_weight=values[1];}
 if(!isfinite(local_weight)||local_weight<0||local_weight>1e10)throw runtime_error("invalid local search weight");
 // High congestion costs must not make necessary electrical-budget excess
 // cheap. Defaults and the earlier <=1e8 search mode remain byte compatible.
 double budget_weight=local_weight>=1e9?local_weight:5000;
 if(capacity_target!=0&&(capacity_target<.35||capacity_target>.8))throw runtime_error("capacity objective outside explicit range");
 if(!in||n!=26||k<7000||iterations<1000)throw runtime_error("invalid envelope");
 vector<double>w(n),h(n),ww(n),hh(n);for(int i=0;i<n;++i){in>>w[i]>>h[i];if(w[i]!=h[i])throw runtime_error("Square fixed macros required for this rotation search");ww[i]=ceil(w[i]/4)*4+gap;hh[i]=ceil(h[i]/4)*4+gap;}
 vector<Net>nets(k);for(auto& net:nets){int ext,count;in>>net.budget>>ext>>count;net.external=ext;net.ends.resize(count);for(auto& e:net.ends)in>>e.id>>e.x>>e.y;if(!in||count<1)throw runtime_error("invalid actual endpoint");}
 mt19937 rng(stoul(argv[3]));auto uniform=[&](){return generate_canonical<double,53>(rng);};
 vector<int>rot(n,0);
 auto shifts=[&](int i){int r=rot[i];return array<double,2>{r==0?0:r==1?.165-fmod(w[i],4):r==2?.19-fmod(w[i],4):.025,r==0?0:r==1?-.025:r==2?.14-fmod(h[i],4):.165-fmod(h[i],4)};};
 auto cost=[&](const vector<double>&x,const vector<double>&y){
  double W=0,H=0;for(int i=0;i<n;++i){auto s=shifts(i);W=max(W,x[i]+s[0]+w[i]);H=max(H,y[i]+s[1]+h[i]);}W=ceil((W+256)/4)*4;H=ceil((H+256)/4)*4;
  Cost c{0,0,W,H,0,0};
  array<array<double,17>,17> horizontal{},vertical{};
  for(auto& net:nets){double x0=1e30,y0=1e30,x1=-1e30,y1=-1e30;
   for(auto e:net.ends){int i=e.id,r=rot[i];auto s=shifts(i);double ex=r==0?e.x:r==1?w[i]-e.y:r==2?w[i]-e.x:e.y,ey=r==0?e.y:r==1?e.x:r==2?h[i]-e.y:h[i]-e.x;double xx=x[i]+s[0]+128+ex,yy=y[i]+s[1]+128+ey;x0=min(x0,xx);x1=max(x1,xx);y0=min(y0,yy);y1=max(y1,yy);}
   double length=x1-x0+y1-y0;if(net.external)length+=min({x0-32,W-32-x1,y0-32,H-32-y1});
   c.wire+=length;c.energy+=length;
   if(net.budget>0){double extra=max(0.0,length-net.budget);c.violations+=extra>1e-7;c.ratio=max(c.ratio,length/net.budget);c.energy+=budget_weight*extra*extra/net.budget;}
   if(local_weight>0){
    int a=clamp(int(x0*16/W),0,15),b=clamp(int(x1*16/W),0,15),d=clamp(int(y0*16/H),0,15),e=clamp(int(y1*16/H),0,15);
    double area=(b-a+1)*(e-d+1)*W*H/256;
    auto deposit=[&](auto& grid,double value){grid[a][d]+=value;grid[b+1][d]-=value;grid[a][e+1]-=value;grid[b+1][e+1]+=value;};
    // One preferred-direction layer at the original4um pitch. Quantized
    // uniform-bbox demand is a search heuristic, never a feasibility gate.
    deposit(horizontal,4*(x1-x0)/area);deposit(vertical,4*(y1-y0)/area);
   }
  }
  c.energy+=800*(W+H)+.05*W*H+1500*abs(W-H);
  // BBox wire cells / total two-layer cells is only a placement proxy.
  // Lower utilization leaves space for access/vias and negotiated detours.
  if(capacity_target>0)c.energy+=1e8*pow(max(0.0,2*c.wire/(W*H)-capacity_target),2);
  if(local_weight>0){double penalty=0;
   for(int x=0;x<16;++x)for(int y=0;y<16;++y){
    auto prefix=[&](auto& grid){grid[x][y]+=(x?grid[x-1][y]:0)+(y?grid[x][y-1]:0)-(x&&y?grid[x-1][y-1]:0);return grid[x][y];};
    penalty+=pow(max(0.0,prefix(horizontal)-.7),2)+pow(max(0.0,prefix(vertical)-.7),2);
   }c.energy+=local_weight*penalty/256;
  }
  return c;
 };
 auto pack=[&](const vector<int>&p,const vector<int>&q,vector<double>&x,vector<double>&y){
  vector<int>rank(n);for(int i=0;i<n;++i)rank[q[i]]=i;x.assign(n,0);y.assign(n,0);
  for(int i=0;i<n;++i)for(int j=i+1;j<n;++j){int a=p[i],b=p[j];if(rank[a]<rank[b])x[b]=max(x[b],x[a]+ww[a]);else y[b]=max(y[b],y[a]+hh[a]);}
 };
 vector<int>p(n),q(n);iota(p.begin(),p.end(),0);q=p;shuffle(p.begin(),p.end(),rng);shuffle(q.begin(),q.end(),rng);
 vector<double>x,y;pack(p,q,x,y);Cost current=cost(x,y),best=current;vector<double>bx=x,by=y;vector<int>br=rot;double initial=max(1e6,current.energy*.03);
 for(int t=0;t<iterations;++t){auto pp=p,qq=q,oldrot=rot;int a=rng()%n,b=rng()%n;if(a==b)continue;int mode=rng()%(rotate?4:3);
  if(mode==3)rot[a]=rng()%4;else{if(mode!=1)swap(pp[a],pp[b]);if(mode!=0)swap(qq[a],qq[b]);}vector<double>xx,yy;pack(pp,qq,xx,yy);auto c=cost(xx,yy);
  double temp=initial*pow(1-double(t)/iterations,3)+100;
  if(c.energy<current.energy||uniform()<exp(min(0.0,(current.energy-c.energy)/temp))){p=move(pp);q=move(qq);x=move(xx);y=move(yy);current=c;}else rot=oldrot;
  if(current.energy<best.energy){best=current;bx=x;by=y;br=rot;}
 }
 // Translate one unchanged rectangle at a time; reject every overlap. This
 // refines pin alignment that compact sequence-pair packing alone cannot vary.
 x=bx;y=by;rot=br;current=best;
 for(int t=0;t<10000;++t){auto xx=x,yy=y;int a=rng()%n,step=array<int,4>{4,16,64,256}[rng()%4];if(rng()%2)step=-step;
  if(rng()%2)xx[a]+=step;else yy[a]+=step;double lowx=*min_element(xx.begin(),xx.end()),lowy=*min_element(yy.begin(),yy.end());
  for(int i=0;i<n;++i){xx[i]-=lowx;yy[i]-=lowy;}bool legal=true;
  for(int b=0;b<n;++b)if(a!=b&&!(xx[a]+w[a]+gap<=xx[b]||xx[b]+w[b]+gap<=xx[a]||yy[a]+h[a]+gap<=yy[b]||yy[b]+h[b]+gap<=yy[a])){legal=false;break;}
  if(!legal)continue;auto c=cost(xx,yy);double temp=50000*pow(1-double(t)/10000,3)+100;
  if(c.energy<current.energy||uniform()<exp(min(0.0,(current.energy-c.energy)/temp))){x=move(xx);y=move(yy);current=c;}
  if(current.energy<best.energy){best=current;bx=x;by=y;}
 }
 ofstream out(argv[2]);out.precision(17);out<<best.energy<<' '<<best.wire<<' '<<best.w<<' '<<best.h<<' '<<best.ratio<<' '<<best.violations<<'\n';
 for(int i=0;i<n;++i)out<<bx[i]<<' '<<by[i]<<' '<<br[i]<<'\n';if(!out)throw runtime_error("output failed");return 0;
}catch(const exception&e){cerr<<e.what()<<endl;return 1;}}
