// Reuse frozen signal driver, not its random stimulus or integer oracle.
#define main frozen_regression_main
#include "../../../work/YUZE-LU/157/inputs/test_recurrent_macro.cpp"
#undef main
#include <fstream>
template<class T>static std::vector<T> read_items(std::ifstream&f,size_t n){std::vector<T>v(n);f.read(reinterpret_cast<char*>(v.data()),n*sizeof(T));need(bool(f),"truncated binary corpus");return v;}
static Row row_of(const std::vector<int32_t>&v,size_t pos){Row r;std::copy(v.begin()+pos,v.begin()+pos+8,r.begin());return r;}
static void history_matches(const std::vector<int32_t>&v){for(unsigned j=0;j<3;++j)for(unsigned p=0;p<2;++p){auto reply=cmd(14,2*j+p,0).data;for(unsigned l=0;l<4;++l)need(int32_t(reply>>(32*l))==v[j*8+p*4+l],"corpus history mismatch");}}
int main(int argc,char**argv){try{
 need(argc==2,"usage corpus_rtl corpus.bin");Verilated::commandArgs(argc,argv);std::ifstream f(argv[1],std::ios::binary);need(bool(f),"corpus absent");auto h=read_items<uint32_t>(f,8);unsigned mode=h[0],n=h[1],layers=h[2],tokens=h[3],flags=h[5];
 if(mode!=2&&n>2048){std::cout<<"{\"status\":\"UNSUPPORTED_ORIGINAL_CAPACITY\"}\n";return 0;}
 std::vector<std::vector<int32_t>>states;for(unsigned l=0;l<layers;++l)states.push_back(read_items<int32_t>(f,n));reset();
 for(unsigned token=0;token<tokens;++token)for(unsigned layer=0;layer<layers;++layer){
  auto k=read_items<int16_t>(f,n/8),q=read_items<int16_t>(f,n/8);auto v=read_items<int32_t>(f,24);auto factors=read_items<uint32_t>(f,mode==1?n:0);auto taps=read_items<int16_t>(f,mode==2?32:0);auto status=read_items<uint32_t>(f,2);auto out=read_items<int32_t>(f,8),next=read_items<int32_t>(f,n);
  if(flags&32)std::fill(states[layer].begin(),states[layer].end(),0);
  open(mode==2?1:n/8);values(0,row_of(v,0));
  if(mode==2){for(unsigned j=0;j<3;++j)for(unsigned p=0;p<2;++p)cmd(9,j*2+p,half(row_of(states[layer],j*8),p));for(unsigned j=0;j<4;++j){U t=0;for(unsigned l=0;l<8;++l)t|=U(uint16_t(taps[j*8+l]))<<(16*l);cmd(10,j,t);}}
  else{
   std::vector<Row>a;for(unsigned i=0;i<n;i+=8)a.push_back(row_of(states[layer],i));state_load(a);load_vector(2,k);load_vector(3,q);values(2,row_of(v,8));cmd(5,0,U(h[6])|(U(h[7])<<32));cmd(5,1,half(row_of(v,16),0));cmd(5,2,half(row_of(v,16),1));
   if(mode==1)for(unsigned i=0;i<n;i+=4){U value=0;for(unsigned j=0;j<4;++j)value|=U(factors[i+j])<<(32*j);cmd(15,i/4,value);}
  }
  auto reply=execute(mode,!status[0]);need(reply.latency==(mode==2?14:mode==0?4*(n/8)+15:3*(n/8)+11),"corpus EXEC cycle mismatch");
  if(status[0])output_matches(row_of(out,0));
  if(status[1])commit(position+1);else cmd(8,0,0);
  if(mode==2)history_matches(next);else{std::vector<Row>a;for(unsigned i=0;i<n;i+=8)a.push_back(row_of(next,i));state_matches(a);}
  states[layer]=next;
 }
 need(f.peek()==std::char_traits<char>::eof(),"trailing corpus bytes");std::cout<<"{\"status\":\"PASS\",\"checks\":"<<checks<<",\"cycles\":"<<cycles<<"}\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
