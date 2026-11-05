from pathlib import Path
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control'
for p in [h/'control162-docs790.py',r/'docs/CONTROL_V1.md',r/'docs/STATUS.md',r/'progress/YUZE-LU/STATUS.md',r/'work/YUZE-LU/162/continuation-checkpoint-67.md']:
 s=p.read_text(encoding='utf-8');s=s.replace('300精确Dijkstra/资源/距离检查','300项精确Dijkstra及原资源/距离检查').replace('未暂停或改写运行任务，不读写外国PID','未暂停或改写运行任务，未采样其他任务').replace('所有旧源/规格/失败与部分日志保留','所有旧源、规格、失败及全部已有日志和部分输出保留');p.write_bytes(s.encode())
