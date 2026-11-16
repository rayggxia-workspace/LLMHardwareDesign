// Fast literal numeric interpreter, not a cycle/energy simulator or hardware.
// Every streamed scalar is staged through finite SRAM; one <=8x8 M context
// survives full K. Packed/flag vectors below explicitly represent external RAM.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

using Word=std::array<int16_t,8>;
enum Metric { READS,WRITES,ZEROS,TILES,DB,DA,DS,DF,DX,FINAL,CANON,ESIGN,
              PACKED,FLAGS,SI,SB,SX,SF,SS,PHIGH,EHIGH,TMPHIGH,METRICS };
using Counts=std::array<uint64_t,METRICS>;

template<class T> void input(T* p,size_t count) {
    if (count && std::fread(p,sizeof(T),count,stdin)!=count) throw std::runtime_error("truncated tile payload");
}
template<class T> void output(const T* p,size_t count) {
    if (count && std::fwrite(p,sizeof(T),count,stdout)!=count) throw std::runtime_error("tile output write failed");
}
size_t extent(uint64_t a,uint64_t b) {
    if (b && a>std::numeric_limits<size_t>::max()/b) throw std::runtime_error("external extent overflow");
    return size_t(a*b);
}
struct SRAM {
    std::vector<Word> words;
    std::vector<bool> valid;
    size_t high=0;
    explicit SRAM(size_t capacity):words(capacity),valid(capacity,false) {}
    void write_ack(size_t address,const Word& word) {
        if(address>=words.size())throw std::runtime_error("finite SRAM overflow");
        words[address]=word;valid[address]=true;high=std::max(high,address+1);
    }
    const Word& read(size_t address) const {
        if(address>=words.size()||!valid[address])throw std::runtime_error("read unwritten SRAM");
        return words[address];
    }
};
Word scalar(int16_t value) {Word w{};w[0]=value;return w;}
int32_t final32(int64_t value,unsigned shift) {
    // Magnitude is safe: admitted decomposed full-K bound excludes INT64_MIN.
    if(shift) {
        const uint64_t magnitude=value<0?uint64_t(-value):uint64_t(value);
        const uint64_t base=magnitude>>shift,rem=magnitude&((uint64_t(1)<<shift)-1);
        const uint64_t half=uint64_t(1)<<(shift-1);
        const int64_t rounded=int64_t(base+(rem>half||(rem==half&&(base&1))));
        value=value<0?-rounded:rounded;
    }
    return int32_t(std::max<int64_t>(INT32_MIN,std::min<int64_t>(INT32_MAX,value)));
}
void put32(Word& word,unsigned lane,int32_t value) {
    const uint32_t bits=uint32_t(value);
    word[lane*2]=int16_t(bits&65535);word[lane*2+1]=int16_t(bits>>16);
}
int32_t get32(const Word& word) {
    const uint32_t bits=uint32_t(uint16_t(word[0]))|(uint32_t(uint16_t(word[1]))<<16);
    return bits<=uint32_t(INT32_MAX)?int32_t(bits):int32_t(int64_t(bits)-(int64_t(1)<<32));
}

