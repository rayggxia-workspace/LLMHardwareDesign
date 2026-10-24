# Issue72封存后精确说明

原phase/结果/包SHA保持，不覆盖已执行产物；本文件是追加解释，不把新HEAD写成旧运行源码。

1. 全I32×I32经N256求和的通用宽度为72 signed bits：S=C=-2^31时256×2^62=+2^70，71位有符号最大2^70-1，故容不下。冻结phase13 service metadata/limit和早期说明写71，属于描述性off-by-one。真实数值路径始终有actual maxproduct×N I64 guard，超界abort/不发布；本批已通过的I64任务和服务成本不变。新增独立最负码边界测试验证该反例以及guard原子拒绝。当前HEAD将未来服务metadata改72，原source capsule仍按原SHA接收；不声称全码域I64保证或已实现72bit RTL。
2. factor2/4同时缩放所有VR byte-lane服务成本，包括宽算术、复制/重排、guard和控制，M/SFU/port不缩放。它不是单独宽乘的消融，不能把总差归因宽乘。
3. 本机字节验收工具后续仅显式LF换行；原phase15工具/实际运行源仍按原Git SHA保留。原PC回执值相同，仓库展示版统一LF；archive及成员字节未变。
