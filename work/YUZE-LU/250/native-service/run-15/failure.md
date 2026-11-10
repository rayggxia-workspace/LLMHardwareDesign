102195严格编译拒绝新增诊断消息：旧require接口只接const char*，新增拼接为std::string。
显式在调用期间取c_str()修复，未放宽任何编译选项或数值/资源验收。
