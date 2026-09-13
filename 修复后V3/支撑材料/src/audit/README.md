# C题独立审计门

`audit_final.py` 只读原始附件、官方模板、正式结果与旧审计，不修改任何工作簿。

它先验证空值、非数值、非有限值和公式错误，再执行数值计算。正式结果表逐项检查官方字段、日期、144 个唯一时段及顺序；Q3/Q4-3 使用全精度明细重算最终相对结算，并分别审计 252 条/日的正式承诺链与 360 条/日的逐次敏感性链。每个版本的 `forecast_issue_time` 还必须严格等于同日 0/6/12/18 点的 `decision_time`，且附件 3 中存在相应发布记录。每种模式另须有 71,928 条完整跨日预览（333 天 × 36/72/108 条），预览目标日、位置、非负有限电量和四个空承诺字段均逐行核验。紧急购电连续区间也只从全精度数量重建。

默认命令：

```bash
python3 -m src.audit.audit_final --config config/final.yaml --results-dir outputs/c_final_v1 --output-dir outputs/c_final_v1/audit
```

正式五表未生成时，正式检查记为 `PENDING`，命令成功生成阶段报告。五表生成后，只要有正式检查 `FAIL`，进程退出码为 2；零 `FAIL` 且零 `PENDING` 才将 `formal_delivery_gate` 记为 `PASS`。

紧急购电规则：先把每个 10 分钟全精度数量按 `ROUND_HALF_UP` 显示到配置的小数位；只有显示结果等于 0 的记录才能省略；过滤后再逐日合并相邻位置。有效阈值始终写入 JSON 和 Markdown 报告。
