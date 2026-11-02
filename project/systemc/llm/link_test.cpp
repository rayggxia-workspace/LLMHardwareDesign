#include "tensor_link.hpp"
#include <iostream>
using namespace llm;
class Test : public sc_core::sc_module {
  TensorLink link{"link"};
  unsigned finished = 0;
  void sender(unsigned id) {
    try {
      Tensor x;
      x.e = -7;
      x.v.resize(2051);
      x.lane_e.resize(x.v.size());
      for (size_t i = 0; i < x.v.size(); ++i) {
        x.v[i] = int16_t((i * 17 + id * 331) % 65536 - 32768);
        x.lane_e[i] = int(i % 23) - 25;
      }
      auto y = link.forward(x);
      if (y.v != x.v || y.lane_e != x.lane_e || y.e != x.e)
        throw std::runtime_error("tensor reconstruction");
      if (++finished == 3) {
        if (!link.packets || link.max_request_slots > 4 || !link.lock_wait_ns)
          throw std::runtime_error("finite/contended transport not exercised");
        std::cout << "LINK_TEST PASS packets=" << link.packets
                  << " lock_wait_ns=" << link.lock_wait_ns << "\n";
        passed = true;
        sc_core::sc_stop();
      }
    } catch (const std::exception &e) {
      rejection = e.what();
      std::cerr << "LINK_TEST_REJECT " << e.what() << "\n";
      sc_core::sc_stop();
    }
  }
  void a() { sender(1); }
  void b() { sender(2); }
  void c() { sender(3); }
  void watchdog() {
    sc_core::wait(1, sc_core::SC_MS);
    timed_out = true;
    std::cerr << "LINK_WATCHDOG incomplete transfer\n";
    sc_core::sc_stop();
  }

public:
  bool passed = false, timed_out = false;
  std::string rejection;
  SC_HAS_PROCESS(Test);
  explicit Test(sc_core::sc_module_name n) : sc_module(n) {
    SC_THREAD(a);
    SC_THREAD(b);
    SC_THREAD(c);
    SC_THREAD(watchdog);
  }
};
int sc_main(int argc, char **argv) {
  Test t{"test"};
  sc_core::sc_start();
  if (argc == 2 && std::string(argv[1]) == "--expect-corruption")
    return t.rejection == "link payload mismatch" ? 0 : 1;
  if (argc == 2 && std::string(argv[1]) == "--expect-timeout")
    return t.timed_out ? 0 : 1;
  return t.passed ? 0 : 1;
}
