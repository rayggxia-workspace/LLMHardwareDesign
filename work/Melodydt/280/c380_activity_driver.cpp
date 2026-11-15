#include "Vtest_native_attention_core_scope.h"
#include "verilated.h"
#include "verilated_fst_c.h"

#include <cstdint>
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char** argv) {
    const std::string output_arg = "+DDR_OUTPUT=";
    std::string output;
    for (int index = 1; index < argc; ++index) {
        const std::string arg = argv[index];
        if (arg.compare(0, output_arg.size(), output_arg) == 0) {
            output = arg.substr(output_arg.size());
        }
    }
    if (output.empty()) {
        std::cerr << "C380 activity requires the original DDR_OUTPUT path\n";
        return 1;
    }

    auto context = std::make_unique<VerilatedContext>();
    context->commandArgs(argc, argv);
    context->traceEverOn(true);
    auto top = std::make_unique<Vtest_native_attention_core_scope>(context.get());
    VerilatedFstC trace;
    top->trace(&trace, 4);
    constexpr uint32_t first_callback = 4096;
    constexpr uint64_t window_ps = 20480000;
    uint64_t first_ps = 0;
    bool capturing = false;
    bool finished = false;
    while (!context->gotFinish()) {
        top->eval();
        const uint64_t now_ps = context->time();
        if (!capturing && !finished && top->sample_kv_callbacks >= first_callback) {
            first_ps = now_ps;
            trace.open((output + "/attention.fst").c_str());
            capturing = true;
        }
        if (capturing) {
            trace.dump(now_ps);
            if (now_ps >= first_ps + window_ps) {
                trace.close();
                capturing = false;
                finished = true;
                std::cout << "ACTIVITY_WINDOW start_ps=" << first_ps << " end_ps=" << now_ps
                          << " start_callback=" << first_callback
                          << " end_callback=" << top->sample_kv_callbacks << '\n';
            }
        }
        if (!top->eventsPending()) {
            break;
        }
        context->time(top->nextTimeSlot());
    }
    top->final();
    if (!context->gotFinish() || !finished) {
        std::cerr << "C380 simulation or bounded activity capture did not finish\n";
        return 2;
    }
    return 0;
}
