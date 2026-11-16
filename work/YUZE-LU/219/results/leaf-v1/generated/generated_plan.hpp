#include <map>
#include <memory>
using NativeWord=std::array<uint32_t,4>;using Buffer=std::vector<NativeWord>;
static NativeWord lanes16(const blocks::Reply& r){NativeWord w{};for(unsigned i=0;i<r.count;++i)w[i/2]|=uint32_t(uint16_t(r.lane[i]))<<(16*(i%2));return w;}
static NativeWord lanes32(const blocks::Reply& r){NativeWord w{};for(unsigned i=0;i<4;++i)w[i]=uint32_t(r.lane[i]);return w;}
static std::array<int16_t,8> raw16(const Buffer& b){std::array<int16_t,8> a{};if(!b.empty())for(unsigned i=0;i<8;++i)a[i]=int16_t(b[0][i/2]>>(16*(i%2)));return a;}
template<class D> static D& engine(std::map<std::string,std::unique_ptr<D>>& engines,const std::string& id){auto& p=engines[id];if(!p)p=std::make_unique<D>();return *p;}
void replay_generated_plan(){std::map<std::string,Buffer> values;
std::map<std::string,std::unique_ptr<layer::Matrix>> matrices;
std::map<std::string,std::unique_ptr<layer::Normalizer>> norms;
std::map<std::string,std::unique_ptr<layer::Activation>> activations;
std::map<std::string,std::unique_ptr<Compact>> vectors;
std::map<std::string,std::unique_ptr<TiledRecurrent>> recurrent;
std::map<std::string,std::unique_ptr<Handoff>> handoffs;
values["epsilon@0:1"]={NativeWord{1u,0u,0u,0u}};
values["x@0:2"]={NativeWord{67109888u,0u,0u,0u}};
values["x@2:2"]={NativeWord{67109888u,0u,0u,0u}};
values["x@4:2"]={NativeWord{67109888u,0u,0u,0u}};
values["x@6:2"]={NativeWord{67109888u,0u,0u,0u}};
values["gamma@0:2"]={NativeWord{67109888u,0u,0u,0u}};
values["gamma@2:2"]={NativeWord{67109888u,0u,0u,0u}};
values["gamma@4:2"]={NativeWord{67109888u,0u,0u,0u}};
values["gamma@6:2"]={NativeWord{67109888u,0u,0u,0u}};
values["w@M_B:0,0,2,2"]={NativeWord{2097168u,0u,0u,0u},NativeWord{4194336u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:0,2,2,2"]={NativeWord{4194352u,0u,0u,0u},NativeWord{8388704u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:0,4,2,2"]={NativeWord{6291536u,0u,0u,0u},NativeWord{12583072u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:0,6,2,2"]={NativeWord{8388720u,0u,0u,0u},NativeWord{16777440u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:2,0,2,2"]={NativeWord{6291504u,0u,0u,0u},NativeWord{8388672u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:2,2,2,2"]={NativeWord{12583056u,0u,0u,0u},NativeWord{16777408u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:2,4,2,2"]={NativeWord{18874608u,0u,0u,0u},NativeWord{25166144u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["w@M_B:2,6,2,2"]={NativeWord{25166160u,0u,0u,0u},NativeWord{33554880u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u},NativeWord{0u,0u,0u,0u}};
values["residual@0:2"]={NativeWord{4293656586u,0u,0u,0u}};
values["residual@2:2"]={NativeWord{4292345886u,0u,0u,0u}};
values["old@0:64"]={NativeWord{4294967169u,4294967170u,0u,0u},NativeWord{4294967170u,4294967172u,0u,0u},NativeWord{4294967171u,4294967174u,0u,0u},NativeWord{4294967172u,4294967176u,0u,0u},NativeWord{4294967173u,4294967178u,0u,0u},NativeWord{4294967174u,4294967180u,0u,0u},NativeWord{4294967175u,4294967182u,0u,0u},NativeWord{4294967176u,4294967184u,0u,0u},NativeWord{4294967177u,4294967186u,0u,0u},NativeWord{4294967178u,4294967188u,0u,0u},NativeWord{4294967179u,4294967190u,0u,0u},NativeWord{4294967180u,4294967192u,0u,0u},NativeWord{4294967181u,4294967194u,0u,0u},NativeWord{4294967182u,4294967196u,0u,0u},NativeWord{4294967183u,4294967198u,0u,0u},NativeWord{4294967184u,4294967200u,0u,0u},NativeWord{4294967185u,4294967202u,0u,0u},NativeWord{4294967186u,4294967204u,0u,0u},NativeWord{4294967187u,4294967206u,0u,0u},NativeWord{4294967188u,4294967208u,0u,0u},NativeWord{4294967189u,4294967210u,0u,0u},NativeWord{4294967190u,4294967212u,0u,0u},NativeWord{4294967191u,4294967214u,0u,0u},NativeWord{4294967192u,4294967216u,0u,0u},NativeWord{4294967193u,4294967218u,0u,0u},NativeWord{4294967194u,4294967220u,0u,0u},NativeWord{4294967195u,4294967222u,0u,0u},NativeWord{4294967196u,4294967224u,0u,0u},NativeWord{4294967197u,4294967226u,0u,0u},NativeWord{4294967198u,4294967228u,0u,0u},NativeWord{4294967199u,4294967230u,0u,0u},NativeWord{4294967200u,4294967232u,0u,0u}};
values["key@0:32"]={NativeWord{4294705146u,4294836220u,4294967294u,65536u},NativeWord{196610u,327684u,4294574086u,4294770683u},NativeWord{4294901757u,65535u,131073u,262147u},NativeWord{393221u,4294705146u,4294836220u,4294967294u}};
values["params@0:2"]={NativeWord{2147483648u,1073741824u,0u,0u}};
values["old@64:64"]={NativeWord{4294967201u,4294967234u,0u,0u},NativeWord{4294967202u,4294967236u,0u,0u},NativeWord{4294967203u,4294967238u,0u,0u},NativeWord{4294967204u,4294967240u,0u,0u},NativeWord{4294967205u,4294967242u,0u,0u},NativeWord{4294967206u,4294967244u,0u,0u},NativeWord{4294967207u,4294967246u,0u,0u},NativeWord{4294967208u,4294967248u,0u,0u},NativeWord{4294967209u,4294967250u,0u,0u},NativeWord{4294967210u,4294967252u,0u,0u},NativeWord{4294967211u,4294967254u,0u,0u},NativeWord{4294967212u,4294967256u,0u,0u},NativeWord{4294967213u,4294967258u,0u,0u},NativeWord{4294967214u,4294967260u,0u,0u},NativeWord{4294967215u,4294967262u,0u,0u},NativeWord{4294967216u,4294967264u,0u,0u},NativeWord{4294967217u,4294967266u,0u,0u},NativeWord{4294967218u,4294967268u,0u,0u},NativeWord{4294967219u,4294967270u,0u,0u},NativeWord{4294967220u,4294967272u,0u,0u},NativeWord{4294967221u,4294967274u,0u,0u},NativeWord{4294967222u,4294967276u,0u,0u},NativeWord{4294967223u,4294967278u,0u,0u},NativeWord{4294967224u,4294967280u,0u,0u},NativeWord{4294967225u,4294967282u,0u,0u},NativeWord{4294967226u,4294967284u,0u,0u},NativeWord{4294967227u,4294967286u,0u,0u},NativeWord{4294967228u,4294967288u,0u,0u},NativeWord{4294967229u,4294967290u,0u,0u},NativeWord{4294967230u,4294967292u,0u,0u},NativeWord{4294967231u,4294967294u,0u,0u},NativeWord{4294967232u,0u,0u,0u}};
values["key@32:32"]={NativeWord{65536u,196610u,327684u,4294574086u},NativeWord{4294770683u,4294901757u,65535u,131073u},NativeWord{262147u,393221u,4294705146u,4294836220u},NativeWord{4294967294u,65536u,196610u,327684u}};
values["old@128:64"]={NativeWord{4294967233u,2u,0u,0u},NativeWord{4294967234u,4u,0u,0u},NativeWord{4294967235u,6u,0u,0u},NativeWord{4294967236u,8u,0u,0u},NativeWord{4294967237u,10u,0u,0u},NativeWord{4294967238u,12u,0u,0u},NativeWord{4294967239u,14u,0u,0u},NativeWord{4294967240u,16u,0u,0u},NativeWord{4294967241u,18u,0u,0u},NativeWord{4294967242u,20u,0u,0u},NativeWord{4294967243u,22u,0u,0u},NativeWord{4294967244u,24u,0u,0u},NativeWord{4294967245u,26u,0u,0u},NativeWord{4294967246u,28u,0u,0u},NativeWord{4294967247u,30u,0u,0u},NativeWord{4294967248u,32u,0u,0u},NativeWord{4294967249u,34u,0u,0u},NativeWord{4294967250u,36u,0u,0u},NativeWord{4294967251u,38u,0u,0u},NativeWord{4294967252u,40u,0u,0u},NativeWord{4294967253u,42u,0u,0u},NativeWord{4294967254u,44u,0u,0u},NativeWord{4294967255u,46u,0u,0u},NativeWord{4294967256u,48u,0u,0u},NativeWord{4294967257u,50u,0u,0u},NativeWord{4294967258u,52u,0u,0u},NativeWord{4294967259u,54u,0u,0u},NativeWord{4294967260u,56u,0u,0u},NativeWord{4294967261u,58u,0u,0u},NativeWord{4294967262u,60u,0u,0u},NativeWord{4294967263u,62u,0u,0u},NativeWord{4294967264u,64u,0u,0u}};
values["key@64:32"]={NativeWord{4294574086u,4294770683u,4294901757u,65535u},NativeWord{131073u,262147u,393221u,4294705146u},NativeWord{4294836220u,4294967294u,65536u,196610u},NativeWord{327684u,4294574086u,4294770683u,4294901757u}};
values["old@192:64"]={NativeWord{4294967265u,66u,0u,0u},NativeWord{4294967266u,68u,0u,0u},NativeWord{4294967267u,70u,0u,0u},NativeWord{4294967268u,72u,0u,0u},NativeWord{4294967269u,74u,0u,0u},NativeWord{4294967270u,76u,0u,0u},NativeWord{4294967271u,78u,0u,0u},NativeWord{4294967272u,80u,0u,0u},NativeWord{4294967273u,82u,0u,0u},NativeWord{4294967274u,84u,0u,0u},NativeWord{4294967275u,86u,0u,0u},NativeWord{4294967276u,88u,0u,0u},NativeWord{4294967277u,90u,0u,0u},NativeWord{4294967278u,92u,0u,0u},NativeWord{4294967279u,94u,0u,0u},NativeWord{4294967280u,96u,0u,0u},NativeWord{4294967281u,98u,0u,0u},NativeWord{4294967282u,100u,0u,0u},NativeWord{4294967283u,102u,0u,0u},NativeWord{4294967284u,104u,0u,0u},NativeWord{4294967285u,106u,0u,0u},NativeWord{4294967286u,108u,0u,0u},NativeWord{4294967287u,110u,0u,0u},NativeWord{4294967288u,112u,0u,0u},NativeWord{4294967289u,114u,0u,0u},NativeWord{4294967290u,116u,0u,0u},NativeWord{4294967291u,118u,0u,0u},NativeWord{4294967292u,120u,0u,0u},NativeWord{4294967293u,122u,0u,0u},NativeWord{4294967294u,124u,0u,0u},NativeWord{4294967295u,126u,0u,0u},NativeWord{0u,128u,0u,0u}};
values["key@96:32"]={NativeWord{65535u,131073u,262147u,393221u},NativeWord{4294705146u,4294836220u,4294967294u,65536u},NativeWord{196610u,327684u,4294574086u,4294770683u},NativeWord{4294901757u,65535u,131073u,262147u}};
values["rx@0:2"]={NativeWord{800u,4294966396u,0u,0u}};
values["query@0:32"]={NativeWord{4294574072u,4294705146u,4294836220u,4294967294u},NativeWord{65536u,196610u,327684u,458758u},NativeWord{4294443016u,4294639609u,4294770683u,4294901757u},NativeWord{65535u,131073u,262147u,393221u}};
values["query@32:32"]={NativeWord{524295u,4294574072u,4294705146u,4294836220u},NativeWord{4294967294u,65536u,196610u,327684u},NativeWord{458758u,4294443016u,4294639609u,4294770683u},NativeWord{4294901757u,65535u,131073u,262147u}};
values["query@64:32"]={NativeWord{393221u,524295u,4294574072u,4294705146u},NativeWord{4294836220u,4294967294u,65536u,196610u},NativeWord{327684u,458758u,4294443016u,4294639609u},NativeWord{4294770683u,4294901757u,65535u,131073u}};
values["query@96:32"]={NativeWord{262147u,393221u,524295u,4294574072u},NativeWord{4294705146u,4294836220u,4294967294u,65536u},NativeWord{196610u,327684u,458758u,4294443016u},NativeWord{4294639609u,4294770683u,4294901757u,65535u}};
{ // norm@row0:begin
const Buffer& a0=values.at("epsilon@0:1");
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(0);c.mode=NCommand::Mode(1);c.count=0;
c.epsilon=a0.at(0)[0];
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
}
{ // norm@row0:stats0
const Buffer& a0=values.at("x@0:2");
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(1);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
}
{ // norm@row0:stats2
const Buffer& a0=values.at("x@2:2");
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(1);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
}
{ // norm@row0:stats4
const Buffer& a0=values.at("x@4:2");
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(1);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
}
{ // norm@row0:stats6
const Buffer& a0=values.at("x@6:2");
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(1);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
}
{ // norm@row0:finalize
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(2);c.mode=NCommand::Mode(1);c.count=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
}
{ // norm@row0:replay0
const Buffer& a0=values.at("x@0:2");
const Buffer& a1=values.at("gamma@0:2");
Buffer out0;
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(5);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
c.gamma=raw16(a1);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
out0.push_back(lanes16(reply));
layer::require(out0.size()==1,"generated output extent");values["normalized@0:2"]=out0;
}
{ // norm@row0:replay2
const Buffer& a0=values.at("x@2:2");
const Buffer& a1=values.at("gamma@2:2");
Buffer out0;
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(5);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
c.gamma=raw16(a1);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
out0.push_back(lanes16(reply));
layer::require(out0.size()==1,"generated output extent");values["normalized@2:2"]=out0;
}
{ // norm@row0:replay4
const Buffer& a0=values.at("x@4:2");
const Buffer& a1=values.at("gamma@4:2");
Buffer out0;
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(5);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
c.gamma=raw16(a1);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
out0.push_back(lanes16(reply));
layer::require(out0.size()==1,"generated output extent");values["normalized@4:2"]=out0;
}
{ // norm@row0:replay6
const Buffer& a0=values.at("x@6:2");
const Buffer& a1=values.at("gamma@6:2");
Buffer out0;
auto& unit=engine(norms,"U0.N");NCommand c;
c.op=NCommand::Op(5);c.mode=NCommand::Mode(1);c.count=2;
auto a=raw16(a0);for(unsigned i=0;i<8;++i)c.data[i]=uint16_t(a[i]);
c.gamma=raw16(a1);
auto reply=unit.execute(c);layer::require(!reply.error,"generated N command");
out0.push_back(lanes16(reply));
layer::require(out0.size()==1,"generated output extent");values["normalized@6:2"]=out0;
}
{ // project@0,0,k0
const Buffer& a0=values.at("normalized@0:2");
const Buffer& a1=values.at("w@M_B:0,0,2,2");
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::Scale;
c.coefficient=1;c.shift=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
}
{ // project@0,0,k2
const Buffer& a0=values.at("normalized@2:2");
const Buffer& a1=values.at("w@M_B:0,2,2,2");
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=false;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
}
{ // project@0,0,k4
const Buffer& a0=values.at("normalized@4:2");
const Buffer& a1=values.at("w@M_B:0,4,2,2");
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=false;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
}
{ // project@0,0,k6
const Buffer& a0=values.at("normalized@6:2");
const Buffer& a1=values.at("w@M_B:0,6,2,2");
Buffer out0;
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=false;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::ReadFinal;
c.half=0;c.width=16;c.shift=10;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
out0.push_back(lanes32(reply));
}
layer::require(out0.size()==1,"generated output extent");values["project:native-s32@0:2"]=out0;
}
{ // project@0,0:pack
const Buffer& a0=values.at("project:native-s32@0:2");
Buffer out0;
auto& unit=engine(vectors,"F0.E");
out0.push_back(lanes16(unit.execute(13,0,raw16(a0))));
layer::require(out0.size()==1,"generated output extent");values["projected@0:2"]=out0;
}
{ // act@0
const Buffer& a0=values.at("projected@0:2");
Buffer out0;
auto& unit=engine(activations,"F0.G");GCommand c;
c.function=GCommand::Function(0);c.gated=false;
auto x=raw16(a0);for(unsigned i=0;i<2;++i)c.x[i]=x[i];
out0.push_back(lanes16(unit.execute(c)));
layer::require(out0.size()==1,"generated output extent");values["activated@0:2"]=out0;
}
{ // add@0
const Buffer& a0=values.at("activated@0:2");
const Buffer& a1=values.at("residual@0:2");
Buffer out0;
auto& unit=engine(vectors,"F0.E");
out0.push_back(lanes16(unit.execute(0,0,raw16(a0),raw16(a1))));
layer::require(out0.size()==1,"generated output extent");values["sum@0:2"]=out0;
}
{ // finish@0
const Buffer& a0=values.at("sum@0:2");
Buffer out0;
out0=engine(handoffs,"J0.T").transfer(a0);
layer::require(out0.size()==1,"generated output extent");values["out@0:2"]=out0;
}
{ // project@0,2,k0
const Buffer& a0=values.at("normalized@0:2");
const Buffer& a1=values.at("w@M_B:2,0,2,2");
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::Scale;
c.coefficient=1;c.shift=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
}
{ // project@0,2,k2
const Buffer& a0=values.at("normalized@2:2");
const Buffer& a1=values.at("w@M_B:2,2,2,2");
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=false;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
}
{ // project@0,2,k4
const Buffer& a0=values.at("normalized@4:2");
const Buffer& a1=values.at("w@M_B:2,4,2,2");
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=false;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
}
{ // project@0,2,k6
const Buffer& a0=values.at("normalized@6:2");
const Buffer& a1=values.at("w@M_B:2,6,2,2");
Buffer out0;
auto& unit=engine(matrices,"P0.M");
{MCommand c;
c.op=MCommand::Op::LoadA;
for(unsigned i=0;i<1;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a0.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(0+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=0;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::LoadB;
for(unsigned i=0;i<4;++i)for(unsigned j=0;j<4;++j)c.data[i*2+j/2]|=uint64_t(a1.at(4+i)[j])<<(32*(j%2));
c.wide_a=c.wide_b=true;
c.half=1;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::Execute;
c.wide_a=c.wide_b=true;c.rows=1;c.tiles=1;c.columns=2;c.last_k=2;c.clear=false;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
}
{MCommand c;
c.op=MCommand::Op::ReadFinal;
c.half=0;c.width=16;c.shift=10;
auto reply=unit.execute(c);layer::require(!reply.error,"generated M command");
out0.push_back(lanes32(reply));
}
layer::require(out0.size()==1,"generated output extent");values["project:native-s32@2:2"]=out0;
}
{ // project@0,2:pack
const Buffer& a0=values.at("project:native-s32@2:2");
Buffer out0;
auto& unit=engine(vectors,"J0.E");
out0.push_back(lanes16(unit.execute(13,0,raw16(a0))));
layer::require(out0.size()==1,"generated output extent");values["projected@2:2"]=out0;
}
{ // act@2
const Buffer& a0=values.at("projected@2:2");
Buffer out0;
auto& unit=engine(activations,"F0.G");GCommand c;
c.function=GCommand::Function(0);c.gated=false;
auto x=raw16(a0);for(unsigned i=0;i<2;++i)c.x[i]=x[i];
out0.push_back(lanes16(unit.execute(c)));
layer::require(out0.size()==1,"generated output extent");values["activated@2:2"]=out0;
}
{ // add@2
const Buffer& a0=values.at("activated@2:2");
const Buffer& a1=values.at("residual@2:2");
Buffer out0;
auto& unit=engine(vectors,"F0.E");
out0.push_back(lanes16(unit.execute(0,0,raw16(a0),raw16(a1))));
layer::require(out0.size()==1,"generated output extent");values["sum@2:2"]=out0;
}
{ // finish@2
const Buffer& a0=values.at("sum@2:2");
Buffer out0;
out0=engine(handoffs,"J0.T").transfer(a0);
layer::require(out0.size()==1,"generated output extent");values["out@2:2"]=out0;
}
{ // recurrent:begin
auto& unit=engine(recurrent,"C0.R");
unit.pass(7);
}
{ // recurrent:predict0
const Buffer& a0=values.at("old@0:64");
const Buffer& a1=values.at("key@0:32");
const Buffer& a2=values.at("params@0:2");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.predict(state,key,a2.at(0)[0],true);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["recurrent:predict0:decayed"]=out0;
}
{ // recurrent:predict32
const Buffer& a0=values.at("old@64:64");
const Buffer& a1=values.at("key@32:32");
const Buffer& a2=values.at("params@0:2");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.predict(state,key,a2.at(0)[0],false);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["recurrent:predict32:decayed"]=out0;
}
{ // recurrent:predict64
const Buffer& a0=values.at("old@128:64");
const Buffer& a1=values.at("key@64:32");
const Buffer& a2=values.at("params@0:2");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.predict(state,key,a2.at(0)[0],false);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["recurrent:predict64:decayed"]=out0;
}
{ // recurrent:predict96
const Buffer& a0=values.at("old@192:64");
const Buffer& a1=values.at("key@96:32");
const Buffer& a2=values.at("params@0:2");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.predict(state,key,a2.at(0)[0],false);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["recurrent:predict96:decayed"]=out0;
}
{ // recurrent:error
const Buffer& a0=values.at("rx@0:2");
const Buffer& a1=values.at("params@0:2");
auto& unit=engine(recurrent,"C0.R");
std::array<int32_t,8> x{};for(unsigned i=0;i<2;++i)x[i]=int32_t(a0.at(i/4)[i%4]);unit.error(x,a1.at(0)[1]);
}
{ // recurrent:update0
const Buffer& a0=values.at("recurrent:predict0:decayed");
const Buffer& a1=values.at("key@0:32");
const Buffer& a2=values.at("query@0:32");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
std::vector<int16_t> query(32);for(unsigned r=0;r<32;++r)query[r]=int16_t(a2.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.update(state,key,query,true);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["next@0:64"]=out0;
}
{ // recurrent:update32
const Buffer& a0=values.at("recurrent:predict32:decayed");
const Buffer& a1=values.at("key@32:32");
const Buffer& a2=values.at("query@32:32");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
std::vector<int16_t> query(32);for(unsigned r=0;r<32;++r)query[r]=int16_t(a2.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.update(state,key,query,false);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["next@64:64"]=out0;
}
{ // recurrent:update64
const Buffer& a0=values.at("recurrent:predict64:decayed");
const Buffer& a1=values.at("key@64:32");
const Buffer& a2=values.at("query@64:32");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
std::vector<int16_t> query(32);for(unsigned r=0;r<32;++r)query[r]=int16_t(a2.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.update(state,key,query,false);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["next@128:64"]=out0;
}
{ // recurrent:update96
const Buffer& a0=values.at("recurrent:predict96:decayed");
const Buffer& a1=values.at("key@96:32");
const Buffer& a2=values.at("query@96:32");
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
TiledRecurrent::State state(32);for(unsigned r=0;r<32;++r)for(unsigned c=0;c<2;++c)state[r][c]=int32_t(a0.at(r*1+c/4)[c%4]);
std::vector<int16_t> key(32);for(unsigned r=0;r<32;++r)key[r]=int16_t(a1.at(r/8)[(r%8)/2]>>(16*(r%2)));
std::vector<int16_t> query(32);for(unsigned r=0;r<32;++r)query[r]=int16_t(a2.at(r/8)[(r%8)/2]>>(16*(r%2)));
auto next=unit.update(state,key,query,false);
for(unsigned r=0;r<32;++r)for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(next[r][half*4+i]);out0.push_back(word);}
layer::require(out0.size()==32,"generated output extent");values["next@192:64"]=out0;
}
{ // recurrent:finish
Buffer out0;
auto& unit=engine(recurrent,"C0.R");
auto x=unit.pass(5);for(unsigned half=0;half<1;++half){NativeWord word{};for(unsigned i=0;i<4&&half*4+i<2;++i)word[i]=uint32_t(x[half*4+i]);out0.push_back(word);}
layer::require(out0.size()==1,"generated output extent");values["ry@0:2"]=out0;
}
{ // narrow@0
const Buffer& a0=values.at("ry@0:2");
Buffer out0;
auto& unit=engine(vectors,"C0.E");
out0.push_back(lanes16(unit.execute(13,6,raw16(a0))));
layer::require(out0.size()==1,"generated output extent");values["small@0:2"]=out0;
}
NEngine nref;NCommand nc;nc.mode=NCommand::Mode::RMS;nc.epsilon=1;nref.execute(nc);
nc.op=NCommand::Op::Stats;nc.count=8;nc.data.fill(1024);nref.execute(nc);
nc.op=NCommand::Op::Finalize;nref.execute(nc);nc.op=NCommand::Op::NormReplay;nc.gamma.fill(1024);auto normalized=nref.execute(nc);
std::array<int16_t,4> projected{};for(unsigned c=0;c<4;++c){blocks::Wide sum=0;for(unsigned k=0;k<8;++k)sum+=normalized.lane[k]*int((k+1)*(c+1)*16);projected[c]=int16_t(blocks::rne(sum,10));}
std::array<int16_t,4> expected{};GEngine gref;const int residual[4]={10,-20,30,-40};
for(unsigned p=0;p<2;++p){GCommand gc;gc.x={projected[p*2],projected[p*2+1]};auto r=gref.execute(gc);for(unsigned i=0;i<2;++i)expected[p*2+i]=int16_t(r.lane[i]+residual[p*2+i]);}
REngine rref;RCommand rc;rc.op=RCommand::Op::Open;rc.length=128;rref.execute(rc);
for(unsigned row=0;row<128;++row){rc=RCommand{};rc.op=RCommand::Op::StateRow;rc.index=row;rc.values[0]=int32_t(row+1)-128;rc.values[1]=int32_t((row+1)*2)-128;rref.execute(rc);rc.op=RCommand::Op::Key;rc.coefficients[0]=int16_t(int(row%13)-6);rref.execute(rc);rc.op=RCommand::Op::Query;rc.coefficients[0]=int16_t(int(row%17)-8);rref.execute(rc);}
rc=RCommand{};rc.op=RCommand::Op::X;rc.values[0]=800;rc.values[1]=-900;rref.execute(rc);
rc=RCommand{};rc.op=RCommand::Op::Parameters;rc.decay=0x80000000;rc.beta=0x40000000;rref.execute(rc);
rc=RCommand{};rc.op=RCommand::Op::Execute;layer::require(!rref.execute(rc).error,"whole R oracle");rc.op=RCommand::Op::ReadOutput;auto ry=rref.execute(rc);rc.op=RCommand::Op::Commit;rref.execute(rc);
for(unsigned i=0;i<2;++i)layer::require(int16_t(values.at("out@0:2").at(0)[i/2]>>(16*(i%2)))==expected[0+i],"whole mixed output");
for(unsigned i=0;i<2;++i)layer::require(int16_t(values.at("out@2:2").at(0)[i/2]>>(16*(i%2)))==expected[2+i],"whole mixed output");
for(unsigned row=0;row<32;++row){rc=RCommand{};rc.op=RCommand::Op::ReadState;rc.index=0+row;auto state=rref.execute(rc);for(unsigned i=0;i<2;++i)layer::require(int32_t(values.at("next@0:64").at(row)[i])==state.lane[i],"whole next state");}
for(unsigned row=0;row<32;++row){rc=RCommand{};rc.op=RCommand::Op::ReadState;rc.index=32+row;auto state=rref.execute(rc);for(unsigned i=0;i<2;++i)layer::require(int32_t(values.at("next@64:64").at(row)[i])==state.lane[i],"whole next state");}
for(unsigned row=0;row<32;++row){rc=RCommand{};rc.op=RCommand::Op::ReadState;rc.index=64+row;auto state=rref.execute(rc);for(unsigned i=0;i<2;++i)layer::require(int32_t(values.at("next@128:64").at(row)[i])==state.lane[i],"whole next state");}
for(unsigned row=0;row<32;++row){rc=RCommand{};rc.op=RCommand::Op::ReadState;rc.index=96+row;auto state=rref.execute(rc);for(unsigned i=0;i<2;++i)layer::require(int32_t(values.at("next@192:64").at(row)[i])==state.lane[i],"whole next state");}
for(unsigned i=0;i<2;++i)layer::require(int16_t(values.at("small@0:2").at(0)[i/2]>>(16*(i%2)))==int16_t(blocks::rne(ry.lane[i],6)),"whole R converted output");
std::cout<<"GENERATED_NATIVE_PLAN_PASS tasks=38 outputs=7\n";}
