// Native TLM DDR transport for the frozen 107361 event model.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <limits>
#include <memory>
#include <stdexcept>
#include <vector>

#include "memory_system.h"

namespace {

constexpr uint64_t ddr_ps = 630;
constexpr uint64_t max_address = uint64_t{16} << 30;
constexpr uint64_t tick_error = std::numeric_limits<uint64_t>::max();
thread_local char last_error[256] = {};

enum Counter {
    reads, writes, callbacks, queue_ps, inflight_ps, dram_backpressure,
    issue_throttle, credit_wait, peak_queue0, peak_queue1, peak_active0,
    peak_active1, counter_count,
};

void set_error(const char* message) noexcept {
    std::snprintf(last_error, sizeof(last_error), "%s", message);
}

struct Request {
    uint64_t id;
    uint64_t address;
    uint64_t queued_ps;
    bool write;
};

struct Pending {
    uint64_t id;
    uint64_t key;
    uint64_t admitted_ps;
};

struct Channel {
    std::unique_ptr<dramsim3::MemorySystem> device;
    std::deque<Request> offered;
    std::vector<Pending> pending;
    std::array<uint64_t, 4> history{};
    unsigned history_count = 0;

    bool throttled(uint64_t cycle) {
        unsigned kept = 0;
        for (unsigned i = 0; i < history_count; ++i) {
            if (cycle - history[i] <= 2) {
                history[kept++] = history[i];
            }
        }
        history_count = kept;
        // The history is nondecreasing. Two entries in the current core
        // cycle must be the two most recent entries.
        return kept == history.size() || (kept >= 2 && history[kept - 2] == cycle);
    }
};

class Transport {
public:
    Transport(const char* config, const char* output0, const char* output1,
              uint32_t credits, uint64_t core_ps)
        : credits_(credits), core_ps_(core_ps) {
        if (!config || !output0 || !output1 || !credits_) {
            throw std::invalid_argument("DDR requires paths and positive credits");
        }
        const std::array<const char*, 2> outputs{output0, output1};
        for (unsigned i = 0; i < channels_.size(); ++i) {
            channels_[i].pending.reserve(credits_);
            auto& device = channels_[i].device;
            device.reset(dramsim3::GetMemorySystem(
                config, outputs[i], [this, i](uint64_t address) { returned(i, address, false); },
                [this, i](uint64_t address) { returned(i, address, true); }));
            if (!device || device->GetBusBits() * device->GetBurstLength() != 512 ||
                std::lround(device->GetTCK() * 1000) != ddr_ps) {
                throw std::runtime_error("DDR requires 64-byte bursts and a 630 ps device period");
            }
            device->EnableStrictWrites();
        }
    }

    void submit(uint64_t id, uint64_t address, int write, int channel, uint64_t queued_ps) {
        if (channel < 0 || channel >= static_cast<int>(channels_.size()) ||
            (write != 0 && write != 1) || address >= max_address || address % 64 || queued_ps < now_) {
            throw std::invalid_argument("invalid native DDR submit");
        }
        auto& queue = channels_[channel].offered;
        if (!queue.empty() && queued_ps < queue.back().queued_ps) {
            throw std::invalid_argument("DDR submits must be ordered per channel");
        }
        queue.push_back({id, address, queued_ps, write != 0});
        auto& peak = stats_[peak_queue0 + channel];
        if (queue.size() > peak) {
            peak = queue.size();
        }
    }

    uint64_t advance(uint64_t limit) {
        if (completion_cursor_ != completed_.size()) {
            throw std::runtime_error("consume pending DDR callbacks before advancing");
        }
        completed_.clear();
        completion_cursor_ = 0;
        while (limit >= now_ && limit - now_ >= ddr_ps) {
            now_ += ddr_ps;
            for (unsigned i = 0; i < channels_.size(); ++i) {
                auto& channel = channels_[i];
                if (!channel.offered.empty()) {
                    offer(channel, i);
                }
                channel.device->ClockTick();
            }
            // Never allow a Python callback to be skipped past a further
            // device edge. Both channels first finish this original tick.
            if (!completed_.empty()) {
                break;
            }
        }
        return now_;
    }

    int pop(uint64_t& id) {
        if (completion_cursor_ == completed_.size()) {
            return 0;
        }
        id = completed_[completion_cursor_++];
        return 1;
    }

    void stats(uint64_t* output) const {
        for (unsigned i = 0; i < stats_.size(); ++i) {
            output[i] = stats_[i];
        }
    }

