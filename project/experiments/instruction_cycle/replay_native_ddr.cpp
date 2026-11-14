#include "memory_system.h"

#include <array>
#include <charconv>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

namespace {

struct Request {
    unsigned channel;
    uint64_t tick;
    bool write;
    uint64_t address;
};

uint64_t decimal(std::string_view field) {
    uint64_t value = 0;
    const auto result = std::from_chars(field.data(), field.data() + field.size(), value);
    if (result.ec != std::errc{} || result.ptr != field.data() + field.size()) {
        throw std::runtime_error("expected an unsigned decimal integer");
    }
    return value;
}

Request parse_request(std::string_view row) {
    if (!row.empty() && row.back() == '\r') row.remove_suffix(1);
    std::array<std::string_view, 4> fields;
    for (size_t column = 0; column < fields.size() - 1; ++column) {
        const auto separator = row.find('\t');
        if (separator == std::string_view::npos) {
            throw std::runtime_error("expected four tab-separated fields");
        }
        fields[column] = row.substr(0, separator);
        row.remove_prefix(separator + 1);
    }
    fields.back() = row;
    const auto channel = decimal(fields[0]);
    if (channel > 1 || (fields[2] != "R" && fields[2] != "W")) {
        throw std::runtime_error("expected channel 0 or 1 and operation R or W");
    }
    const auto address = decimal(fields[3]);
    if (address % 64) throw std::runtime_error("expected a 64-byte-aligned address");
    return {static_cast<unsigned>(channel), decimal(fields[1]), fields[2] == "W", address};
}

class Channel {
public:
    Channel(unsigned id, const char* config, const std::filesystem::path& directory,
            std::ostream& callbacks)
        : id_(id), callbacks_(callbacks) {
        std::filesystem::create_directories(directory);
        memory_.reset(dramsim3::GetMemorySystem(config, directory.string(),
              [this](uint64_t address) { complete(false, address); },
              [this](uint64_t address) { complete(true, address); }));
        if (!memory_ || memory_->GetBusBits() * memory_->GetBurstLength() != 512) {
            throw std::runtime_error("expected a 64-byte DRAM burst");
        }
        memory_->EnableStrictWrites();
    }

    void submit(const Request& request) {
        if (request.tick < ticks_) throw std::runtime_error("schedule ticks decreased");
        while (ticks_ < request.tick) clock_tick();
        if (!memory_->WillAcceptTransaction(request.address, request.write)) {
            throw std::runtime_error("DRAMsim3 was not ready at the recorded admission tick");
        }
        ++pending_[{request.write, request.address}];
        if (!memory_->AddTransaction(request.address, request.write)) {
            throw std::runtime_error("DRAMsim3 rejected a ready transaction");
        }
    }

    void drain() {
        // With no further submissions, a million ticks without a callback
        // indicates an incompatible configuration or a stalled model.
        constexpr uint64_t drain_timeout = 1'000'000;
        last_callback_tick_ = ticks_;
        while (!pending_.empty()) {
            if (ticks_ - last_callback_tick_ >= drain_timeout) {
                throw std::runtime_error("DRAMsim3 stalled while draining pending transactions");
            }
            clock_tick();
        }
    }

private:
    void clock_tick() {
        if (ticks_ == std::numeric_limits<uint64_t>::max()) {
            throw std::runtime_error("DDR tick count overflow");
        }
        // The native bridge logs admissions before ClockTick and increments
        // its counter before ClockTick can invoke callbacks.
        ++ticks_;
        memory_->ClockTick();
    }

    void complete(bool write, uint64_t address) {
        const auto pending = pending_.find({write, address});
        if (pending == pending_.end()) {
            throw std::runtime_error("DRAMsim3 callback has no pending transaction");
        }
        if (--pending->second == 0) pending_.erase(pending);
        last_callback_tick_ = ticks_;
        callbacks_ << id_ << '\t' << ticks_ << '\t' << (write ? 'W' : 'R') << '\t'
                   << address << '\n';
    }

    unsigned id_;
    std::ostream& callbacks_;
    uint64_t ticks_ = 0;
    uint64_t last_callback_tick_ = 0;
    std::map<std::pair<bool, uint64_t>, size_t> pending_;
    std::unique_ptr<dramsim3::MemorySystem> memory_;
};

void replay(const char* config, const std::filesystem::path& directory,
            const char* schedule, std::ostream& callbacks) {
    std::ifstream input(schedule);
    if (!input) throw std::runtime_error("cannot open DDR admission schedule");
    std::array<Channel, 2> channels{{
        {0, config, directory / "channel0", callbacks},
        {1, config, directory / "channel1", callbacks},
    }};
    unsigned current_channel = 0;
    uint64_t line = 0;
    for (std::string row; std::getline(input, row);) {
        ++line;
        try {
            const auto request = parse_request(row);
            if (request.channel < current_channel) {
                throw std::runtime_error("schedule must be grouped by channel in ascending order");
            }
            if (request.channel > current_channel) {
                channels[current_channel].drain();
                current_channel = request.channel;
            }
            channels[current_channel].submit(request);
        } catch (const std::exception& error) {
            throw std::runtime_error("schedule line " + std::to_string(line) + ": " + error.what());
        }
    }
    if (input.bad()) throw std::runtime_error("failed reading DDR admission schedule");
    channels[current_channel].drain();
    callbacks.flush();
    if (!callbacks) throw std::runtime_error("failed writing DDR callbacks");
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: replay_native_ddr CONFIG OUTDIR SCHEDULE\n";
        return 2;
    }
    // Keep library messages out of the callback TSV.
    std::ios::sync_with_stdio(false);
    std::ostream callbacks(std::cout.rdbuf());
    std::cout.rdbuf(std::cerr.rdbuf());
    try {
        replay(argv[1], argv[2], argv[3], callbacks);
    } catch (const std::exception& error) {
        std::cerr << "native DDR replay: " << error.what() << '\n';
        return 1;
    }
}
