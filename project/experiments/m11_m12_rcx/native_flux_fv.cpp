// Independent Cartesian finite-difference charge reference in a grounded box.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <omp.h>

int main(int argc,char** argv) {
 try {
  if(argc!=3)throw std::runtime_error("grid_step threads");
  double h=std::stod(argv[1]);omp_set_num_threads(std::stoi(argv[2]));
  const int nx=std::lround(16/h)+1,ny=std::lround(8/h)+1,nz=std::lround(8/h)+1;
  const int stride=nx*ny,n=nx*ny*nz;
  std::vector<unsigned char> kind(n,0);
  auto id=[&](int x,int y,int z){return (z*ny+y)*nx+x;};
  for(int z=0;z<nz;++z)for(int y=0;y<ny;++y)for(int x=0;x<nx;++x) {
   double X=-8+x*h,Y=-4+y*h,Z=z*h;
   int i=id(x,y,z);
   if(x==0||x==nx-1||y==0||y==ny-1||z==0||z==nz-1)kind[i]=1;
   if(X>=-3&&X<=3&&Y>=-.5&&Y<=.5&&Z>=2&&Z<=3)kind[i]=2;
   if(X>=-4&&X<=-.5&&Y>=-1&&Y<=1&&Z>=4&&Z<=4.5)kind[i]=1;
  }
  const std::array<int,6> delta={-1,1,-nx,nx,-stride,stride};
  std::vector<double> value(n,0),r(n,0),p(n,0),ap(n,0);
  for(int i=0;i<n;++i)if(!kind[i])for(int d:delta)r[i]+=kind[i+d]==2;
  p=r;
  auto dot=[&](const std::vector<double>& a,const std::vector<double>& b){
   double s=0;
   #pragma omp parallel for reduction(+:s)
   for(int i=0;i<n;++i)s+=a[i]*b[i];
   return s;
  };
  double rr=dot(r,r),initial=rr;
  int iter=0;
  while(rr>initial*1e-16&&iter<5000) {
   #pragma omp parallel for
   for(int i=0;i<n;++i)if(!kind[i]) {
    ap[i]=6*p[i];for(int d:delta)ap[i]-=p[i+d];
   }
   double denominator=dot(p,ap);
   if(!(denominator>0))throw std::runtime_error("nonpositive conjugate-gradient direction");
   double alpha=rr/denominator;
   #pragma omp parallel for
   for(int i=0;i<n;++i){value[i]+=alpha*p[i];r[i]-=alpha*ap[i];}
   double next=dot(r,r),beta=next/rr;
   #pragma omp parallel for
   for(int i=0;i<n;++i)p[i]=r[i]+beta*p[i];
   rr=next;++iter;
  }
  if(rr>initial*1e-16)throw std::runtime_error("finite-difference solve did not converge");
  double left=0,right=0;
  for(int z=1;z<nz-1;++z)for(int y=1;y<ny-1;++y)for(int x=1;x<nx-1;++x) {
   int i=id(x,y,z);if(kind[i])continue;
   for(int d:delta)if(kind[i+d]==2) {
    int mx=(i+d)%nx;
    double X=-8+mx*h,q=1-value[i];
    if(X<0)left+=q;else if(X>0)right+=q;else{left+=q/2;right+=q/2;}
   }
  }
  const double factor=8.8541878128e-3*3.9*h;
  std::cout<<std::setprecision(17)<<"{\"h\":"<<h<<",\"nodes\":"<<n<<",\"iterations\":"<<iter
           <<",\"relative_residual\":"<<std::sqrt(rr/initial)<<",\"left_ff\":"<<left*factor
           <<",\"right_ff\":"<<right*factor<<"}\n";
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
