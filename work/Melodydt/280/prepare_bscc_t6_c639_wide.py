"""Reuse the frozen C639 prepared program and widen only Verilator tracing."""
from pathlib import Path
import sys


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"unexpected frozen C639 source anchor: {before}")
    return text.replace(before, after)


path = Path(sys.argv[1])
text = path.read_text()
start = text.index('"$model_env/bin/python" -B "$EXP/$prepare"')
stop = text.index(' provider_sources+=(+define+NATIVE_FFN_RUNTIME_REARM', start)
text = text[:start] + 'test -s "$g/program.json"\nif [[ "$scope" == history-final-product-ffn* ]]; then\n' + text[stop:]
for before, after in (
    ('g=$case_dir/generated', 'g=${C639_GENERATED:?}'),
    ('vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator', 'vlt=${C639_VERILATOR:?}'),
    ('--trace-fst --trace-depth 4', '--trace-fst --trace-depth 4 --trace-max-width 8192'),
):
    text = replace_once(text, before, after)
path.write_text(text)

top = path.with_name("test_native_decode638_product_replay.sv")
rtl = top.read_text()
rtl = replace_once(rtl, "parameter int TILES=28, MOTHER_WORDS=15\n);",
                   "parameter int TILES=28, MOTHER_WORDS=15\n)(output wire writer_trace_trigger);")
anchor = "    import \"DPI-C\" function int unsigned ddr_read_step_at"
rtl = replace_once(rtl, anchor, "    assign writer_trace_trigger = feed_forward.output_wr_valid && "
                   "feed_forward.output_wr_ready && feed_forward.ddr_phase_owner;\n" + anchor)
top.write_text(rtl)

driver = path.with_name("c639_activity_driver.cpp")
cpp = driver.read_text()
for before, after in (
    ("    auto context =", '    windows.emplace_back();\n    windows.back().name = "writer-active";\n'
     '    windows.back().start = UINT64_MAX;\n\n    auto context ='),
    ("        const uint64_t now = context->time();", "        const uint64_t now = context->time();\n"
     "        auto& writer = windows.back();\n"
     "        if (writer.start == UINT64_MAX && now % 5000 == 0 && top->writer_trace_trigger) {\n"
     "            writer.start = now;\n            writer.end = now + 81920000;\n        }"),
    ("windows[0].complete && windows[1].complete ?", "windows[0].complete && windows[1].complete && windows[2].complete ?"),
):
    cpp = replace_once(cpp, before, after)
driver.write_text(cpp)
