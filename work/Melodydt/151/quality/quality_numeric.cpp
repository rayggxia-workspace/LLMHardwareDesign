// Fixed legacy-regression profiles; no calibration selection or quality verdict.
// Compile C++17 with -O2 -ffp-contract=off -fopenmp. The inherited file is frozen.
#define main inherited_qnum_main
#include "../qnum/qwen_layer0_numeric.cpp"
#undef main

static void quality_fp32_exports(const Cache& cache, const std::string& out,
                                 std::ostream& index) {
    const std::string dir = out + "/fp32/" + cache.c.id;
    std::filesystem::create_directories(dir);
    for (const std::string stage : {"Y", "norm", "gate", "up", "mid", "down", "Z"}) {
        V values;
        for (const auto& f : cache.f) {
            const V* row = stage == "Y" ? &f.input : stage == "norm" ? &f.norm :
                stage == "gate" ? &f.gate : stage == "up" ? &f.up :
                stage == "mid" ? &f.mid : stage == "down" ? &f.down : &f.output;
            values.insert(values.end(), row->begin(), row->end());
        }
        const int cols = (stage == "gate" || stage == "up" || stage == "mid") ? I : H;
        need(values.size() == cache.f.size() * size_t(cols), "FP32 complete stage shape");
        const std::string relative = "fp32/" + cache.c.id + "/" + stage + ".f32le";
        writebin(out + "/" + relative, values);
        index << cache.c.id << '\t' << cache.c.split << '\t' << stage << '\t'
              << cache.f.size() << '\t' << cols << '\t' << relative << '\n';
    }
}

static void quality_weight_stream(const Profile& p, const std::string& out) {
    const std::string path = out + "/rtl_exports/" + p.id + "/weights-stream.bin";
    std::ofstream stream(path, std::ios::binary);
    need(bool(stream), "canonical weight stream open");
    size_t bytes = 0, requests = 0;
    const auto chunk = [&](const std::vector<int8_t>& w, int group, int kc, int K) {
        // Four native K8 tiles. Each tile is eight output columns of eight K bytes.
        for (int tile = 0; tile < 4; ++tile) for (int n = 0; n < 8; ++n) {
            const size_t offset = size_t(group * 8 + n) * K + kc * 32 + tile * 8;
            need(offset + 8 <= w.size(), "canonical stream source bounds");
            stream.write(reinterpret_cast<const char*>(w.data() + offset), 8);
            bytes += 8;
        }
        ++requests;
    };
    for (int group = 0; group < 384; ++group) {
        for (int kc = 0; kc < 32; ++kc) chunk(p.g, group, kc, H);
        for (int kc = 0; kc < 32; ++kc) chunk(p.u, group, kc, H);
    }
    for (int group = 0; group < 128; ++group)
        for (int kc = 0; kc < 96; ++kc) chunk(p.d, group, kc, I);
    need(bool(stream) && bytes == 9437184 && requests == 36864, "complete 9MiB weight stream");
}

static void quality_profile_json(std::ostream& out, const Profile& p) {
    out << "{\"id\":\"" << p.id << "\",\"X_Fin\":10,\"norm_gamma_Fin\":10,"
        << "\"gate_up_mid_Fin\":10,\"down_output_residual_Fin\":10,\"weight_Fin\":["
        << p.wg << ',' << p.wu << ',' << p.wd << "],\"M_READ_right_shift\":["
        << p.wg << ',' << p.wu << ',' << p.wd
        << "],\"M_factor\":1,\"M_left_shift\":0,\"epsilon_code\":1,"
        << "\"epsilon_real_effective\":9.5367431640625e-7,\"current_F1024_top_profile\":"
        << (p.wg == 7 ? "true" : "false") << ",\"requires_top_profile_change\":"
        << (p.wg == 7 ? "false" : "true") << ",\"parameter_clips\":{\"gamma\":"
        << p.gamma_clip << ",\"gate_weights\":" << p.wgclip << ",\"up_weights\":"
        << p.wuclip << ",\"down_weights\":" << p.wdclip << "},\"metrics\":{";
    int split_index = 0;
    for (const auto& by_split : p.metrics) {
        if (split_index++) out << ',';
        out << '"' << by_split.first << "\":{";
        int stage_index = 0;
        for (const auto& by_stage : by_split.second) {
            if (stage_index++) out << ',';
            out << '"' << by_stage.first << "\":";
            by_stage.second.json(out);
        }
        out << '}';
    }
    out << "}}";
}

