# V507 实际最终报告：setup 与电容拒收

Refs #121 / PR #122。507/93623 自然完成六阶段；24份原始文件、311份归档 Git blob/远端 SHA、receipt 输入与已采输出逐一核验，见 index.json。内部最终 LEC 为 UNSAT/IDENTICAL，全部 diff0/1 输入输出为零。

实际最终 setup WS −0.0211138ns、TNS −0.120571ns、12项违例；hold WS +0.0136555ns、TNS0/0项；maxcap6/maxslew0。最终标准单元面积715931µm²。流程运行成功不能代替宏验收。

实际最差路径 point_total[7][2] → point_rounded[7][127]，原始报告与综合网表映射见 path-source-mapping.json。八路 P_ROUND_ADD 的串行组进位是本次修正对象；6项电容需另外追踪实际网。508独立最终检查继续，509接口等待真实验收。R404不取消、不重启；旧源资格不转移到修正后的V。
