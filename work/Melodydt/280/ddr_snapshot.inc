// Inserted into SimpleStats: observe cumulative plus current epoch without flushing either.
nlohmann::json SimpleStats::EnergySnapshot() const {
    nlohmann::json result;
    const auto counter = [&](const char* name) {
        return counters_.at(name) + epoch_counters_.at(name);
    };
    result["num_cycles"] = counter("num_cycles");
    result["num_pre_cmds"] = counter("num_pre_cmds");
    result["num_srefe_cmds"] = counter("num_srefe_cmds");
    result["num_srefx_cmds"] = counter("num_srefx_cmds");
    result["num_reads_done"] = counter("num_reads_done");
    result["num_writes_done"] = counter("num_writes_done");
    struct Component {
        const char* counter_name;
        const char* energy_name;
        double increment;
    };
    const Component commands[] = {
        {"num_act_cmds", "act_energy", config_.act_energy_inc},
        {"num_read_cmds", "read_energy", config_.read_energy_inc},
        {"num_write_cmds", "write_energy", config_.write_energy_inc},
        {"num_ref_cmds", "ref_energy", config_.ref_energy_inc},
        {"num_refb_cmds", "refb_energy", config_.refb_energy_inc},
    };
    const Component background[] = {
        {"rank_active_cycles", "act_stb_energy", config_.act_stb_energy_inc},
        {"all_bank_idle_cycles", "pre_stb_energy", config_.pre_stb_energy_inc},
        {"sref_cycles", "sref_energy", config_.sref_energy_inc},
    };
    double total = 0.0;
    for (const auto& component : commands) {
        const auto count = counter(component.counter_name);
        result[component.counter_name] = count;
        const auto energy = count * component.increment;
        result[component.energy_name] = energy;
        total += energy;
    }
    for (const auto& component : background) {
        for (int rank = 0; rank < config_.ranks; ++rank) {
            const auto count = vec_counters_.at(component.counter_name).at(rank)
                               + epoch_vec_counters_.at(component.counter_name).at(rank);
            result[component.counter_name][std::to_string(rank)] = count;
            const auto energy = count * component.increment;
            result[component.energy_name][std::to_string(rank)] = energy;
            total += energy;
        }
    }
    result["total_energy"] = total;
    return result;
}
