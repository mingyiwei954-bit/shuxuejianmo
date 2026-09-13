"""Current-run repair report, with computed effects and explicit limits."""
from pathlib import Path
from datetime import datetime
import json,pandas as pd
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'outputs/c_final_v1';F=O/'frozen'

def main():
    audit=json.loads((O/'audit/independent_validation.json').read_text());quality=json.loads((O/'final_validation_v3.json').read_text())
    exp=pd.read_csv(F/'experiment_summary.csv');official=pd.read_csv(F/'official_summary.csv');settle=pd.read_csv(F/'settlement_sensitivity.csv');jan=pd.read_csv(F/'startup_summary.csv');q1=pd.read_csv(F/'q1_dispatch.csv')
    def get(mode,sc='S0',arm='joint_empirical'):
        return exp[(exp['mode']==mode)&(exp.scenario==sc)&(exp.model_arm==arm)].iloc[0]
    def f(x,n=2):return f'{x:,.{n}f}'
    old={'q2':17646794.819761,'q3':16662138.664212,'q4_2':18660362.332063,'q4_3':17539062.517961}
    rows='\n'.join(f'| {r["mode"]} | {f(old[r["mode"]])} | {f(r.final_relative_cost_yuan)} | {f(r.final_relative_cost_yuan-old[r["mode"]])} |' for _,r in official.iterrows())
    risk='\n'.join(f'| {mode} | {f(get(mode,arm="mean_forecast").final_relative_cost_yuan)} | {f(get(mode).final_relative_cost_yuan)} | {f(get(mode,arm="mean_forecast").final_relative_cost_yuan-get(mode).final_relative_cost_yuan)} | {f(get(mode).emergency_kwh,4)} |' for mode in ['q2','q4_2'])
    ledger='\n'.join(f'| {r["mode"]} | {f(r.main_cost)} | {f(r.same_chain_sequential_cost)} | {f(r.same_chain_sequential_cost-r.main_cost)} | {f(r.no_refund_same_path_cost)} |' for _,r in settle.iterrows() if r['mode'] in ['q3','q4_3'])
    schedule='\n'.join(f'| {mode.upper()} | {f(get(mode).final_relative_cost_yuan)} | {f(get(mode,"S3").final_relative_cost_yuan)} | {f(get(mode,"S3").final_relative_cost_yuan-get(mode).final_relative_cost_yuan)} | {f(get(mode,"S3").final_relative_cost_yuan-get(mode,"S2").final_relative_cost_yuan)} |' for mode in ['q3','q4_3'])
    times='\n'.join(f'| {h}:00–{h}:10 | {int(h*6+1)} | {f(q1.loc[q1.position==h*6+1,"plan_00_grid_kwh"].iloc[0],6)} |' for h in [10,12,14,16,18,20])
    text=f'''# V3闭环修复与独立复验报告

生成时间：{datetime.now().astimezone().isoformat()}。对象：桌面“最新版本V3”。用户本轮已明确授权实际修复，要求保留真实数据、禁止未来信息泄漏并遵守数学约束。此前只读审查报告描述修复前快照；本报告使用新的正式运行。

## 当前结论

本轮已实际重写风险规划、滚动承诺和启动逻辑，重跑一月选型及二月至十二月正式实验，重新导出论文和五份结果工作簿。原始附件未修改。独立数值及工作簿检查{len(audit['checks'])}项，状态{audit['status']}；文档与导出检查{len(quality['checks'])}项，状态{quality['status']}。这些检查证明下述实现、约束和证据一致性，不证明模型在所有解释和所有未来数据下最优。

没有用旧报告数值充当本轮结果，没有把历史预测场景伪装成实际观测，也没有仅修改PASS字段。旧流水线被停止，修订前完整备份保留在本次Codex任务的work/before_repair；项目自身旧输出保留在work/pre_repair_output。

## 1. 已修复事项与数值影响

### 五倍缺口成本已进入日前规划

`src/model/risk.py:cases/solve`使用完整观测的历史联合轨迹构造经验预测分布。所有采购、充放电和状态在场景之间共享；仅紧急采购随场景变化，目标直接含五倍价缺口损失。没有提前给优化器未来实际负载、光伏或电价。残差的基准预测也在对应历史日只使用更早日期生成。

`experiments.py`只用1月8—31日比较两种场景构造与0.5/1/1.5终端惩罚倍数，锁定因果残差场景、倍数1.0。已解析配置在`frozen/resolved_config.json`；候选默认值不能代替实际解析配置。正式期334天不参与参数选择。

相同日期与状态合同下，均值预测控制与新风险策略比较如下，差额是本数据实现结果：

| 模式 | 均值预测费/元 | 风险策略费/元 | 费用降低/元 | 风险策略紧急量/kWh |
|---|---:|---:|---:|---:|
{risk}

无储能控制费用分别为{f(get('q2',arm='no_storage').final_relative_cost_yuan)}、{f(get('q4_2',arm='no_storage').final_relative_cost_yuan)}元。紧急购电是题面允许的缺口补足机制，不能把该量称为最终停电量。有限历史分布仍可能漏掉极端风险。

### 逐次结算已改为同一真实承诺链

`rolling.py:simulate`记录每次正式更新的旧承诺、新承诺、交付位置和发布时间。后续预览不记为正式订单；已交付段不允许重写。现有同链逐次结果如下：

| 模式 | 净额费用/元 | 同链逐次费用/元 | 逐次减净额/元 | 不退原价同路径/元 |
|---|---:|---:|---:|---:|
{ledger}

独立审计从版本记录重新累积每一笔调整，并单独从原始曲线重算同一执行轨迹的紧急费。旧版以另一条确定性路径计算调整费、再拼正式路径紧急费的做法已删除。相同非负交付价下，`逐次−净额 = 0.5Σp(Σ|ΔA|−|ΣΔA|) ≥ 0`；100→80→100、价格1元的例子，逐次较净额多20元。退费和交付价是明示解释；其他定价解释须重新定义模型。

### 十分钟错位和Q2—Q4缺表已修复

以右端点数据代表前十分钟区间为统一离散化口径。论文按`physical_interval`抽取，官方模板按原列序写入；新增“时段映射”页保留原标签与物理键的区别。Q1费用仍为{f(q1.final_relative_cost_yuan.sum(),6)}元；不以目标相同掩盖时段错误。

| 题面物理区间 | 正确位置 | 当前计划量/kWh（六位展示） |
|---|---:|---:|
{times}

例如12:00应取位置73、原模板B74，旧论文误取位置72。六个时段已在DOCX、PDF、工作簿中核对。Q2/Q3/Q4-2/Q4-3四类×四指定日期均包括六个十分钟值、六组四小时充放电、0/24点SOC、全天量/费用和连续紧急区间。含Q1共17组；文档存在的占位符数量为0。修复前本次审查也已查明“剩80个占位”的历史说法不适用于当时快照，因此不把这一旧数字算作本轮成果。

### S0/S3比较已固定共同日前承诺

先用因果的S0参考过程形成各日B。四种频次使用同一B、相同一月启动和年末状态；滚动差异来自后续允许信息更新。全部计划动作在场景中共享完整窗口，避免旧版午夜分支共享范围不一致。

| 模式 | S0费用/元 | S3费用/元 | S3减S0/元 | S3减S2/元 |
|---|---:|---:|---:|---:|
{schedule}

本次S2略低于S3，S3仍作为题设四时点机制的正式结果，而非被称为全局最优。32个相同LP实例、3种求解法共96次诊断中，目标最大差约7.28×10⁻¹²元，但采购轨迹L1最大差292.46 kWh、SOC轨迹最大差2577.19 kWh。存在并列解敏感性；没有据此宣称替代求解器的全年策略排序已经稳定。逐日配对7天块重采样区间已列论文，重采样不被当作新观测。

### 一月SOC衔接与无历史启动已重建

删除“首日无历史时用当天完整实际曲线”的未来信息兜底。采用明示、可行的一月启动合同：电池待机C=D=0；首日计划为0，实际缺口按紧急合同支付；以后只用已经完成的历史日作采购分位数决策。逐段记录4464个时段，因此一月末6000是状态递推的结果，二月初值从账本读取，不是空填6000。Q2/Q3一月启动费各{f(jan[jan['mode']=='q2'].cost_yuan.iloc[0])}元，Q4-2/Q4-3各{f(jan[jan['mode']=='q4_2'].cost_yuan.iloc[0])}元，均披露在论文。

这是一项保守的启动策略，不声称一月最优。离线选型回放与真实启动合同区分记录。普通分段结束不强行回到6000；仅明确评价末端（训练子实验或12月31日）施加终端条件。首日、跨日、分段恢复、不同充放电效率和年末边界已测试。

## 2. 与修复前已交付版本的差异

| 模式 | 修复前已交付费/元 | 当前正式费/元 | 当前减旧版/元 |
|---|---:|---:|---:|
{rows}

旧版数值来自本轮修复前的独立复算，不是历史报告直接抄录的结论。修复前后台另有Q3从1200起步的未同步结果16,664,426.073252元；它与当时6000起步的交付稿不一致。本次所有分支已统一启动合同。表中总差额同时包含风险模型、预测、合同与边界改变，不能全部归因为一个修复点；模型改进效果优先看第1节受控比较。

## 3. 数学约束与信息隔离证据

- 真实负载、光伏、价格直接从附件1、2、4读取重算，逐时段匹配；源功率转电量除以6。
- 独立重算供需、紧急量、未用富余、费用和`E_next=E+0.9C−D/0.9`；检查SOC在[1200,10800]、每段充放电≤5000/6、不同时充放电、前后状态连续。
- Q1另构建一套LP约束矩阵验证最优目标，未调用原模型费用函数。
- 未来观测扰动保持决策已知信息不变；改变未发生的负载、光伏、电价后，场景和当前决策不变。更晚发布的预报不能影响0点结果。测试范围见`tests/test_closed_loop.py`，共7个测试。
- 对全部8条S0—S3承诺链独立回放，核对旧值连续、没有改写过去、最终值等于正式执行及同路径费用不等式。
- 五份工作簿检查原始列序、逐时段量、日期、日总量/费用、四小时汇总、端点SOC及全部紧急区间，不只查文件存在。
- DOCX/PDF指定表逐值与全精度轨迹核对；PDF中的表格数字文字与DOCX一致，公式、图及各页进行了渲染检查。

## 4. 可复算证据链与运行

| 证据环节 | 当前文件/入口 |
|---|---|
| 原题与原附件 | 原题C题.pdf、附件1—5；evidence/source_provenance.json保存原始SHA256 |
| 信息与模型 | src/model/risk.py、forecast.py、rolling.py、experiments.py |
| 参数来源 | evidence/january_parameter_validation.csv、frozen/resolved_config.json |
| 执行与合同 | frozen中正式/控制/各频次逐时段轨迹、decision_versions、各S0—S3账本 |
| 独立复算 | src/audit/audit_final.py、audit/independent_validation.json |
| 表格及文稿 | 五份result工作簿、paper/main.md、scripts/paper_content.py、native_equations.py |
| 最终检查 | final_validation_v3.json、SHA256SUMS.json；哈希清单排除自身 |

工程完整运行：在支撑材料目录执行`./run_pipeline.sh`。可通过CODEX_PYTHON_BIN、CODEX_NODE_BIN指定解释器；原附件根路径配置在config/final.yaml或CUMCM_SOURCE_ROOT。Python依赖见requirements.txt；表格/文档构建还使用已安装的Codex工作区运行时。

压缩交付使用列去重与XZ无损归档，全精度CSV文本不舍入。运行`scripts/unpack_frozen.py`后恢复到配置指定的outputs/c_final_v1/frozen，并逐文件校验原始SHA256；再运行`src/audit/audit_final.py --workbooks`即可独立复验。压缩仅为满足支撑材料体积约束，不丢弃不利结果或实验分支。

## 5. 仍需讨论的模型取舍

已确认的错位、混链、未来信息冷启动、对照不一致及文档缺表已在本轮修复。剩余的是需要明确承认的模型边界：

1. 退费和价格时点存在题意解释空间；论文已列同路径敏感性，不能冒充官方唯一解释。
2. 一月待机启动虽严格可行，经济上保守；若进一步优化一月，应使用可用信息重新运行全年，不能仅把启动末SOC改成更有利数值。
3. 20条历史经验场景、全窗口共同动作及有限期终端惩罚可能偏保守，不能保证未见极端风险或全局最优。
4. S2与S3的差额很小，若要声称更新频次排序稳健，修复顺序应是先增加有明确二级经济含义的选解准则，再做完整年度替代求解器回放；目前只作名义样本比较。

下一轮如继续提升，优先讨论上述结算解释与一月启动目标，其次才是提高预测/风险分布质量和全年排序稳定性。禁止通过挑正式期参数、选择性省略成本或改写实际数据获得更好结果。
'''
    (O/'evidence/闭环修复与独立复验报告.md').write_text(text)
    print('Repair report written')

if __name__=='__main__':main()
