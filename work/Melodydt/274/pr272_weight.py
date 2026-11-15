"""Bind the sealed PR #272 WeightFetch service to short-replay FFN routes."""
from pathlib import Path
import re


_QWEN3_FFN = re.compile(r"L[0-9]{2}-mlp\.(gate|up|down)_proj\.bin")
_EXPERT_FFN = re.compile(r"\.block_sparse_moe\.(input|output)_linear\.weight\.expert[0-9]+\.bin$")
_DENSE_FFN = tuple(
    f".{scope}.{operator}_proj.weight.bin"
    for scope in ("mlp", "feed_forward")
    for operator in ("gate", "up", "gate_up", "down")
)


def is_ffn_weight(image_path):
    """Recognize the frozen packers' Gate/Up/Down records by image filename."""
    name = Path(image_path).name
    return (
        name.endswith(_DENSE_FFN)
        or _QWEN3_FFN.fullmatch(name) is not None
        or _EXPERT_FFN.search(name) is not None
    )


def make_ffn_projections(base_projections):
    """Create RTL-backed weight providers using the existing projection geometry."""
    from pr272_native_projection import Projection

    return [
        Projection(
            base.clock, base.dram, base.memory, base.source, base.target,
            source_word=base.source_word, scratch_word=base.scratch_word,
            scratch_sram=base.scratch_sram, rtl_weight_fetch=True,
        )
        for base in base_projections
    ]
