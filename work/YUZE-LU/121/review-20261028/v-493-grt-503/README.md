# 新493全局布线阶段证据

Refs #121 / PR122。实际493/93618/node25完成全局布线并进入详细布线。5原始文件、完整4515653字节GRT JSON的远端SHA索引与标量metrics、311源Git blobs及实际四份RTL SHA核验；485映射/功能receipt与501 CTS的绑定保持一致。

GRT setup WS−0.0180429ns/TNS−0.0399418ns、6违例；hold WS+0.075662ns/TNS0、0违例；maxcap11/maxslew2。全部阶段违例原样保留，不作为最终300MHz接收。详细布线、fresh RCX、全部端点/电气/DRC/最终网表功能/严格LEC、文件/几何/接口仍须完成。

完整GRT JSON保留授权服务器，SHA为178527aa5442c860ce64178f2163ff4428722f50ee6b8da416b7e838b2ad6680。首次采集因完整JSON超过小文件阈值而在本地查找失败，未生成封存index；恢复时五份原始文件逐字节重新核验相同，只补充索引和标量数据，没有重跑或修改EDA。

实际路径、来源与核验见[index.json](index.json)；当前源为4399685bceca5f4364a9f601c5f23a6ecebe912a，不挪用旧V资格。
