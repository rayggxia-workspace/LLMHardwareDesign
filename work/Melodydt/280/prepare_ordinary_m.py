"""Prepare a private copy of the accepted Qwen3 observer, or audit its outputs."""
import json
from pathlib import Path
import shutil
import sys


action, bundle, original, output = sys.argv[1:]
bundle, original, output = map(Path, (bundle, original, output))
if action == 'prepare':
    runner = output / 'runner'
    runner.mkdir()
    for path in (original / 'runner').iterdir():
        if path.suffix in ('.py', '.cpp'):
            shutil.copy2(str(path), str(runner / path.name))
    shutil.copy2(str(bundle / 'ordinary_m_observation.py'), str(runner))
    native = Path('/public/home/yuzelu/project-circuit/issue260-native-sram512-SMbOWTw6/native_tlm_projection.py')
    text = native.read_text()
    anchor = '                        self.edge(finish_group, 8 + 8 * (8 if head16 else 1))'
    if text.count(anchor) != 1:
        raise ValueError('ordinary projection source changed')
    text = text.replace(anchor, '                        cycles = 8 + 8 * (8 if head16 else 1)\n'
                        '                        self.target.component_observation.native_m_group(self.target, self.clock.now, cycles)\n'
                        '                        self.edge(finish_group, cycles)')
    (runner / native.name).write_text(text)
    qwen = runner / 'qwen3_short.py'
    text = qwen.read_text()
    anchor = 'from qwen3_component_observation import Observation'
    if text.count(anchor) != 1:
        raise ValueError('Qwen3 observer source changed')
    qwen.write_text(text.replace(anchor, 'from ordinary_m_observation import Observation'))
    for name in ('ddr-dma-probe.so', 'projection_math.so'):
        (output / name).symlink_to(original / name)
elif action == 'audit':
    stages = {}
    for prefix in ('prefill', 'decode-live'):
        name = prefix + '-w4-tile128-pr272-combined'
        old, new = original / name, output / name
        if json.loads((old / 'result.json').read_bytes()) != json.loads((new / 'result.json').read_bytes()):
            raise ValueError('complete frozen result changed')
        checked = []
        for path in old.iterdir():
            if path.suffix in ('.bin', '.q16', '.s32') or path.name == 'layer-trace.json':
                if path.read_bytes() != (new / path.name).read_bytes():
                    raise ValueError('frozen numerical output changed: ' + path.name)
                checked.append(path.name)
        obs = json.loads((new / 'component-observation.json').read_bytes())
        assert obs['ordinary_and_ffn_intervals_disjoint']
        stages[prefix] = {'complete_result_equal': True, 'numerical_files_equal': checked,
                          'ordinary_and_ffn_intervals_disjoint': True}
    (output / 'acceptance.json').write_text(json.dumps(stages, indent=2) + '\n')
    print('ORDINARY_M_ACCEPTED')
else:
    raise ValueError('invalid action')
