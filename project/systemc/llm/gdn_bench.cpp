// 单个真实R模块轮转32头×16个value分块；每轮显式装入/回写外存状态。
#include "runtime.hpp"
using namespace llm;
class Driver : public sc_core::sc_module {
  Runtime rt;
  std::string dir;
  template <class T> static void read(std::ifstream &f, T *p, size_t count) {
    f.read(reinterpret_cast<char *>(p), std::streamsize(count * sizeof(T)));
    if (!f)
      throw std::runtime_error("short GDN input");
  }
  void run() {
    try {
      std::ifstream input(dir + "/inputs.bin", std::ios::binary);
      uint32_t header[5];
      int32_t exponent;
      read(input, header, 5);
      read(input, &exponent, 1);
      unsigned steps = header[1], heads = header[2], keys = header[3],
               values = header[4];
      if (header[0] != 0x47444e31 || keys > 256 || values % 8)
        throw std::runtime_error("GDN shape");
      std::vector<int32_t> state(size_t(heads) * keys * values, 0),
          output(size_t(steps) * heads * values);
      std::vector<int16_t> q(keys), k(keys);
      std::vector<int32_t> x(values);
      for (unsigned step = 0; step < steps; ++step)
        for (unsigned head = 0; head < heads; ++head) {
          uint32_t decay, beta;
          read(input, q.data(), keys);
          read(input, k.data(), keys);
          read(input, x.data(), values);
          read(input, &decay, 1);
          read(input, &beta, 1);
          for (unsigned value = 0; value < values; value += 8) {
            RCommand c;
            c.op = RCommand::Op::Open;
            c.length = keys;
            rt.r.call(c);
            for (unsigned row = 0; row < keys; ++row) {
              c = RCommand{};
              c.op = RCommand::Op::StateRow;
              c.index = row;
              for (unsigned lane = 0; lane < 8; ++lane)
                c.values[lane] =
                    state[(size_t(head) * keys + row) * values + value + lane];
              rt.r.call(c);
              c = RCommand{};
              c.op = RCommand::Op::Key;
              c.index = row;
              c.coefficients[0] = k[row];
              rt.r.call(c);
              c.op = RCommand::Op::Query;
              c.coefficients[0] = q[row];
              rt.r.call(c);
            }
            c = RCommand{};
            c.op = RCommand::Op::Parameters;
            c.decay = decay;
            c.beta = beta;
            rt.r.call(c);
            c = RCommand{};
            c.op = RCommand::Op::X;
            for (unsigned lane = 0; lane < 8; ++lane)
              c.values[lane] = x[value + lane];
            rt.r.call(c);
            c = RCommand{};
            c.op = RCommand::Op::Execute;
            c.mode = RCommand::Mode::GDN;
            rt.r.call(c);
            c.op = RCommand::Op::ReadOutput;
            auto y = rt.r.call(c);
            for (unsigned lane = 0; lane < 8; ++lane)
              output[(size_t(step) * heads + head) * values + value + lane] =
                  int32_t(y.lane[lane]);
            c.op = RCommand::Op::Commit;
            c.next_position = 1;
            rt.r.call(c);
            for (unsigned row = 0; row < keys; ++row) {
              c = RCommand{};
              c.op = RCommand::Op::ReadState;
              c.index = row;
              auto s = rt.r.call(c);
              for (unsigned lane = 0; lane < 8; ++lane)
                state[(size_t(head) * keys + row) * values + value + lane] =
                    int32_t(s.lane[lane]);
            }
          }
        }
      std::ofstream o(dir + "/systemc_output.bin", std::ios::binary);
      o.write(reinterpret_cast<const char *>(output.data()),
              std::streamsize(output.size() * 4));
      std::ofstream s(dir + "/systemc_state.bin", std::ios::binary);
      s.write(reinterpret_cast<const char *>(state.data()),
              std::streamsize(state.size() * 4));
      std::cout << "GDN_R_DONE steps=" << steps << " heads=" << heads
                << " value_tiles=" << values / 8
                << " state_exponent=" << exponent
                << " R_transactions=" << rt.r.transactions << std::endl;
    } catch (const std::exception &e) {
      error = e.what();
      std::cerr << error << std::endl;
    }
    sc_core::sc_stop();
  }

public:
  std::string error;
  SC_HAS_PROCESS(Driver);
  Driver(sc_core::sc_module_name name, std::string path)
      : sc_module(name), dir(std::move(path)) {
    SC_THREAD(run);
  }
};
int sc_main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  Driver driver("gdn", argv[1]);
  sc_core::sc_start();
  return driver.error.empty() ? 0 : 1;
}
