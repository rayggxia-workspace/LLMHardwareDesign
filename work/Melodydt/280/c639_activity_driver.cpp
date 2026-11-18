#include "Vtest_native_decode638_product_replay.h"
#include "verilated.h"
#include "verilated_fst_c.h"

#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

struct Window {
    std::string name;
    uint64_t start = 0;
    uint64_t end = 0;
    std::unique_ptr<VerilatedFstC> trace;
    bool opened = false;
    bool complete = false;
};

int main(int argc, char** argv) {
    const std::string output_arg = "+DDR_OUTPUT=";
    const std::string schedule_arg = "+CAPTURE_SCHEDULE=";
    std::string output;
    std::string schedule;
    for (int index = 1; index < argc; ++index) {
        const std::string arg = argv[index];
        if (arg.compare(0, output_arg.size(), output_arg) == 0) {
            output = arg.substr(output_arg.size());
        } else if (arg.compare(0, schedule_arg.size(), schedule_arg) == 0) {
            schedule = arg.substr(schedule_arg.size());
        }
    }
    std::ifstream input(schedule);
    std::vector<Window> windows(2);
    for (auto& window : windows) {
        if (!(input >> window.name >> window.start >> window.end) || window.start >= window.end) {
            std::cerr << "Invalid C639 activity window schedule\n";
            return 1;
        }
    }
    if (output.empty() || windows[0].name != "gate-up" || windows[1].name != "down"
            || windows[0].end >= windows[1].start) {
        std::cerr << "Missing output path or ambiguous C639 sample windows\n";
        return 1;
    }

    auto context = std::make_unique<VerilatedContext>();
    context->commandArgs(argc, argv);
    context->traceEverOn(true);
    auto top = std::make_unique<Vtest_native_decode638_product_replay>(context.get());
    for (auto& window : windows) {
        window.trace = std::make_unique<VerilatedFstC>();
        top->trace(window.trace.get(), 4);
    }
    while (!context->gotFinish()) {
        top->eval();
        const uint64_t now = context->time();
        for (auto& window : windows) {
            if (!window.opened && now >= window.start) {
                if (now != window.start) {
                    std::cerr << "C639 activity start did not align to a simulator edge\n";
                    return 2;
                }
                window.trace->open((output + "/ffn-" + window.name + ".fst").c_str());
                window.opened = true;
            }
            if (window.opened && !window.complete) {
                window.trace->dump(now);
                if (now >= window.end) {
                    if (now != window.end) {
                        std::cerr << "C639 activity end did not align to a simulator edge\n";
                        return 2;
                    }
                    window.trace->close();
                    window.complete = true;
                    std::cout << "C639_ACTIVITY " << window.name << " " << window.start
                              << " " << window.end << '\n';
                }
            }
        }
        if (!top->eventsPending()) {
            break;
        }
        context->time(top->nextTimeSlot());
    }
    top->final();
    return context->gotFinish() && windows[0].complete && windows[1].complete ? 0 : 2;
}
