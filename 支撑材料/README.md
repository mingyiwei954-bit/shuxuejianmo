# 微网购电 V3 实质改进版复现说明

正式算法与五份结果表沿用一月选择后冻结的版本。新增消融、连续参数诊断与论文生成独立保存，未用正式期诊断反向挑选参数。原题及原始Excel只读。

## 版本和结果

正式参数以 `frozen/resolved_config.json` 为准：因果残差场景、最多20条已完成历史、终端倍数1。`config/final.yaml` 中的原始候选默认值用于记录原训练入口，不应取代已解析配置。

Q1日费用35,126.95元；二月至十二月Q2费用14,794,949.72元，Q3 S3费用15,632,485.48元，Q4-2费用15,623,134.83元，Q4-3 S3费用16,455,780.60元。一月启动费用另列，不包含在上述正式期金额内。

`frozen/columns.tar.xz` 与 `csv_manifest.json` 无损保存正式轨迹及既有对照。恢复时逐字节核验SHA256。`diagnostics` 是本轮新增，不能覆盖或混称正式结果。旧验证资料按时间和文件来源理解，不以旧版页数记录验证当前论文。

## 依赖

本轮实测环境见 `diagnostics/environment.json`：Python 3.12.14、NumPy 2.3.5、SciPy 1.16.1及内置HiGHS 1.8.0，Apple M1。其余Python依赖见 `requirements.txt`。源码不需要GPU。

工作簿生成使用Node和 `@oai/artifact-tool`；本机复现使用Codex已配置的运行时。DOCX生成使用python-docx，PDF及PNG检查使用文档技能的render_docx.py与配套LibreOffice。可通过 `--node` 与 `--renderer` 指定相应入口；其他机器需先准备这些依赖。已交付的五份工作簿可直接用于独立数值审计，无需重新生成。

## 三类入口

所有命令在支撑材料目录中运行。`--source-root` 指向其下包含“C题/附件”的目录；不要直接指向“附件”文件夹。下列 `<原始输入父目录>` 为用户本地路径占位符，不是实际命令内容。

```bash
python reproduce.py restore
python reproduce.py audit --source-root '<原始输入父目录>'
python reproduce.py diagnostics --source-root '<原始输入父目录>'
python reproduce.py paper
python reproduce.py workbooks --source-root '<原始输入父目录>'
```

- `restore`：解开原始冻结记录至 `outputs/c_final_v1`，不求解。
- `audit`：运行测试及原始附件、工作簿的独立核验；主要是账本复算，含独立Q1重新构造求解，不能称为全年策略重算。
- `diagnostics`：按已锁定协议运行新增方案；每个方案读取自己保存的完成记录，已有结果不重复运行。缺少完成记录才重新求解。统计入口校验64段连续运行及四组基准等价性。
- `paper`：从当前正文、已完成诊断和冻结结果生成当前DOCX、PDF；不再调用旧论文生成脚本。生成后仍须进行逐页视觉检查。
- `workbooks`：从当前正式冻结记录生成五份结果表，再独立核验；不改变正式策略。

若要从零重新求解原正式模型，而非恢复旧轨迹：

```bash
python reproduce.py numeric --source-root '<原始输入父目录>'
```

此入口使用原一月已选配置，重新计算正式模型及控制分支，写入 `outputs/recomputed_formal` 并核验该新目录。不会覆盖 `frozen` 或当前正式工作簿。若该目录已存在，程序停止，需先自行保留或移动旧运行。

`run_pipeline.sh` 统一转发以上入口；不带参数时为 `all`，顺序恢复正式结果、补齐新增诊断、审计并生成当前论文。`all` 不冒充重新求解正式模型，重新求解必须显式运行 `numeric`。

## 实验恢复和结果边界

`diagnostics/protocol.json` 与其哈希固定候选和比较口径。64段连续运行包含32段一月验证和32段二月至十二月回放；各段内部逐时执行并连续传递状态。均值基线、S2/S3的既有替代求解器和分块统计属于历史证据，本轮未把它们冒称为新重算。

完整诊断明细包保存压缩轨迹和合同链；支撑材料保存每次求解日志、逐日费用、配置、审计与汇总。若要强制从零重跑某项诊断，请先备份并移走该项 `diagnostics/runs/<phase>/<mode>__<variant>`，再运行diagnostics。不要只删除个别文件而保留summary.json，避免将不完整记录当作完成。

公开交付配置中的本机派生路径以相对路径或占位符记录；本地工作记录保留原日志。路径归一化不改变算法、输入文件哈希或任何数值结果。

AI详细使用说明和现有声明原样保留，本轮不重新评价。队员真实人工核验、身份页和赛区实际提交要求仍为提交前待办；自动审计不能替代人工签核。
