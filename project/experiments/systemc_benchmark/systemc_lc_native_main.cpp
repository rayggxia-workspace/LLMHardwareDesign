// Execute the accepted control/native RTL under the actual SystemC kernel.
// This is component calibration, not a scalable whole-model timing model.
#include <systemc>
#include <verilated.h>
#include "Vtb_native_pair.h"
#include <iostream>

int sc_main(int argc, char** argv) {
    sc_core::sc_set_time_resolution(1, sc_core::SC_PS);
    Verilated::commandArgs(argc, argv);
    Vtb_native_pair top{"top"};
    // Verilog $finish sets Verilator's flag; it does not stop SystemC's
    // independent delayed watchdog. Bound each kernel advance and honor it.
    while (!Verilated::gotFinish())
        sc_core::sc_start(1, sc_core::SC_NS);
    sc_core::sc_stop();
    top.final();
    if (!Verilated::gotFinish()) {
        std::cerr << "SystemC ended without the native completion checks\n";
        return 1;
    }
    std::cout << "PASS actual_SystemC_kernel version=" << sc_core::sc_version()
              << " stopped_at=" << sc_core::sc_time_stamp() << '\n';
    return 0;
}
