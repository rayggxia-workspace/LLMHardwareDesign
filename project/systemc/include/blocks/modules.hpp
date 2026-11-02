/**
 * 七个真实SystemC模块的共同包装层：把各块功能引擎放入独立SC_THREAD。
 * 命令FIFO -> commands.read() -> engine.execute() -> responses.write() -> 响应FIFO。
 * 没有时钟或人为延迟，不能推断RTL拍数；FIFO满/空时由SystemC内核挂起相应线程。
 * 每块一个引擎实例，存储和有效位互相独立；对同一块的命令按输入FIFO顺序执行。
 * Reset仍是命令，不会异步取消FIFO中已入队的命令/响应；需要调用方协调系统复位。
 */
#pragma once
#include "e.hpp"
#include "g.hpp"
#include "m.hpp"
#include "n.hpp"
#include "r.hpp"
#include "s.hpp"
#include "t.hpp"
#include <systemc>
namespace blocks {
// Untimed transaction-level module. One active operation and one pending
// response, plus the caller's explicitly bounded sc_fifo channels. No clock.
// Reset is an ordered command; it cannot cancel a response already in a FIFO.
// Engine约定提供Command/Response类型和execute(const Command&)；七块共用通信机制但功能状态各异。
template <class Engine> class Module : public sc_core::sc_module {
    // 私有功能引擎，拥有本块的固定容量存储和控制状态，外部不能绕过命令直接改成员。
    Engine engine_;
    // 永久工作线程：输入空时read阻塞；输出满时write阻塞，并保留这一份待发响应。
    // execute在两次FIFO操作之间原子完成且不wait；状态更新发生在写响应之前。
    // 测试的深度1输入+深度1输出允许“已排队响应+待发响应+待执行命令”三个包占位。
    void run() {
        while (true) {
            auto command = commands.read();
            auto response = engine_.execute(command);
            responses.write(response); // blocks when downstream applies backpressure
        }
    }

  public:
    // 端口本身不决定容量；调用方创建sc_fifo并绑定，示例采用深度1以实际检查背压。
    sc_core::sc_fifo_in<typename Engine::Command> commands{"commands"};
    sc_core::sc_fifo_out<typename Engine::Response> responses{"responses"};
    // 为模板sc_module声明进程支持；构造时注册SC_THREAD，sc_start后由内核运行。
    SC_HAS_PROCESS(Module);
    explicit Module(sc_core::sc_module_name name) : sc_core::sc_module(name) { SC_THREAD(run); }
};
// 七个可实例化模块类型。例如blocks::N n{"N"}，绑定NCommand输入和Reply输出即可运行。
using M = Module<MEngine>;
using N = Module<NEngine>;
using E = Module<EEngine>;
using G = Module<GEngine>;
using R = Module<REngine>;
using S = Module<SEngine>;
using T = Module<TEngine>;
} // namespace blocks
