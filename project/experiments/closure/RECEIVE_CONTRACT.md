# Issue72 独立接收约定

接收代码不导入producer。`integer_oracle.py`用Python int、Fraction、逐bit恢复
除法/开方定义RNE、溢出、饱和、S8 digit宽乘与LUT边界；这些是数学参考，
不是实测硬件实现。tiny边界测试可本机运行，真实模型/采集/数值只在授权服务器。

各producer必须记录模型revision/权重SHA、输入/cal-eval token及来源SHA、
代码commit/实际模块SHA、编译常量/LUT字节SHA、shape/dtype/layout、code和单位
关系、静态/动态尺度及量化粒度。manifest完整列每artifact路径/大小/SHA，
接收前全部核验，输出新目录不覆盖旧结果。

整数runtime输入、状态和输出trace为整数数组，包含每个完整stage及连续状态
必要的初末值。评价浮点参考另存；误差只在独立评价层计算。state事务记录token、
head、attempt、当前/试算单位、epoch、guard、accept、published版本与checksum，
失败代不能污染已提交状态。chunk变化须保持同一串输入与连续checkpoint。

独立接收先校来源和数值边界，再从源整数code完整重算被声称的消费者链，不能
仅抽查已给出的最终值或相信自报operation count。大张量可逐token/head流式，
但4096norm必须完整归约。W8投影若未串入真实整数递推，应明确cut点，不能把
不同轨迹的投影/状态误差相加或拼称完整链。runtime源码需可审查无FP算术桥；
仅整数trace自身不足以证明无隐含浮点运算。

至少执行真正重写SHA的code、LUT/参数、route/epoch等语义篡改负例。每项分别
保留hash层和数学/协议层结果，不把文件哈希通过当数值正确或硬件质量通过。
