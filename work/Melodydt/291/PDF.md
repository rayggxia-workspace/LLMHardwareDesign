# 七模型速度报告 PDF

[下载完整 PDF](../../../docs/experiments/seven-model-speed-evaluation.pdf)；本地输出为 output/pdf/seven-model-speed-evaluation.pdf。24页、39张表，保留已发布HTML中的全部七模型数据和估算资格说明。短Prefill/Decode为已有TLM回执；512-token Prefill为条件线性估计，非完整序列实测。独立序列验证按用户指令暂缓。

PDF SHA-256：839d0d379507f680bd49fac300b0fbe5d34aef694c97692362af12ad2209fbf1。
源HTML SHA-256：e1f21defdd5435f93e23277e6699e5797822ce7a022866cc008335057a42b3bb。

## 生成与验证

使用Python、ReportLab 4.4.9、BeautifulSoup、pypdf，以及Deng.ttf/Dengb.ttf。字体可通过参数指定；不修改原HTML或JSON。

```powershell
python -B work/Melodydt/291/build_speed_pdf.py
python -B work/Melodydt/291/verify_speed_pdf.py
pdftoppm -r 85 -png output/pdf/seven-model-speed-evaluation.pdf work/Melodydt/291/tmp/pdfs/checked
```

本机使用Codex捆绑Python运行ReportLab/pypdf，BeautifulSoup复用D:/EDA/Anaconda3/lib/site-packages；Poppler使用捆绑运行时。已核对1939个表格单元格、8个警示框、七模型关键值和2个链接，渲染24页并目检；调整首页表头后重新渲染并检查。无新仿真。文档核验不替代暂缓的独立序列验证。

原43文件复算ZIP保持冻结，不含后追加的PDF。PDF、此说明、build_speed_pdf.py、verify_speed_pdf.py、pdf-build-receipt.json和pdf-validation.json在PR #292单独交付。审查/合并未完成；项目登记pending，看板unverified/同步pending。
