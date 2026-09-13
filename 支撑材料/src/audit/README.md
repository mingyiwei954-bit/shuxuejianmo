# 当前独立审计入口

在支撑材料根目录运行：

```bash
python reproduce.py audit --source-root '<包含C题文件夹的原始输入父目录>'
```

该入口先运行测试，再运行 `python src/audit/audit_final.py --workbooks`。审计直接读取原始附件、恢复后的冻结轨迹和五份工作簿，重算状态、费用与承诺链，并独立重建问题一LP；不修改工作簿。默认报告写到 outputs/c_final_v1/audit。

只审计另一个完整数值运行目录时：

```bash
python src/audit/audit_final.py --frozen-dir outputs/recomputed_formal/frozen
```

源码中的输入父目录由 CUMCM_SOURCE_ROOT 指定。进程退出0须所有检查PASS；不会把缺少输入或结果记为成功。新增连续诊断在 scripts/contribution_experiments.py 另行独立重算设备、跨日状态、费用与共同合同，结果保存在 diagnostics/runs 下。

交付根目录 audit 中为本轮已经实际执行的审计记录；重新运行的结果写入 outputs，二者应结合生成时间与文件哈希理解。
