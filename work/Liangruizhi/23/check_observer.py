"""Development integration test on random tiny weights, not research evidence."""
from pathlib import Path
import sys
import json
import torch
from transformers import Qwen3Config, Qwen3ForCausalLM, DynamicCache
from transformers.models.qwen3 import modeling_qwen3

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "project/experiments/qwen3_trace"))
from trace import Observer, forward, run_trace
from numeric import run_numeric

torch.manual_seed(23)
torch.set_num_threads(2)
config = Qwen3Config(hidden_size=64, intermediate_size=96, num_hidden_layers=2,
                    num_attention_heads=4, num_key_value_heads=2, head_dim=16,
                    vocab_size=64, max_position_embeddings=128, use_sliding_window=False)
config._attn_implementation = "eager"
model = Qwen3ForCausalLM(config).float().eval()
ids = torch.tensor([[3, 6, 8, 10, 11, 12]], dtype=torch.long)
with torch.inference_mode():
    numeric = run_numeric(model, ids, prefix=4, steps=2)
    trace = run_trace(model, ids, 4, 2, [0, 1], 1e-4, 1e-4)
    original = modeling_qwen3.eager_attention_forward
    observer = Observer(model, [0])
    def fail(_module, _args, _output):
        raise RuntimeError("intentional hook failure")
    raised = False
    handle = model.model.layers[0].mlp.down_proj.register_forward_hook(fail)
    cache = DynamicCache(config=config)
    try:
        with observer.capture(cache):
            forward(model, ids, cache, 0, 4)
    except RuntimeError as error:
        if str(error) != "intentional hook failure":
            raise
        raised = True
    finally:
        handle.remove()
    restored = modeling_qwen3.eager_attention_forward is original and not observer.active
    no_hooks = all(not module._forward_hooks and not module._forward_pre_hooks
                   for module in model.modules())
result = {"scope": "random tiny-model development integration only",
          "numeric": numeric["status"], "trace": trace["status"],
          "trace_events": len(trace["events"]),
          "injected_failure_raised": raised, "eager_function_restored": restored,
          "hooks_removed": no_hooks, "numeric_failures": numeric["failures"],
          "trace_failures": trace["failures"]}
print(json.dumps(result, indent=2))
if numeric["status"] != "PASS" or trace["status"] != "PASS" or not (raised and restored and no_hooks):
    raise SystemExit(1)
