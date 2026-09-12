# C题最终独立审计报告

- 正式交付门：**PASS**
- 检查数：81
- 状态计数：`{'PASS': 81}`
- 配置：`config/final.yaml`（存在；解析器 `json`）
- 紧急购电显示阈值：`5e-05` kWh；四位小数 `ROUND_HALF_UP` 后为 0 才省略。
- 审计策略：任何必填空值、非数值、非有限值或公式错误先记 FAIL，不进入数值计算；绝不静默补零。

## 正式结果门

- `PASS` `FINAL-result1.xlsx-SCHEMA`：result1.xlsx
- `PASS` `FINAL-result1.xlsx-FORMULA-ERRORS`：result1.xlsx
- `PASS` `FINAL-result1.xlsx-计划购电量-COVERAGE`：result1.xlsx/计划购电量
- `PASS` `FINAL-result1.xlsx-DETAIL-SOURCE`：result1.xlsx
- `PASS` `FINAL-result1.xlsx-DETAIL-COVERAGE`：result1.xlsx
- `PASS` `FINAL-result1.xlsx-PHYSICS`：result1.xlsx
- `PASS` `FINAL-result1.xlsx-SOURCE-MAPPING`：result1.xlsx
- `PASS` `FINAL-result1.xlsx-计划购电量-VALUES`：result1.xlsx/计划购电量
- `PASS` `FINAL-result1.xlsx-4H`：result1.xlsx/充放电量
- `PASS` `FINAL-result1.xlsx-COST`：result1.xlsx
- `PASS` `FINAL-result2.xlsx-SCHEMA`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-FORMULA-ERRORS`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-计划购电量-COVERAGE`：result2.xlsx/计划购电量
- `PASS` `FINAL-result2.xlsx-DETAIL-SOURCE`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-DETAIL-COVERAGE`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-DISPATCH-CAUSALITY`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-PHYSICS`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-SOURCE-MAPPING`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-计划购电量-VALUES`：result2.xlsx/计划购电量
- `PASS` `FINAL-result2.xlsx-4H`：result2.xlsx/充放电量
- `PASS` `FINAL-result2.xlsx-EMERGENCY-SEGMENTS`：result2.xlsx
- `PASS` `FINAL-result2.xlsx-COST`：result2.xlsx
- `PASS` `FINAL-result3.xlsx-SCHEMA`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-FORMULA-ERRORS`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-计划购电量-COVERAGE`：result3.xlsx/计划购电量
- `PASS` `FINAL-result3.xlsx-调整购电量-COVERAGE`：result3.xlsx/调整购电量
- `PASS` `FINAL-result3.xlsx-DETAIL-SOURCE`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-DETAIL-COVERAGE`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-DISPATCH-CAUSALITY`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-PHYSICS`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-SOURCE-MAPPING`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-计划购电量-VALUES`：result3.xlsx/计划购电量
- `PASS` `FINAL-result3.xlsx-调整购电量-VALUES`：result3.xlsx/调整购电量
- `PASS` `FINAL-result3.xlsx-4H`：result3.xlsx/充放电量
- `PASS` `FINAL-result3.xlsx-EMERGENCY-SEGMENTS`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-SETTLEMENT-FINAL`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-FORECAST-RELEASE`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-NEXT-DAY-PREVIEW`：result3.xlsx
- `PASS` `FINAL-result3.xlsx-SETTLEMENT-SEQUENTIAL`：result3.xlsx
- `PASS` `FINAL-result4-2.xlsx-SCHEMA`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-FORMULA-ERRORS`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-计划购电量-COVERAGE`：result4-2.xlsx/计划购电量
- `PASS` `FINAL-result4-2.xlsx-DETAIL-SOURCE`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-DETAIL-COVERAGE`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-DISPATCH-CAUSALITY`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-PHYSICS`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-SOURCE-MAPPING`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-计划购电量-VALUES`：result4-2.xlsx/计划购电量
- `PASS` `FINAL-result4-2.xlsx-4H`：result4-2.xlsx/充放电量
- `PASS` `FINAL-result4-2.xlsx-EMERGENCY-SEGMENTS`：result4-2.xlsx
- `PASS` `FINAL-result4-2.xlsx-COST`：result4-2.xlsx
- `PASS` `FINAL-result4-3.xlsx-SCHEMA`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-FORMULA-ERRORS`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-计划购电量-COVERAGE`：result4-3.xlsx/计划购电量
- `PASS` `FINAL-result4-3.xlsx-调整购电量-COVERAGE`：result4-3.xlsx/调整购电量
- `PASS` `FINAL-result4-3.xlsx-DETAIL-SOURCE`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-DETAIL-COVERAGE`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-DISPATCH-CAUSALITY`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-PHYSICS`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-SOURCE-MAPPING`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-计划购电量-VALUES`：result4-3.xlsx/计划购电量
- `PASS` `FINAL-result4-3.xlsx-调整购电量-VALUES`：result4-3.xlsx/调整购电量
- `PASS` `FINAL-result4-3.xlsx-4H`：result4-3.xlsx/充放电量
- `PASS` `FINAL-result4-3.xlsx-EMERGENCY-SEGMENTS`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-SETTLEMENT-FINAL`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-FORECAST-RELEASE`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-NEXT-DAY-PREVIEW`：result4-3.xlsx
- `PASS` `FINAL-result4-3.xlsx-SETTLEMENT-SEQUENTIAL`：result4-3.xlsx

## 全部非 PASS 项

- 无。

## 旧成果状态

旧审计结果逐项保存在 `legacy_audit_snapshot.json`。新版正式结果通过不会删除、覆盖或改写旧 FAIL/WARN/NOT_VERIFIABLE。该文件还保存用新版逐段规则回放旧 result3/result4-3 的补充检查；旧表的 0.0009 kWh 漏项和区间拆分继续保留为失败证据。

## 复跑命令

```bash
python3 -m src.audit.audit_final --config config/final.yaml --results-dir outputs/c_final_v1 --output-dir outputs/c_final_v1/audit
```
