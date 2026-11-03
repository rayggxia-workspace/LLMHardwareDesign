# Issue175 文档交付验证

2026-11-03，Asia/Shanghai；基线 `4b1df2c7cbdaa0fa6f9f468f2b5b854cec875609`。这份回执只对应文档任务，不是控制器、三个 LLM 或新 Block 的硬件通过证据。

| 检查 | 实际执行/结果 |
| --- | --- |
| 规则/隔离 | 已读 AGENTS、协作 Skill1.0.0、项目资料及本人进度；实际登录 YUZE-LU；独立 task/175 worktree，无现有脏改动被覆盖 |
| 管理结构 | 首先运行 `python -X utf8 -B scripts/check_project.py`，PASS；仅管理文件结构 |
| 图解析/渲染 | `node docs/local-blocks/render_diagrams.cjs --mermaid <固定11.4.1文件> --browser <Chrome> --screenshots <外部临时目录>`；13/13 parse/render PASS、非空节点标签、有效 viewBox、无 foreignObject |
| 图目视 | 逐张查看13张最终PNG；确认中文可读、无节点裁切/遮盖、分支/回路/数据落点清楚；结构图从五块横排改为纵排，增加标签宽度避免关键数值断行造成误读 |
| 来源/功能核对 | 与固定算子图§7/8/9/10和宏合同对照；核对Qwen部分RoPE/GDN顺序、Falcon双支/门后Norm/MuP、Granite attention_multiplier及TopK/归并；R/整数差异集中说明 |
| 资源预算 | 9 Block/28叶实例，工作S192KiB＋T12KiB；P的S32KiB为候选，不继承旧S16KiB物理资格；R局部bank和MEM整层状态分列 |
| 链接/摘要 | `python -X utf8 -B work/YUZE-LU/175/validate_docs.py`：PASS，6份固定来源blob/SHA-256、33个产物摘要、13对图源/SVG、15份Markdown本地文件链接；来源SHA为Git原字节，工作树/文本产物仅CRLF→LF规范化 |
| 格式/范围 | `git diff --check`；提交前核对仅文档、图源/SVG、图构建与文档检查辅助文件，无RTL/EDA改动 |
| 在线元数据 | PR152 head读回55243d2c；管理中心PR5 open/merged=false；Issue175 Projects查询返回 INSUFFICIENT_SCOPES(read:project)，无看板配置，留持久交接；实际PR/Issue状态以交付读回为准 |
| 上传 | Git直连github.com超时，使用GitHub API上传完全相同的Git tree与原作者/日期commit，首提交远端与本地同为5ca6bd8f；PR176已创建。最终HEAD及后续回执提交在PR中读回绑定 |

未执行：模型推理/整数质量、RTL仿真/LEC、服务器/Slurm、综合/P&R、300MHz和M11/M12接入。本轮未修改R/S/既有合格六宏，未改变现有任务/作业，未自合并。数值合同与物理证据欠项见[来源/差异表](../../../docs/local-blocks/SOURCES_AND_GAPS.md)。

渲染输入及工具精确版本见 [render-receipt.json](render-receipt.json)。首次渲染检查误把未标注边的空 text 节点当作空标签，已改为检查真实 node label，并关闭 HTML labels 生成纯 SVG；最终13图均按修正后的规则成功。未删有效图或用旧SVG替代失败图。