    void finish() {
        if (completion_cursor_ != completed_.size()) {
            throw std::runtime_error("DDR closed before callbacks were delivered");
        }
        for (const auto& channel : channels_) {
            if (!channel.offered.empty() || !channel.pending.empty()) {
                throw std::runtime_error("DDR closed before drain");
            }
        }
        for (auto& channel : channels_) {
            channel.device->PrintStats();
        }
    }

private:
    void offer(Channel& channel, unsigned index) {
        const auto& request = channel.offered.front();
        if (request.queued_ps > now_) {
            return;
        }
        const uint64_t cycle = core_ps_ ? now_ / core_ps_ : 0;
        if (core_ps_ && channel.throttled(cycle)) {
            ++stats_[issue_throttle];
            return;
        }
        if (channel.pending.size() >= credits_) {
            ++stats_[credit_wait];
            return;
        }
        auto& device = *channel.device;
        if (!device.WillAcceptTransaction(request.address, request.write) ||
            !device.AddTransaction(request.address, request.write)) {
            ++stats_[dram_backpressure];
            return;
        }
        // The active list is bounded by credits. Its stable order matches
        // duplicate address/direction returns FIFO without per-beat allocations.
        const auto key = request.address | uint64_t{request.write};
        channel.pending.push_back({request.id, key, now_});
        auto& peak = stats_[peak_active0 + index];
        if (channel.pending.size() > peak) {
            peak = channel.pending.size();
        }
        if (core_ps_) {
            channel.history[channel.history_count++] = cycle;
        }
        stats_[queue_ps] += now_ - request.queued_ps;
        ++stats_[request.write ? writes : reads];
        channel.offered.pop_front();
    }

    void returned(unsigned index, uint64_t address, bool write) {
        auto& channel = channels_[index];
        const auto key = address | uint64_t{write};
        const auto found = std::find_if(channel.pending.begin(), channel.pending.end(),
                                        [key](const Pending& request) { return request.key == key; });
        if (found == channel.pending.end()) {
            throw std::runtime_error("unmatched DRAMsim3 callback");
        }
        ++stats_[callbacks];
        stats_[inflight_ps] += now_ - found->admitted_ps;
        completed_.push_back(found->id);
        channel.pending.erase(found);
    }

    std::array<Channel, 2> channels_{};
    std::array<uint64_t, counter_count> stats_{};
    std::vector<uint64_t> completed_;
    std::size_t completion_cursor_ = 0;
    uint64_t now_ = 0;
    uint32_t credits_;
    uint64_t core_ps_;
};

Transport& transport(void* handle) {
    if (!handle) {
        throw std::invalid_argument("null DDR transport");
    }
    return *static_cast<Transport*>(handle);
}

template <typename Function, typename Result>
Result guard(Function function, Result error) noexcept {
    try {
        return function();
    } catch (const std::exception& e) {
        set_error(e.what());
    } catch (...) {
        set_error("unknown DDR transport error");
    }
    return error;
}

}  // namespace

extern "C" void* fast_dram_open(const char* config, const char* output0, const char* output1,
                                 uint32_t credits, uint64_t core_ps) noexcept {
    return guard([&]() -> void* { return new Transport(config, output0, output1, credits, core_ps); },
                 static_cast<void*>(nullptr));
}

extern "C" int fast_dram_submit(void* handle, uint64_t id, uint64_t address, int write, int channel,
                                uint64_t queued_ps) noexcept {
    return guard([&] {
        transport(handle).submit(id, address, write, channel, queued_ps);
        return 1;
    }, -1);
}

extern "C" uint64_t fast_dram_advance(void* handle, uint64_t inclusive_limit_ps) noexcept {
    return guard([&] { return transport(handle).advance(inclusive_limit_ps); }, tick_error);
}

extern "C" int fast_dram_pop(void* handle, uint64_t* id) noexcept {
    return guard([&] {
        if (!id) {
            throw std::invalid_argument("missing DDR callback output");
        }
        return transport(handle).pop(*id);
    }, -1);
}

extern "C" int fast_dram_stats(void* handle, uint64_t* output) noexcept {
    return guard([&] {
        if (!output) {
            throw std::invalid_argument("missing DDR stats output");
        }
        transport(handle).stats(output);
        return 1;
    }, -1);
}

extern "C" int fast_dram_close(void* handle) noexcept {
    return guard([&] {
        if (!handle) {
            throw std::invalid_argument("null DDR transport");
        }
        std::unique_ptr<Transport> instance(static_cast<Transport*>(handle));
        instance->finish();
        return 1;
    }, -1);
}

extern "C" const char* fast_dram_error(void*) noexcept {
    return last_error;
}
