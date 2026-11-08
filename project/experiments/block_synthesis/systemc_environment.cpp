// Dependency/kernel check only. This is not a calibrated hardware model.
#include <systemc>
#include <iostream>

SC_MODULE(EnvironmentCheck) {
    sc_core::sc_fifo<int> fifo{"fifo",1};
    int sum=0, received=0;
    void producer() { for (int i=1;i<=3;++i) fifo.write(i); }
    void consumer() {
        for (int i=0;i<3;++i) {
            wait(5,sc_core::SC_NS);
            sum+=fifo.read(); ++received;
        }
        sc_core::sc_stop();
    }
    SC_CTOR(EnvironmentCheck) { SC_THREAD(producer); SC_THREAD(consumer); }
};

int sc_main(int,char**) {
    EnvironmentCheck check{"check"};
    sc_core::sc_start();
    if (check.received!=3 || check.sum!=6 || sc_core::sc_time_stamp()!=sc_core::sc_time(15,sc_core::SC_NS)) return 2;
    std::cout << "SYSTEMC_ENV_PASS version=" << sc_core::sc_version()
              << " time=" << sc_core::sc_time_stamp() << " fifo_depth=1 received=3\n";
    return 0;
}
