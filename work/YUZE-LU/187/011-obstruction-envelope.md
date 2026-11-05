# 011 · 用保守下层障碍减小接入搜索

- `011-obstruction-envelope/overlay.sha256` 摘要 `45d757331eb10dc1bff8eb7f77e22377429549172e8a54ddb56b24dbcedcc40a`，RTL 同 010。作业 97484，c96 node13 两个 12 核步骤。用 `PJ_CONSERVATIVE_LEF=1` 运行 P&R。
- M1–M6 的所有原障碍都被包进各自整块覆盖矩形，原引脚和 M7–M10 障碍保持。子 GDS、时序数据和验收规则均维持固定来源。
- J 的接入从原详细 LEF 下的多分钟降至约 2.4 s，随后明确报 `DRT-0073 store/req_data[276]`。该原 pin 的 x 中心落在 1.6 µm 原生轨道的中间，2 µm 宽 pin 加上强制 via 完全包入，无法直接保证接入。下一轮允许在 M10 上平面接入和再换层，由实际 DRC 判定。
- P 复现 010 的 CTS hold 缓冲上限失败。后续检查父层真实时钟树，保留同一约束。