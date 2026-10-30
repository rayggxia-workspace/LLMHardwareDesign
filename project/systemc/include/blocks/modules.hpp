#pragma once
#include "e.hpp"
#include "g.hpp"
#include "m.hpp"
#include "n.hpp"
#include "r.hpp"
#include "s.hpp"
#include "t.hpp"
#include <systemc>
namespace blocks {
// Untimed transaction-level module. One active operation and one pending
// response, plus the caller's explicitly bounded sc_fifo channels. No clock.
// Reset is an ordered command; it cannot cancel a response already in a FIFO.
template <class Engine> class Module : public sc_core::sc_module {
    Engine engine_;
    void run() {
        while (true) {
            auto command = commands.read();
            auto response = engine_.execute(command);
            responses.write(response); // blocks when downstream applies backpressure
        }
    }

  public:
    sc_core::sc_fifo_in<typename Engine::Command> commands{"commands"};
    sc_core::sc_fifo_out<typename Engine::Response> responses{"responses"};
    SC_HAS_PROCESS(Module);
    explicit Module(sc_core::sc_module_name name) : sc_core::sc_module(name) { SC_THREAD(run); }
};
using M = Module<MEngine>;
using N = Module<NEngine>;
using E = Module<EEngine>;
using G = Module<GEngine>;
using R = Module<REngine>;
using S = Module<SEngine>;
using T = Module<TEngine>;
} // namespace blocks