void run(const std::array<uint32_t,11>& h) {
    const uint32_t rows=h[2],cols=h[3],k=h[4],rt=h[5],ct=h[6],shift=h[7];
    if(h[0]!=0x54494c45||(h[1]!=1&&h[1]!=2)||!rows||!cols||!k||!rt||!ct||rt>8||ct>8||shift>63||
       rt>rows||ct>cols||k>uint64_t(INT64_MAX)/((uint64_t(1)<<31)+131072)/(uint64_t(1)<<15))
        throw std::runtime_error("invalid tile protocol/shape/accumulator bound");
    std::array<Word,9> constants{};input(constants.data(),constants.size());
    std::vector<int16_t> prepared(extent(extent(rows,k),3));input(prepared.data(),prepared.size());
    std::vector<int16_t> weights(extent(k,cols));input(weights.data(),weights.size());
    // Reject malformed prepared planes before assuming the conservative bound.
    for(size_t i=0;i<prepared.size();i+=3) {
        const int64_t lo=prepared[i],hi=prepared[i+1],flag=prepared[i+2];
        const int64_t value=lo+65536*(hi+flag);
        if(flag!=int(lo<0)||value<INT32_MIN||value>INT32_MAX)
            throw std::runtime_error("invalid prepared S32 component identity");
    }
    SRAM p(h[8]),e(h[9]);Counts counts{};
    const bool materialized=h[1]==2;
    if(materialized&&ct<=1)throw std::runtime_error("materialized protocol needs E conversion");
    auto load=[&](SRAM& s,size_t a,const Word& w){s.write_ack(a,w);++counts[READS];};
    auto store=[&](const SRAM& s,size_t a){++counts[WRITES];return s.read(a);};
    for(unsigned i=0;i<8;++i) {load(p,i,constants[0]);load(p,16+i,constants[0]);}
    counts[ZEROS]=16;
    std::vector<int64_t> raw(extent(rows,cols));std::vector<int32_t> result(raw.size());
    struct Pending {uint32_t rr,cc;unsigned r,n;size_t offset;};
    std::vector<Pending> pending;
    std::vector<Word> all_packed,all_flags;
    auto signs=[&](const std::vector<Word>& packed) {
        std::vector<Word> flags;
        for(const Word& word:packed) {
            load(e,0,word);Word flag{};
            for(unsigned j=0;j<8;++j)flag[j]=e.read(0)[j]<0?-1:0;
            e.write_ack(1,flag);flags.push_back(store(e,1));++counts[ESIGN];
        }
        counts[TMPHIGH]=std::max<uint64_t>(counts[TMPHIGH],packed.size()+flags.size());
        if(counts[TMPHIGH]>h[10])throw std::runtime_error("external temporary region overflow");
        counts[FLAGS]+=flags.size();return flags;
    };
    auto scatter=[&](const Pending& grid,const std::vector<Word>& packed,const std::vector<Word>& flags) {
        const unsigned stride=(grid.n+3)/4;
        for(unsigned i=0;i<grid.r;++i)for(unsigned j=0;j<grid.n;++j) {
            const size_t index=grid.offset+i*stride+j/4;const unsigned lane=2*(j%4);int64_t sum=0;
            for(unsigned component=0;component<3;++component) {
                load(p,0,component==2?flags.at(index):packed.at(index));
                load(p,16,constants[1+lane+(component==1)]);
                int64_t partial=0;
                for(unsigned v=0;v<8;++v)partial+=int64_t(p.read(0)[v])*p.read(16)[v];
                sum+=partial*(component==0?1:component==1?65536:-65536);
                ++counts[SI];++counts[SB];++counts[SX];++counts[SF];++counts[SS];
            }
            Word word{};put32(word,0,final32(sum,0));p.write_ack(512+i*8+j,word);
            result[size_t(grid.rr+i)*cols+grid.cc+j]=get32(store(p,512+i*8+j));++counts[FINAL];++counts[CANON];
        }
    };
    for(uint32_t rr=0;rr<rows;rr+=rt) for(uint32_t cc=0;cc<cols;cc+=ct) {
        const unsigned r=std::min(rt,rows-rr),n=std::min(ct,cols-cc);++counts[TILES];
        std::array<int64_t,64> acc{};std::array<int16_t,8> bbank{};
        for(uint32_t kk=0;kk<k;++kk) {
            for(unsigned j=0;j<n;++j)load(p,16+j,scalar(weights[size_t(kk)*cols+cc+j]));
            counts[DB]+=n;
            for(unsigned component=0;component<3;++component) {
                for(unsigned i=0;i<r;++i)load(p,i,scalar(prepared[(size_t(rr+i)*k+kk)*3+component]));
                counts[DA]+=r;
                if(component==0)for(unsigned j=0;j<n;++j)bbank[j]=p.read(16+j)[0];
                for(unsigned i=0;i<r;++i) {
                    const int64_t a=int64_t(p.read(i)[0])*(component?65536:1);
                    for(unsigned j=0;j<n;++j)acc[i*8+j]+=a*bbank[j];
                }
                ++counts[DS];++counts[DF];++counts[DX];
            }
        }
        for(unsigned i=0;i<r;++i)for(unsigned j=0;j<n;++j)raw[size_t(rr+i)*cols+cc+j]=acc[i*8+j];
        if(n==1) {
            for(unsigned i=0;i<r;++i) {
                Word word{};put32(word,0,final32(acc[i*8],shift));p.write_ack(512+i*8,word);
                result[size_t(rr+i)*cols+cc]=get32(store(p,512+i*8));
            }
            counts[FINAL]+=r;counts[CANON]+=r;continue;
        }
        std::vector<Word> packed; // Explicit external temporary objects.
        for(unsigned i=0;i<r;++i)for(unsigned first=0;first<n;first+=4) {
            Word word{};
            for(unsigned j=first;j<std::min(n,first+4);++j)put32(word,j-first,final32(acc[i*8+j],shift));
            p.write_ack(96+packed.size(),word);packed.push_back(store(p,96+packed.size()));++counts[FINAL];
        }
        counts[PACKED]+=packed.size();
        if(materialized) {
            pending.push_back({rr,cc,r,n,all_packed.size()});
            all_packed.insert(all_packed.end(),packed.begin(),packed.end());
        } else {
            const auto flags=signs(packed);scatter({rr,cc,r,n,0},packed,flags);
        }
    }
    if(materialized) {
        all_flags=signs(all_packed);
        for(unsigned i=0;i<8;++i){load(p,i,constants[0]);load(p,16+i,constants[0]);}
        counts[ZEROS]+=16;
        for(const auto& grid:pending)scatter(grid,all_packed,all_flags);
    }
    counts[PHIGH]=p.high;counts[EHIGH]=e.high;
    const std::array<uint32_t,2> reply{{0,METRICS}};
    output(reply.data(),reply.size());output(counts.data(),counts.size());output(raw.data(),raw.size());
    output(result.data(),result.size());std::fflush(stdout);
}
int main() {
    const uint32_t endian=1;
    if(*reinterpret_cast<const uint8_t*>(&endian)!=1)return 2;
    try {
        for(;;) {
            std::array<uint32_t,11> header{};
            const size_t got=std::fread(header.data(),sizeof(uint32_t),header.size(),stdin);
            if(!got&&std::feof(stdin))return 0;
            if(got!=header.size())throw std::runtime_error("truncated tile header");
            run(header);
        }
    } catch(const std::exception& error) {
        const std::string message=error.what();const std::array<uint32_t,2> reply{{1,uint32_t(message.size())}};
        output(reply.data(),reply.size());output(message.data(),message.size());std::fflush(stdout);
        std::fprintf(stderr,"native tile replay: %s\n",error.what());return 1;
    }
}
