# AH2只接收双头context，完整A仍须单资源整合

Issue151/PR152，Melodydt，2026-11-03；源70611916、95327有限仿真证据已形成待独立审查。

AH2采用M/N/E/S各1，完整H1024/D128一KV供两Q；统一Fin10/W7/epsilon1整数候选，真实512KiB tile-major供参，K/V保存且不重投影。RoPE真实split-half64 gather，V轴不改，token0只count1、token1 count2。当前固定FSM预制候选，不是启动装载控制程序。

为单独接收head机制，本轮输出64字context且不配T，也不保原X残差；ATSP保持先前独立证据。下一完整A必须合并局控/owner和共享S/E/T，不能并排实例化两个自带S/E的验证top。扩8KV/16Q、全部8192B context后才Wo2048，并与T原残差lease/输出复用一起重验。

权重stream只对当前request tag接受，坏/旧/未来拍fail且不S写，不做无界late drain。局部同钟域协调reset不代替任意外部MEM晚返回隔离。外部generation/provider须协调。质量/官方框架/尺度与完整A→F接口另门，不因context通过放宽24GAP或R/系统物理资格。

Issue旧正文接近上限，已在7436dc0d归档原64972字符/105671B并逐字读回，再整理在线入口，不改变历史要求或回执。
