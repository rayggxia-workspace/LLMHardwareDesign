#!/usr/bin/env bash
# 任一下载/校验/构建失败即退出；未定义变量和管道失败不能被后续成功命令掩盖。
set -euo pipefail
# Local dependency only; no sudo and no global configuration changes.
# 从脚本位置定位仓库，支持带空格/中文路径；依赖只写本任务仓库内的忽略目录。
repo_root=$(cd "$(dirname "$0")/../../.." && pwd)
deps="$repo_root/.systemc-deps"
mkdir -p "$deps"
cd "$deps"
# 下载固定3.0.1版本。已有归档仍必须经过下面的SHA校验，不能直接信任缓存。
if [ ! -f systemc.tar.gz ]; then
  curl -fL --connect-timeout 15 --max-time 180 \
    https://codeload.github.com/accellera-official/systemc/tar.gz/refs/tags/3.0.1 \
    -o systemc.tar.gz
fi
# 固定官方归档的SHA-256；内容不符立即停止，不安装或自动升级其他版本。
printf '%s  %s\n' d07765d0d2ffd6c01767880d0c6aaf53cd9487975f898c593ffffd713258fcbb systemc.tar.gz | sha256sum -c -
# 仅缺失源目录时解包；增量编译复用本地源/构建目录，不覆盖全局配置。
if [ ! -d systemc-3.0.1 ]; then tar -xzf systemc.tar.gz; fi
# 依赖与应用均采用C++17；Release仅针对依赖库，应用可单独使用Debug+UBSan。
cmake -S systemc-3.0.1 -B build -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$deps/install"
# 这是本地小型依赖的6路编译，不申请或调度项目的远端计算节点。
cmake --build build -j 6
cmake --install build
