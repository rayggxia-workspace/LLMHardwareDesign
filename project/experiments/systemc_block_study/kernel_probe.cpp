#include <cstdint>
#include <iostream>
#include <array>
using I=__int128_t;
std::array<int64_t,3> parts(int32_t x){
 uint32_t u=static_cast<uint32_t>(x);
 int64_t lo=static_cast<int16_t>(u&65535u),hi=static_cast<int16_t>(u>>16);
 return {lo,hi,(u&32768u)?1:0};
}
int32_t round_sat(I x,int shift){
 I unit=I(1)<<shift,q=x/unit,r=x%unit;
 if(r<0){--q;r+=unit;}
 if(shift&&(2*r>unit||(2*r==unit&&(q&1))))++q;
 if(q>INT32_MAX)return INT32_MAX;
 if(q<INT32_MIN)return INT32_MIN;
 return static_cast<int32_t>(q);
}
int main(){
 int cases;std::cin>>cases;
 for(int c=0;c<cases;++c){int k,shift;std::cin>>k>>shift;I acc=0;const I factor[3]={1,65536,65536};
  for(int i=0;i<k;++i){int32_t a,b;std::cin>>a>>b;auto x=parts(a),y=parts(b);
   for(int j=0;j<3;++j)for(int l=0;l<3;++l)acc+=I(x[j])*y[l]*factor[j]*factor[l];
  }
  // A 96-bit candidate accumulator must contain every full-K intermediate.
  if(acc<-(I(1)<<95)||acc>=(I(1)<<95))return 3;
  std::cout<<round_sat(acc,shift)<<'\n';
 }
 return std::cin?0:2;
}