int main(int argc, char** argv) {
    try {
        std::fesetround(FE_TONEAREST);
        const uint16_t endian = 1;
        need(*reinterpret_cast<const unsigned char*>(&endian) == 1, "little-endian required");
        if (argc == 2 && std::string(argv[1]) == "--self-test") {
            self_test();
            std::cout << "PASS_QUALITY_NUMERIC_SELFTEST\n";
            return 0;
        }
        need(argc == 4, "usage: quality_numeric tensor-map.tsv cases.tsv output-directory");
        self_test();
        const std::string out = argv[3];
        need(!std::filesystem::exists(out + "/numeric-summary.json") &&
             !std::filesystem::exists(out + "/rtl_exports") &&
             !std::filesystem::exists(out + "/fp32"), "numeric artifacts must not already exist");
        std::filesystem::create_directories(out);
        const Model model = load(argv[1]);
        for (const std::string name : {"gate_proj", "up_proj", "down_proj"})
            need(safe_frac(model.t.at(name)) == 8, "pinned complete matrix safe WFin must equal8: " + name);
        const auto prompts = cases(argv[2]);
        const std::map<std::string, std::pair<std::string, std::vector<int>>> expected = {
            {"cal_text_0", {"cal", {9707, 1879, 0, 198}}},
            {"cal_math_0", {"cal", {16, 10, 16, 28}}},
            {"eval_text_0", {"eval", {785, 8251, 374, 2613}}},
            {"eval_math_0", {"eval", {17, 9, 18, 28}}}
        };
        need(prompts.size() == expected.size(), "exact four legacy-regression prefixes");
        std::map<std::string, bool> seen;
        std::vector<Cache> cache;
        std::ofstream fpindex(out + "/fp32-stage-index.tsv");
        need(bool(fpindex), "FP32 stage index open");
        for (const auto& c : prompts) {
            need(expected.count(c.id) && !seen[c.id], "legacy case ID or duplicate");
            const auto& e = expected.at(c.id);
            need(c.split == e.first && c.ids == e.second, "exact legacy split and token IDs");
            seen[c.id] = true;
            cache.push_back(fp32(model, c, out));
            quality_fp32_exports(cache.back(), out, fpindex);
        }
        fpindex.close();
        need(bool(fpindex), "FP32 stage index write");
        std::vector<Profile> profiles;
        for (int wf : {7, 8}) {
            Profile p{wf == 7 ? "current_Fin10_WFin7" : "matrix_safe_x10_n10",
                      10, 10, wf, wf, wf, 1, {}, {}, {}, {}};
            p.g = quant8(model.t.at("gate_proj"), wf, p.wgclip);
            p.u = quant8(model.t.at("up_proj"), wf, p.wuclip);
            p.d = quant8(model.t.at("down_proj"), wf, p.wdclip);
            p.gamma = quant16(model.t.at("post_norm"), 10, p.gamma_clip);
            profiles.push_back(std::move(p));
        }
        const auto table = gtable();
        std::ofstream rows(out + "/rtl-export-rows.tsv");
        need(bool(rows), "RTL export rows open");
        for (auto& p : profiles) {
            for (const auto& c : cache) evaluate(p, c, table);
            export_profile(p, cache, table, out, rows);
            quality_weight_stream(p, out);
        }
        rows.close();
        need(bool(rows), "RTL export rows write");
        std::ofstream summary(out + "/numeric-summary.json");
        need(bool(summary), "numeric summary open");
        summary << std::setprecision(17)
            << "{\"status\":\"FIXED_BASELINE_W8_LEGACY_REGRESSION_NOT_MODEL_QUALITY\","
            << "\"selection\":\"fixed_profiles_no_selection_legacy_regression_not_holdout\","
            << "\"W8_safe_fraction_all_matrices_verified\":true,"
            << "\"quality_acceptance\":false,\"cal_cases\":2,\"eval_cases\":2,"
            << "\"attention\":\"independent FP32 complete layer0 Attention creates Y; only F(Y) quantized\","
            << "\"FP32_backend\":\"sequential F32 reductions; FMA disabled by required compiler flag; actual framework comparison separate\","
            << "\"profiles\":[";
        for (size_t i = 0; i < profiles.size(); ++i) {
            if (i) summary << ',';
            quality_profile_json(summary, profiles[i]);
        }
        summary << "]}\n";
        summary.close();
        need(bool(summary), "numeric summary write");
        std::cout << "PASS_QUALITY_NUMERIC profiles=2 legacy_prefixes=4 exported_fixtures=8\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_QUALITY_NUMERIC " << error.what() << '\n';
        return 1;
    }
}
