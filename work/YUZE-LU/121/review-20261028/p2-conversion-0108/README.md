# T P2严格转换失败及261队列

实际捕获01:06:52 CST；8个原始文件见[index.json](index.json)。260运行到2.2µm cut-spacing转换时，Decimal(float)保留二进制浮点尾差，严格整数DBU检查拒绝；失败保留。261改Decimal(str(value))，仍严格拒绝半DBU。对实际脚本抽出的转换函数，本地GDSdbu0.0001环境中2.2µm=22000、2µm=20000、实际native坐标转换通过，0.00005µm被拒；这个测试不模拟或证明KLayout。261实际完整P2尚未通过，等待真实回执。
