"""Install the payload and PM probes in a disposable replay source copy."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
source = path.read_text()
anchor = "    result = execution.run(trace_layers=args.trace_layers)"
if source.count(anchor) != 1:
    raise ValueError("Qwen3 runner entry changed")
path.write_text(source.replace(anchor, '''    import os
    from qwen3_real_activity import RealActivity
    windows = json.loads(Path(os.environ["QWEN3_COMPONENT_WINDOWS"]).read_bytes())
    real_activity = RealActivity(execution, windows)
    result = execution.run(trace_layers=args.trace_layers)
    names = ("prefill",) if args.mode == "prefill" else ("first_token", "decode")
    real_activity.write(args.output, names)'''))
