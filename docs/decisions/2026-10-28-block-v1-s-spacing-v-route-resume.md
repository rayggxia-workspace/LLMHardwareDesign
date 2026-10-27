# S实际间距与V原生路线接续

S207独立检查完整保留：未修改FreePDK45 deck实际10项METAL10.2；原生7标记。190已有时序/电气、最终功能、严格LEC通过不能替代DRC。先只读定位实际M10线段、via及接口，后续修物理并重生寄生/全部独立接收。不得删标记、改deck或沿用旧源资格。

V215详细布线0违规，但do-finish缺5_route.odb失败。安装原生Makefile实际将route定义为5_2_route→5_3_fillcell→5_route.odb及5_1_grt.sdc→5_route.sdc。新222从失败回执封存的5_2_route.odb接续三个遗漏阶段及do-finish，不重复既有44分钟路线。原失败回执与完整驱动修复保留，源203不改，222全部最终物理/完整GDS DRC/三初态功能/严格LEC重验。接续仍可能发现新的真实电气或间距失败，准备与路由0均不算最终接收。

旧207父为主动排空后的FAILED，209仍承载共享队列；215依父终态将R delivery提前BLOCKED，实际R还在196详细布线。新队列在核215已终态且208业务CWD未创建后，复用从未领取的R physical/delivery，依真实子回执，不改215历史或重复领取。

每任务16CPU硬绑定、六槽即完即补；222新增实际ready的V finish与S locator可并行。旧任务自然收尾，无时间取消。新geometry需匹配真正最终源，221仅暂存不提交。
