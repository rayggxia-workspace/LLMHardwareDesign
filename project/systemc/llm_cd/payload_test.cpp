#include "payload.hpp"
#include <iostream>
class Test:public sc_core::sc_module {
    llm_cd::Payload payload_{"payload"};unsigned finished_=0;
    void sender(unsigned seed) {
        for(unsigned count: {1u,15u,16u,17u,257u,16384u,32771u}) {
            std::vector<uint8_t> input(count);
            for(unsigned i=0;i<count;++i)input[i]=uint8_t(i*71+seed);
            if(payload_.exchange(input)!=input)throw std::runtime_error("payload test");
        }
        if(++finished_==3) {
            if(payload_.windows!=27)throw std::runtime_error("finite window count");
            passed=true;std::cout<<"CD_PAYLOAD_PASS windows="<<payload_.windows
                <<" words="<<payload_.words<<" bursts="<<payload_.burst_count<<"\n";sc_core::sc_stop();
        }
    }
    void a(){sender(1);}void b(){sender(2);}void c(){sender(3);}
    void watchdog(){sc_core::wait(10,sc_core::SC_MS);sc_core::sc_stop();}
  public:
    bool passed=false;SC_HAS_PROCESS(Test);
    explicit Test(sc_core::sc_module_name name):sc_module(name){SC_THREAD(a);SC_THREAD(b);SC_THREAD(c);SC_THREAD(watchdog);}
};
int sc_main(int,char**){Test t{"test"};sc_core::sc_start();return t.passed?0:1;}
