#include <cstdint>
#include <memory>
#include <stdexcept>

#include "memory_system.h"

using Callback = void (*)(uint64_t, bool);

extern "C" void* native_dram_open(const char* config, const char* output, Callback done) {
    auto model = std::unique_ptr<dramsim3::MemorySystem>(dramsim3::GetMemorySystem(
        config, output, [done](uint64_t address) { done(address, false); },
        [done](uint64_t address) { done(address, true); }));
    if (model->GetBusBits() * model->GetBurstLength() != 512)
        throw std::runtime_error("native TLM requires 64-byte DDR bursts");
    model->EnableStrictWrites();
    return model.release();
}

extern "C" double native_dram_period_ns(void* handle) {
    return static_cast<dramsim3::MemorySystem*>(handle)->GetTCK();
}

extern "C" bool native_dram_offer(void* handle, uint64_t address, bool write) {
    auto& model = *static_cast<dramsim3::MemorySystem*>(handle);
    return model.WillAcceptTransaction(address, write) && model.AddTransaction(address, write);
}

extern "C" void native_dram_tick(void* handle) {
    static_cast<dramsim3::MemorySystem*>(handle)->ClockTick();
}

extern "C" void native_dram_close(void* handle) {
    auto model = std::unique_ptr<dramsim3::MemorySystem>(static_cast<dramsim3::MemorySystem*>(handle));
    model->PrintStats();
}
