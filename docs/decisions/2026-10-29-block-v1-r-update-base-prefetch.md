# R更新旧状态值随行流水提前取出

311原生正常CTS收尾，其详细placement实际setup−1.49ns、TNS−44472.72ns；resizer为−1.66ns。最差路径在原input.v对应product_row[1]/[3]→failed。原报告、网表SHA和源映射见work/YUZE-LU/121/review-20261028/r-311-placement-diagnosis；中间placement估算不是最终提取STA。

UP_MUL/UP_WRITE原先按product_row在退休当拍选择shadow，再作S128符号扩展、完整乘积RNE、S128更新加法、fits32及八lane错误汇总。现将每行旧S32状态与operand_row提前取出，随乘积传到退休端：八lane两级S32寄存共512bit，不新增结果队列或缩小数值域。既有行标记与valid控制保持，八共享乘法器与一行/拍吞吐、填充/排空相位和预期公共延迟不变。

取数只在UP_MUL真实fetch时发生；每行退休前对应旧状态已捕获。GDN在误差计算后取shadow，SSM在衰减写回后取shadow；同轮不同row的写回不覆盖待取旧值，最后一行随原排空路径退休。bank_role只在后续COMMIT交换。数据载荷不新增复位，仍由原valid标签保护，必须三初态独立参考验证。

342新源四项数值/公共/卷积/映射尚待执行；不得因为预期周期保持而继承309测量、310占用、311物理资格。后续须重新取新公共测量、占用与预算源，再以全新物理六阶段、最终四门/六文件/完整几何和接口验收。311及原实验继续正常运行，只有未分配未来选择才可退役。
