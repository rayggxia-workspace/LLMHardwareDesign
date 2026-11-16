"""Build actual weight frontend + raw M and exercise bounded public records."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def run(command, log):
    with log.open('w') as output:
        subprocess.run([str(x) for x in command], stdout=output, stderr=subprocess.STDOUT, check=True)


def wrapper(source, out):
    text = (source / 'project/rtl/w8a16_v1/weight_records.sv').read_text()
    header = text[text.index('module weight_records'):text.index('\n);')]
    header = header.replace('module weight_records', 'module weight_test_top', 1)
    header = header.replace('input wire w_ready', 'output wire w_ready')
    header += ''',
 input wire [255:0] a_data,
 input wire allow_w, raw_out_ready, raw_cancel_reset,
 output wire raw_valid, raw_error,
 output wire [31:0] raw_tag,
 output wire [3:0] raw_n,
 output wire [255:0] raw_data
);
 wire raw_in_ready;
 weight_records #(.KEY_W(KEY_W),.MC_CREDITS(MC_CREDITS)) dut(.*);
 assign w_ready=allow_w&&raw_in_ready;
 m_group_s32 core(.clk(clk),.reset(reset||raw_cancel_reset),
  .in_valid(w_valid&&allow_w),.in_ready(raw_in_ready),
  .in_first(w_first),.in_last(w_last),.in_tag(w_raw_tag),
  .in_group_k(w_group_k),.in_offset(w_offset),.in_k(5'd16),.in_n(w_n),
  .in_a(a_data),.in_w(w_data),.out_valid(raw_valid),.out_ready(raw_out_ready),
  .out_tag(raw_tag),.out_n(raw_n),.out_data(raw_data),.out_error(raw_error));
endmodule
'''
    path = out / 'weight_test_top.sv'
    path.write_text(header)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--fixture', required=True, type=Path)
    p.add_argument('--seed', required=True, type=int)
    p.add_argument('--jobs', type=int, default=10)
    p.add_argument('--verilator', required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    rtl = a.source / 'project/rtl/w8a16_v1'
    check = a.source / 'project/experiments/w8a16_weight'
    wrapped = wrapper(a.source, a.out)
    common = [a.verilator, '--Wall', '--top-module', 'weight_records', str(rtl / 'weight_records.sv')]
    run(common + ['--lint-only'], a.out / 'production-lint.log')
    command = [a.verilator, '--cc', '--exe', '--build', '--Wall', '--x-initial', 'unique',
               '--top-module', 'weight_test_top', '-j', str(a.jobs),
               '--Mdir', a.out / 'obj', '-CFLAGS', '-std=c++17 -Wall -Wextra -Werror',
               wrapped, rtl / 'weight_records.sv', rtl / 'm_group_s32.sv', check / 'test.cpp']
    run(command, a.out / 'build.log')
    logs = []
    for initial in (0, 1, 2):
        log = a.out / f'initial-{initial}.log'
        run([a.out / 'obj/Vweight_test_top', a.fixture, a.seed, initial], log)
        text = log.read_text()
        assert text.startswith('PASS weights '), text
        logs.append(dict(initial=initial, receipt=text.strip()))
    result = dict(passed=True, seed=a.seed, fixture_SHA256=hashlib.sha256(a.fixture.read_bytes()).hexdigest(),
                  source_commit=(a.source / 'source-commit.txt').read_text().strip(),
                  wrapper_SHA256=hashlib.sha256(wrapped.read_bytes()).hexdigest(), runs=logs)
    (a.out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
