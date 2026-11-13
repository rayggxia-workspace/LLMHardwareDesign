// Live, read-only transport to the public DRAMsim3 API.
// Same-address requests are serialized because the API callbacks carry only an address.
#include <charconv>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "dramsim3.h"

namespace {

uint64_t number(std::istringstream& request) {
    std::string word;
    request >> word;
    uint64_t value = 0;
    const auto result = std::from_chars(word.data(), word.data() + word.size(), value);
    if (result.ec != std::errc{} || result.ptr != word.data() + word.size()) {
        throw std::runtime_error("expected an unsigned decimal integer");
    }
    return value;
}

void end_of_request(std::istringstream& request) {
    std::string extra;
    if (request >> extra) throw std::runtime_error("unexpected trailing command argument");
}

class Bridge {
public:
    Bridge(const char* config, const char* output)
        : memory_(dramsim3::GetMemorySystem(config, output,
              [this](uint64_t address) { read_complete(address); },
              [](uint64_t) { throw std::runtime_error("unexpected write callback in read-only bridge"); })) {
        if (!memory_ || memory_->GetBusBits() * memory_->GetBurstLength() != 512) {
            throw std::runtime_error("expected a 64-byte DRAM burst");
        }
        const double period = memory_->GetTCK() * 1000.;
        if (!std::isfinite(period) || period < 1. || period > 1e9 || std::abs(period - std::round(period)) > 1e-6) {
            throw std::runtime_error("DRAM clock period must be an integral number of picoseconds");
        }
        period_ps_ = static_cast<uint64_t>(std::round(period));
    }

    void run(std::ostream& reply) {
        reply << "READY " << period_ps_ << std::endl;
        for (std::string line; std::getline(std::cin, line);) {
            std::istringstream request(line);
            std::string op;
            request >> op;
            if (op == "CAN") {
                const auto address = number(request);
                end_of_request(request);
                reply << "CAN " << can_accept(address) << std::endl;
            } else if (op == "READ") {
                const auto id = number(request);
                const auto address = number(request);
                end_of_request(request);
                if (!can_accept(address) || !ids_.insert(id).second) {
                    throw std::runtime_error("read submitted without a free slot and unique live identity");
                }
                addresses_.emplace(address, id);
                if (!memory_->AddTransaction(address, false)) {
                    throw std::runtime_error("DRAM admission changed after acceptance");
                }
                reply << "READ " << id << std::endl;
            } else if (op == "TICK") {
                const auto count = number(request);
                end_of_request(request);
                if (!count || (count != 1 && !addresses_.empty())) {
                    throw std::runtime_error("live reads require individual DRAM ticks");
                }
                for (uint64_t tick = 0; tick < count; ++tick) memory_->ClockTick();
                reply << "DONE " << completed_.size();
                for (const auto& [id, address] : completed_) reply << ' ' << id << ' ' << address;
                completed_.clear();
                reply << std::endl;
            } else if (op == "EXIT") {
                end_of_request(request);
                if (!addresses_.empty() || !completed_.empty()) {
                    throw std::runtime_error("cannot exit before all reads complete");
                }
                memory_->PrintStats();
                reply << "EXIT" << std::endl;
                return;
            } else {
                throw std::runtime_error("unsupported DRAM command; bridge is read-only");
            }
        }
        throw std::runtime_error("unexpected EOF; use EXIT after draining reads");
    }

private:
    bool can_accept(uint64_t address) const {
        if (address % 64) throw std::runtime_error("unaligned DRAM address");
        return !addresses_.count(address) && memory_->WillAcceptTransaction(address, false);
    }

    void read_complete(uint64_t address) {
        const auto entry = addresses_.find(address);
        if (entry == addresses_.end()) throw std::runtime_error("read callback has no live owner");
        const auto id = entry->second;
        addresses_.erase(entry);
        ids_.erase(id);
        completed_.emplace_back(id, address);
    }

    std::unordered_map<uint64_t, uint64_t> addresses_;
    std::unordered_set<uint64_t> ids_;
    std::vector<std::pair<uint64_t, uint64_t>> completed_;
    std::unique_ptr<dramsim3::MemorySystem> memory_;
    uint64_t period_ps_ = 0;
};

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: dramsim_bridge CONFIG OUTPUT_DIR\n";
        return 2;
    }
    // Reserve stdout for protocol replies even when the library prints stats.
    std::ostream reply(std::cout.rdbuf());
    std::cout.rdbuf(std::cerr.rdbuf());
    try {
        Bridge(argv[1], argv[2]).run(reply);
    } catch (const std::exception& error) {
        std::cerr << "DRAM bridge: " << error.what() << '\n';
        return 1;
    }
}
