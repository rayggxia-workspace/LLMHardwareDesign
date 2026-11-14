// Live transport to the public DRAMsim3 API. The optional WR observer is
// distinct from the archived controller's native strict write callback.
// Same-address requests are always serialized.
#include <charconv>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#ifdef ISSUE265_NATIVE_STRICT
#include "memory_system.h"
#else
#include "dramsim3.h"
#endif

#if defined(ISSUE265_WRITE_COMMIT) && defined(ISSUE265_NATIVE_STRICT)
#error "Select one DRAM write completion mechanism"
#endif

#if defined(ISSUE265_WRITE_COMMIT) || defined(ISSUE265_NATIVE_STRICT)
#define ISSUE265_SUPPORTS_WRITES
#endif

#ifdef ISSUE265_WRITE_COMMIT
extern "C" void issue265_observe_writes(void (*observer)(void *, uint64_t, uint64_t, uint64_t), void *context);
#endif

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
    Bridge(const char* config, const char* output) {
#ifdef ISSUE265_WRITE_COMMIT
        issue265_observe_writes([](void* context, uint64_t address, uint64_t raw_tick, uint64_t write_delay) {
            static_cast<Bridge*>(context)->write_issued(address, raw_tick, write_delay);
        }, this);
#endif
        memory_.reset(dramsim3::GetMemorySystem(config, output,
              [this](uint64_t address) { read_complete(address); },
#ifdef ISSUE265_NATIVE_STRICT
              [this](uint64_t address) { complete(address, true); }));
        if (!memory_) throw std::runtime_error("could not construct strict DDR device");
        memory_->EnableStrictWrites();
#else
              [this](uint64_t address) { write_admitted(address); }));
#endif
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
        reply << "READY " << period_ps_;
#ifdef ISSUE265_WRITE_COMMIT
        reply << " WR_COMPLETION";
#elif defined(ISSUE265_NATIVE_STRICT)
        reply << " WR_CALLBACK";
#endif
        reply << std::endl;
        for (std::string line; std::getline(std::cin, line);) {
            std::istringstream request(line);
            std::string op;
            request >> op;
            if (op == "CAN") {
                const auto address = number(request);
#ifdef ISSUE265_SUPPORTS_WRITES
                const auto write = number(request);
                if (write > 1) throw std::runtime_error("write flag must be zero or one");
#else
                const auto write = false;
#endif
                end_of_request(request);
                reply << "CAN " << can_accept(address, write) << std::endl;
            } else if (op == "READ"
#ifdef ISSUE265_SUPPORTS_WRITES
                       || op == "WRITE"
#endif
            ) {
                const auto id = number(request);
                const auto address = number(request);
                const bool write = op == "WRITE";
                end_of_request(request);
                if (!can_accept(address, write) || !ids_.insert(id).second) {
                    throw std::runtime_error("request submitted without a free slot and unique live identity");
                }
                addresses_.emplace(address, Pending{id, write});
                if (!memory_->AddTransaction(address, write)) {
                    throw std::runtime_error("DRAM admission changed after acceptance");
                }
                reply << op << ' ' << id << std::endl;
            } else if (op == "TICK") {
                const auto count = number(request);
                end_of_request(request);
                if (!count || count > std::numeric_limits<uint64_t>::max() - tick_
                    || (count != 1 && !addresses_.empty())) {
                    throw std::runtime_error("invalid advance; live requests require individual DRAM ticks");
                }
                for (uint64_t elapsed = 0; elapsed < count; ++elapsed) {
                    ++tick_;
                    memory_->ClockTick();
#ifdef ISSUE265_WRITE_COMMIT
                    finish_writes();
#endif
                }
                reply << "DONE " << completed_.size();
                for (const auto& completion : completed_) {
                    reply << ' ' << completion.id << ' ' << completion.address;
#ifdef ISSUE265_SUPPORTS_WRITES
                    reply << ' ' << completion.done_tick << ' ';
                    if (completion.command_tick) reply << completion.command_tick;
                    else reply << -1;
#endif
                }
                completed_.clear();
                reply << std::endl;
            } else if (op == "EXIT") {
                end_of_request(request);
                if (!addresses_.empty() || !completed_.empty() || !due_writes_.empty()) {
                    throw std::runtime_error("cannot exit before all transactions complete");
                }
                memory_->PrintStats();
                reply << "EXIT" << std::endl;
                return;
            } else {
                throw std::runtime_error("unsupported DRAM bridge command");
            }
        }
        throw std::runtime_error("unexpected EOF; use EXIT after draining reads");
    }

private:
    struct Pending {
        uint64_t id;
        bool write;
        bool admission_callback = false;
        uint64_t command_tick = 0;
    };

    struct Completion {
        uint64_t id;
        uint64_t address;
        uint64_t done_tick;
        uint64_t command_tick;
    };

    bool can_accept(uint64_t address, bool write) const {
        if (address % 64) throw std::runtime_error("unaligned DRAM address");
        return !addresses_.count(address) && memory_->WillAcceptTransaction(address, write);
    }

    void complete(uint64_t address, bool write) {
        const auto entry = addresses_.find(address);
        if (entry == addresses_.end() || entry->second.write != write) {
            throw std::runtime_error("DRAM completion has no matching live owner");
        }
        const auto pending = entry->second;
#ifdef ISSUE265_WRITE_COMMIT
        if (write && (!pending.admission_callback || !pending.command_tick)) {
            throw std::runtime_error("write completed without observed admission and WR issue");
        }
#endif
        addresses_.erase(entry);
        ids_.erase(pending.id);
        completed_.push_back({pending.id, address, tick_, pending.command_tick});
    }

    void read_complete(uint64_t address) { complete(address, false); }

#ifndef ISSUE265_NATIVE_STRICT
    void write_admitted(uint64_t address) {
        const auto entry = addresses_.find(address);
        if (entry == addresses_.end() || !entry->second.write || entry->second.admission_callback) {
            throw std::runtime_error("write admission callback has no unique live owner");
        }
        entry->second.admission_callback = true;
    }
#endif

#ifdef ISSUE265_WRITE_COMMIT
    void write_issued(uint64_t address, uint64_t raw_tick, uint64_t write_delay) {
        const auto entry = addresses_.find(address);
        // The hook runs inside ClockTick at the controller's zero-based index.
        // Tick replies and the old read bridge instead count executed ticks.
        if (!tick_ || raw_tick != tick_ - 1 || !write_delay
            || write_delay > std::numeric_limits<uint64_t>::max() - tick_
            || entry == addresses_.end() || !entry->second.write || entry->second.command_tick) {
            throw std::runtime_error("WR command has no unique live owner or valid tick");
        }
        entry->second.command_tick = tick_;
        due_writes_.emplace(tick_ + write_delay, address);
    }

    void finish_writes() {
        while (!due_writes_.empty() && due_writes_.begin()->first <= tick_) {
            const auto entry = due_writes_.begin();
            if (entry->first != tick_) throw std::runtime_error("missed modeled write data completion");
            complete(entry->second, true);
            due_writes_.erase(entry);
        }
    }
#endif

    std::unordered_map<uint64_t, Pending> addresses_;
    std::unordered_set<uint64_t> ids_;
    std::multimap<uint64_t, uint64_t> due_writes_;
    std::vector<Completion> completed_;
    std::unique_ptr<dramsim3::MemorySystem> memory_;
    uint64_t period_ps_ = 0, tick_ = 0;
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
