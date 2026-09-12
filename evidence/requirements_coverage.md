# 要求覆盖表

| 题目或交付要求 | 正式证据 | 验收方式 |
|---|---|---|
| Q1确定性日计划 | `workbooks/result1.xlsx`、`frozen/q1_dispatch.csv` | 144时段、能量平衡、6000→6000 |
| Q2因果日前策略 | `workbooks/result2.xlsx`、`frozen/q2_dispatch.csv` | 历史截止日早于决策、334×144 |
| Q3日内调整 | `workbooks/result3.xlsx`、`frozen/q3_dispatch.csv`、`decision_versions.csv` | 承诺链、过去冻结、两种结算 |
| Q4波动价格 | `workbooks/result4-2.xlsx`、`workbooks/result4-3.xlsx` | 因果价格预测、实际价格事后结算 |
| 24h跨日滚动 | `decision_versions.csv`、SOC列 | 下一日预览、执行块、跨日连续 |
| 三项增强与消融 | `experiment_summary.csv`、`monthly_effects.csv` | 同信息边界、同端点、同结算 |
| 数值稳定性 | `stability_summary.csv` | 3方法×3并列破除系数、分币判断 |
| 工作簿 | 五份result文件、`qa/workbook_build.json` | 重开、重算、错误扫描、逐表渲染 |
| 论文与匿名 | `paper/C题论文.pdf`、`paper/C题论文.docx` | 无目录、正文≤30页、无身份信息 |
| AI披露 | 论文参考文献前声明、`paper/AI工具使用详情.pdf` | 团队人工核对并补录未知模型信息 |
| 支撑材料 | `支撑材料.zip`、`SHA256SUMS.json` | 两文件均小于20MB、哈希冻结 |
