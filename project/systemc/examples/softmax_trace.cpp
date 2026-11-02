/**
 * 257元素Softmax教学示例：通过真实SystemC FIFO连接S、N、T。
 * S窄字0..32保存x，128..160保存EXP；每字8个16位编码，末字只有1项有效。
 * N只保存统计/因子和计数；原始x以及EXP都由S重新读取后回放。
 * 前256项循环[-1,0,1,2]，最后一项4；因此最后一批到达前max绝不应提前成为4。
 * 打印值都是原始整数编码：x为Q5.10，EXP为UQ1.15，最终概率为非负S16 Q1.14。
 * 本程序展示事务顺序，不打印RTL周期，也不要求量化后概率之和恰好为16384。
 */
// Run this example to see 257 values pass through S -> N -> T.
// No full-vector array exists in N. S keeps inputs AND the EXP replay values.
#include "blocks/modules.hpp"
#include <iostream>
#include <stdexcept>
using namespace blocks;
// 教学用调度模块，拥有三个独立硬件行为模型及一个上层控制线程。
struct Demo : sc_core::sc_module {
    // S保存两份有限向量区域；N执行统计/函数；T接收完整输出批次。
    S storage{"S"};
    N norm{"N"};
    T transfer{"T"};
    // 输入和响应FIFO深度均为1，send必须等待对应响应，不能依靠无限软件队列。
    sc_core::sc_fifo<SCommand> si{"si", 1};
    sc_core::sc_fifo<NCommand> ni{"ni", 1};
    sc_core::sc_fifo<TCommand> ti{"ti", 1};
    sc_core::sc_fifo<Reply> so{"so", 1}, no{"no", 1}, to{"to", 1};
    // tag只用于请求/响应对应；completed供sc_main检查示例是否走完全部阶段。
    uint64_t tag = 0;
    bool completed = false;
    SC_HAS_PROCESS(Demo);
    // 绑定各模块端口，再注册上层run线程；仿真由sc_main中的sc_start启动。
    Demo(sc_core::sc_module_name name) : sc_module(name) {
        storage.commands(si);
        storage.responses(so);
        norm.commands(ni);
        norm.responses(no);
        transfer.commands(ti);
        transfer.responses(to);
        SC_THREAD(run);
    }
    // 发送一条带tag命令并阻塞等待响应；错误或tag不匹配立刻终止示例，避免打印伪成功轨迹。
    template <class C> Reply send(sc_core::sc_fifo<C> &in, sc_core::sc_fifo<Reply> &out, C c) {
        c.tag = ++tag;
        in.write(c);
        auto r = out.read();
        if (r.error || r.tag != c.tag)
            throw std::runtime_error("transaction rejected or response reordered");
        return r;
    }
    // 把最多8个16位位型拼入128位字；先转U16保留负数二补码，lane0占最低16位。
    static Word pack(const std::array<int64_t, 8> &lane) {
        Word w{};
        for (unsigned i = 0; i < 8; ++i)
            w[i / 4] |= uint64_t(uint16_t(lane[i])) << (16 * (i % 4));
        return w;
    }
    // 上层流程：写S -> 扫描最大值 -> 计算/存EXP -> 固定分母 -> 回放概率 -> T提交/消费/释放。
    void run() {
        // 257项需要33个字。exp_base单位是128位字地址，不是字节；与原输入区域不重叠。
        constexpr unsigned length = 257, words = (length + 7) / 8, exp_base = 128;
        for (unsigned word = 0; word < words; ++word) {
            SCommand c;
            c.op = SCommand::Op::Write;
            c.address = word;
            std::array<int64_t, 8> values{};
            for (unsigned i = 0; i < 8 && word * 8 + i < length; ++i) {
                unsigned index = word * 8 + i;
                values[i] = index == 256 ? 4096 : int64_t((int(index % 4) - 1) * 1024);
            }
            c.data = pack(values);
            send(si, so, c);
        }
        // 阶段1：建立单一Softmax上下文。此时尚未给N任何元素，max只是初始化哨兵值。
        NCommand c;
        c.op = NCommand::Op::Begin;
        send(ni, no, c);
        for (unsigned word = 0; word < words; ++word) {
            SCommand read;
            read.op = SCommand::Op::Read;
            read.address = word;
            auto source = send(si, so, read);
            c.op = NCommand::Op::Stats;
            c.count = std::min(8U, length - word * 8);
            for (unsigned i = 0; i < c.count; ++i)
                c.data[i] = halfword(source.bits, i);
            send(ni, no, c);
            NCommand query;
            query.op = NCommand::Op::ReadStats;
            auto stats = send(ni, no, query);
            std::cout << "STATS chunk=" << word << " accepted=" << stats.lane[0]
                      << " running_max=" << stats.lane[1] << "\n";
        }
        // 阶段1结束：最后那1个元素已统计，才锁定全向量最大值，之后禁止再追加Stats。
        c.op = NCommand::Op::Finalize;
        send(ni, no, c);
        for (unsigned word = 0; word < words; ++word) {
            SCommand read;
            read.op = SCommand::Op::Read;
            read.address = word;
            auto source = send(si, so, read);
            // 阶段2：从S重读x，由N计算EXP(x-final_max)。每批返回值写入S的EXP区域。
            c.op = NCommand::Op::Exp;
            c.count = std::min(8U, length - word * 8);
            for (unsigned i = 0; i < c.count; ++i)
                c.data[i] = halfword(source.bits, i);
            auto ex = send(ni, no, c);
            SCommand write;
            write.op = SCommand::Op::Write;
            write.address = exp_base + word;
            write.data = pack(ex.lane);
            send(si, so, write);
            NCommand query;
            query.op = NCommand::Op::ReadStats;
            auto stats = send(ni, no, query);
            std::cout << "EXP   chunk=" << word << " exp_count=" << stats.lane[5]
                      << " denominator_UQ1.15=" << stats.lane[6] << " first_exp=" << ex.lane[0]
                      << "\n";
        }
        // 阶段2全部完成后固定exp_sum，并计算floor(2^44/exp_sum)；因子尚未形成前不能输出概率。
        c.op = NCommand::Op::FinishExp;
        send(ni, no, c);
        c.op = NCommand::Op::ReadFactor;
        std::cout << "FACTOR floor(2^44/denominator)=" << send(ni, no, c).lane[0] << "\n";
        // 申请33字输出批次；T在写满并Commit前不向消费者暴露临时结果。
        TCommand tc;
        tc.op = TCommand::Op::Begin;
        tc.words = words;
        tc.generation = 1;
        send(ti, to, tc);
        int64_t probability_sum = 0;
        for (unsigned word = 0; word < words; ++word) {
            SCommand read;
            read.op = SCommand::Op::Read;
            read.address = exp_base + word;
            auto source = send(si, so, read);
            // 阶段3：从S读EXP，不重新求指数，N使用唯一最终分母进行归一化。
            c.op = NCommand::Op::SoftReplay;
            c.count = std::min(8U, length - word * 8);
            for (unsigned i = 0; i < c.count; ++i)
                c.data[i] = halfword(source.bits, i);
            auto y = send(ni, no, c);
            for (unsigned i = 0; i < c.count; ++i)
                probability_sum += y.lane[i];
            tc.op = TCommand::Op::Write;
            tc.index = word;
            // 一个T字保存最多8个Q1.14概率；末字其余lane为零，不计入概率求和。
            tc.data = pack(y.lane);
            send(ti, to, tc);
            std::cout << "REPLAY chunk=" << word << " output_Q1.14=";
            for (unsigned i = 0; i < c.count; ++i)
                std::cout << (i ? " " : "") << y.lane[i];
            std::cout << "\n";
        }
        // 输出已全部填满才Commit；之后Take顺序消费，验证index与末字标志。
        tc.op = TCommand::Op::Commit;
        send(ti, to, tc);
        for (unsigned word = 0; word < words; ++word) {
            tc.op = TCommand::Op::Take;
            auto result = send(ti, to, tc);
            if (result.index != word || result.last != (word + 1 == words))
                throw std::runtime_error("T result sequence");
        }
        // 最后一字消费后显式Release，允许T接受下一批；单个概率的独立舍入可能使总和略偏离1。
        tc.op = TCommand::Op::Release;
        send(ti, to, tc);
        std::cout << "DONE sum_of_quantized_probabilities=" << probability_sum
                  << "/16384 (independent rounding need not sum to exactly one)\n";
        completed = true;
        sc_core::sc_stop();
    }
};
// SystemC程序入口：创建模块、运行内核；异常或未完成返回非零，便于CTest检测失败。
int sc_main(int, char **) {
    try {
        Demo demo{"softmax_demo"};
        sc_core::sc_start();
        return demo.completed ? 0 : 1;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
