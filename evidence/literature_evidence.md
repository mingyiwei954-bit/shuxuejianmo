# C题文献证据与方法边界

版本：paper-agent-v1  
核对日期：2026-09-12  
用途：为论文方法选择、实验设计和参考文献提供可追溯依据。本文只记录论文原文、出版社页面、作者或大学机构页面、软件官方文档和竞赛官方规则。最终论文引用前须由团队逐条打开链接复核作者、题名、刊名、卷期、页码和 DOI。

## 1 证据使用原则

1. 文献只用于说明已有方法和本文设计动机，不能替代对本题数据的实验验证。
2. “原方法”指来源中明确提出或验证的方法；“本文改编”指本项目基于题面和数据自行作出的简化；“未采用”指来源中存在但本项目没有实现的部分。
3. 题目没有给出负载和实时电价预报。正式策略只使用决策时刻以前的观测和当时已经发布的光伏预报。未来实际量只用于时段执行后的结算。
4. 完全信息结果只作为事后参照。在目标函数、约束、日期和 SOC 端点一致时，才可以称为对应可执行策略的完全信息下界。
5. 所有最终数值必须从冻结结果清单自动注入。本文档不把当前审计原型的数字当成最终竞赛结果。

## 2 文献证据矩阵

| 编号 | 一手或官方来源 | 来源中的可核对内容 | 本文改编及使用位置 | 不应作出的表述 |
|---|---|---|---|---|
| L1 | Parisio A, Rikos E, Glielmo L. A Model Predictive Control Approach to Microgrid Operation Optimization. *IEEE Transactions on Control Systems Technology*, 2014, 22(5): 1813-1827. DOI: 10.1109/TCST.2013.2295737. [曼彻斯特大学作者成果页](https://research.manchester.ac.uk/en/publications/a-model-predictive-control-approach-to-microgrid-operation-optimi/) | 该文把微网运行的在线优化写成 MPC 框架，在满足时变需求和运行约束的同时调度发电、储能和外网交换；原文使用 MILP，并在实验微网上验证。 | 本文采用滚动时域思想：0、6、12、18 时重新求解 24 h 预测窗口，只执行下一个 6 h 块。由于本题不含机组启停，核心模型保持为 LP。用于“问题三模型”和“跨日滚动设计”。 | 不得写“完全复现 Parisio 算法”；本文没有其机组逻辑、网络潮流和实验设备，也没有证明相同的控制性能。 |
| L2 | Mayne D Q, Rawlings J B, Rao C V, Scokaert P O M. Constrained Model Predictive Control: Stability and Optimality. *Automatica*, 2000, 36(6): 789-814. DOI: 10.1016/S0005-1098(99)00214-9. [Elsevier 出版社页面](https://www.sciencedirect.com/science/article/pii/S0005109899002149) | 该综述把 MPC 描述为：以当前状态作为初始状态求有限时域最优控制序列，并实施序列中的首个控制；讨论了终端约束、终端费用和预测时域对稳定性与最优性的作用。 | 本文用该思想解释为什么短视窗末端不能免费放空储能，并比较每日闭环、24 h 首尾相同、软目标 6000 kWh 三种终端处理。本文实施的是下一个 6 h 块，不是单采样点。 | 不得声称本文由该文的定理保证闭环稳定。我们的目标、执行块长度和软惩罚选择均为本题改编，稳定性以可行性和 SOC 连续性实证检查为准。 |
| L3 | Olivares D E, Lara J D, Cañizares C A, Kazerani M. Stochastic-Predictive Energy Management System for Isolated Microgrids. *IEEE Transactions on Smart Grid*, 2015, 6(6): 2681-2693. DOI: 10.1109/TSG.2015.2469631. [作者所在大学全文](https://uwaterloo.ca/scholar/sites/ca.scholar/files/ccanizar/files/daniel_stochasticems.pdf) | 该文提出两阶段决策与滚动时域结合的随机预测微网能量管理系统，并把确定性方案作为对照。 | 本文的场景模型只要求第一执行块的购电与充放电决策跨场景一致，之后允许按场景递补，目标为场景等概率期望费用。用于“三项增强”中的场景滚动。 | 不得称本文复现其随机 MILP 或非线性潮流；本题模型是单节点能量平衡 LP，且不含风险厌恶项。 |
| L4 | Birge J R, Louveaux F. *Introduction to Stochastic Programming*. Springer. [Springer 出版社页面](https://link.springer.com/book/10.1007/b97617) | 出版社目录明确包含两阶段线性递补、多阶段随机规划、期望近似与抽样方法。 | 用于解释“当前不可更改的第一阶段决策”和“未来可随场景调整的递补决策”的一般结构。本文把第一阶段定为未来 6 h 执行块。 | 不得把有限的历史场景数解释成概率分布已经被一致估计；本文必须同时报告场景数量、来源日期和覆盖不足。 |
| L5 | Pinson P, Madsen H, Nielsen H A, Papaefthymiou G, Klöckl B. From Probabilistic Forecasts to Statistical Scenarios of Short-term Wind Power Production. *Wind Energy*, 2009, 12(1): 51-62. DOI: 10.1002/we.284. [DTU 作者机构预印本](https://backend.orbit.dtu.dk/ws/files/4900902/pinsonetal_wpfscenarios_fin.pdf) | 原文指出，逐提前期的边际概率预报不足以表达预测误差随时间的发展；用于多阶段决策的场景应保留不同提前期误差之间的依赖结构。原方法通过变换和协方差矩阵生成统计场景。 | 本文不做高斯变换，而是按同一发布时间抽取最近最多 20 条完整历史残差轨迹，借由整条轨迹的共同抽样保留样本内时间相关性。用于“场景构造”。 | 不得把本文方法称为 Pinson 场景生成法；本文只是采用“保留跨提前期依赖”的设计原则。也不得把风电案例的实证结论直接推广到本题光伏。 |
| L6 | Hyndman R J, Athanasopoulos G. *Forecasting: Principles and Practice*, 3rd ed. [作者维护的 OTexts：简单预测方法](https://otexts.com/fpp3/simple-methods.html)；[时间序列交叉验证](https://otexts.com/fpp3/tscv.html)；[残差自助法](https://otexts.com/fpp3/prediction-intervals.html) | 作者页面给出历史均值、季节朴素等基准，并强调滚动预测原点的训练集只能包含预测时刻以前的观测；残差重采样可形成未来可能路径，但逐点残差自助法以残差不相关、方差稳定为前提。 | 本文把“过去四个同星期日的平均曲线”定义为移动窗口季节均值基线；1 月只用于参数选择，2-12 月采用滚动原点评估。光伏残差均值校正按发布时间与提前期分组，只使用过去 28 天。 | 不得把“四个同星期日均值”称为季节朴素法；它是本文定义的季节均值基线。完整轨迹重采样也不同于来源中的逐点残差自助法。 |
| L7 | Künsch H R. The Jackknife and the Bootstrap for General Stationary Observations. *The Annals of Statistics*, 1989, 17(3): 1217-1241. DOI: 10.1214/aos/1176347265. [Project Euclid 原文页](https://projecteuclid.org/journals/annals-of-statistics/volume-17/issue-3/The-Jackknife-and-the-Bootstrap-for-General-Stationary-Observations/10.1214/aos/1176347265.full)；[作者论文目录](https://people.math.ethz.ch/~hkuensch/papers/) | 原文把 jackknife 与 bootstrap 扩展到平稳序列，通过连续数据块重采样保留序列依赖，并给出相应渐近条件。 | 本文对逐日策略费用差使用 7 天移动块自助法区间，以一周为块保留周内相关。块长 7 天是结合本题周周期作出的预注册选择。 | 不得声称 334 天样本、季节变化和固定 7 天块必然满足原文的全部渐近条件。区间应称经验不确定性区间，并与逐月差异同时报告。 |
| L8 | Sioshansi R, Denholm P, Jenkin T, Weiss J. Estimating the Value of Electricity Storage in PJM: Arbitrage and Some Welfare Effects. *Energy Economics*, 2009, 31(2): 269-277. DOI: 10.1016/j.eneco.2008.10.005. [Elsevier 出版社页面](https://www.sciencedirect.com/science/article/pii/S0140988308001631) | 该文研究价格接受者储能在 PJM 市场的套利价值，并考察效率、储能容量等因素；其估值使用历史价格和完全预见设定。 | 用于解释储能通过低价充电、高价放电进行能量时移，以及为何完全信息套利值只适合作事后参照。 | 不得把该市场研究的收益率直接套到本题；本题没有售电收益，且费用函数含紧急购电和调整违约。 |
| L9 | SciPy 1.16.2 `linprog` 与 HiGHS 方法文档。[SciPy 线性规划总页](https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.optimize.linprog.html)；[SciPy HiGHS 方法页](https://docs.scipy.org/doc/scipy-1.16.2/reference/optimize.linprog-highs.html)；[HiGHS 官方选项表](https://ergo-code.github.io/HiGHS/dev/options/definitions/) | 官方文档列出 `highs`、对偶单纯形和内点法入口，以及原始可行性、对偶可行性和 IPM 最优性容差等选项。 | 本文用 HiGHS、HiGHS-DS、HiGHS-IPM和三种并列破除系数重复 S2/S3；保存状态、目标、原始/对偶残差、迭代数和运行时间。 | 不得仅以“返回 Optimal”证明微小费用差可靠。若方法间方向或分币结果不一致，结论必须写为“数值不可区分”。 |
| L10 | 全国大学生数学建模竞赛组委会. [论文格式规范（2026年修订稿）](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html) | 电子论文为单一 PDF 或 Word，建议 PDF，正文不超过 30 页，电子版第一页为摘要，不含承诺书和编号页；论文与支撑材料均不得出现身份和学校信息；支撑材料 ZIP/RAR 不超过 20 MB。 | 用作最终排版、压缩和匿名检查的唯一竞赛格式依据。 | 不得把本地旧版 `format2026.doc` 以外的非官方模板要求当作全国统一强制项。 |
| L11 | 全国大学生数学建模竞赛组委会. [人工智能工具使用规定（2026年试行）](https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html) | 使用 AI 时须在参考文献前设置规定声明；支撑材料包含文件名为 `AI工具使用详情.pdf` 的说明，记录工具/型号、用途、主要提示与过程、采纳/人工修改/核验；核心建模由团队主导并逐项人工审查。 | 用于论文声明、AI 详情模板和最终人工签字检查。 | 不得省略其他 AI、未知模型或未采纳输出；模型版本无法核实时应如实标为“待从界面/日志补录”。 |

## 3 本文方法的可引用定位

### 3.1 确定性线性规划

本题的能量平衡、储能状态转移、容量与功率约束均为线性关系，费用中的上调、下调和紧急购电也可用非负变量分解为分段线性项。因此，在不显式加入充放电互斥二进制变量时，问题一至问题四的各次规划可以写成 LP。文献 L8 支持储能能量时移的经济动机，L9 支持求解器和数值复核方法。LP 结构本身来自题目约束的代数整理，不是照搬某篇文献。

### 3.2 因果滚动控制

文献 L1-L2 支持“用当前状态重新求有限时域最优序列并实施近期决策”的滚动时域框架。本文把重规划时刻固定为题面给出的 0、6、12、18 时，窗口为未来 24 h，只执行到下一次重规划。下一日购电在午夜前仅为预览，却可通过预测期内的终端状态影响本日储能选择。本文不以 MPC 理论替代因果审计：每个决策版本仍须保存历史截止日、预报发布时间、有效时段和承诺链。

### 3.3 终端状态处理

文献 L2 说明有限预测时域需要认真处理末端状态或末端费用。本文不主张某一种终端规则先验正确，而是预注册三种可比方案：每日 6000 kWh 闭环、24 h 首尾 SOC 相同、对 6000 kWh 偏差施加软惩罚。软惩罚的 0.5、1、1.5 倍预测价格中位数只用 1 月滚动验证选择，正式 2-12 月期间不得重新选择。

### 3.4 光伏偏差校正

文献 L6 支持按滚动预测原点评估，以及从历史预测误差中诊断系统偏差。本文的具体校正公式是自定义的：按“发布时间 × 提前小时”对过去 28 天残差取均值，加到当前原始预报；随后截断为非负，并用过去 60 天相同时钟小时实际光伏的 99.5% 分位数作上界。28 天、60 天和 99.5% 都是实验参数，不应归因于 L6。

### 3.5 历史残差场景与非预见性

文献 L3-L5说明，多阶段调度需要同时表达预测不确定性与跨提前期依赖，并区分当前决策和未来递补。本文从决策时刻以前、相同发布时间的记录中，选择最近最多 20 条完整残差轨迹。每条轨迹作为一个等概率场景；第一个 6 h 块的计划购电、充电和放电在所有场景中相同，后续变量按场景分开。这个经验方案保留被抽取轨迹内部的时间相关，但没有估计连续概率分布，也没有场景削减。

### 3.6 相关数据的不确定性区间

年度逐日费用差不是独立样本。文献 L7 支持使用连续数据块重采样处理相关序列。本文固定 7 天移动块，循环拼接到 334 天，重采样次数从配置读取，区间取 2.5% 与 97.5% 分位数。报告时同时给出全年总差、月度差和区间；该区间反映历史日序列重采样的不确定性，不等同于未来年度预测区间。

## 4 未采用但可在局限性中说明的方法

- 未建立网络潮流、节点电压、无功功率和线路约束。题面把微网抽象为单节点能量调度，本文不额外虚构电气网络。
- 未建立电池老化、温度或循环寿命成本。题目只给容量、功率和效率参数。
- 未使用深度学习光伏/负载预测。只有 31 天训练期可用于第一次正式决策，复杂模型容易引入不透明的参数选择，且不利于因果审计。
- 未采用 CVaR 或最坏情形目标。场景模型按计划固定为等概率期望费用，风险厌恶只作为可讨论的后续扩展。
- 未复现文献 L5 的高斯变量变换与协方差递推；使用历史整轨迹重采样以减少模型假设并便于追踪每个场景的来源日期。
- 未声称 18:00 更新无一般价值。只有在多求解器复算和分币稳定后，才能就本数据、本模型和本结算口径报告其边际费用差；否则写为“数值不可区分”。

## 5 建议的论文参考文献格式

[1] Parisio A, Rikos E, Glielmo L. A model predictive control approach to microgrid operation optimization[J]. IEEE Transactions on Control Systems Technology, 2014, 22(5): 1813-1827. DOI: 10.1109/TCST.2013.2295737.

[2] Mayne D Q, Rawlings J B, Rao C V, et al. Constrained model predictive control: Stability and optimality[J]. Automatica, 2000, 36(6): 789-814. DOI: 10.1016/S0005-1098(99)00214-9.

[3] Olivares D E, Lara J D, Cañizares C A, et al. Stochastic-predictive energy management system for isolated microgrids[J]. IEEE Transactions on Smart Grid, 2015, 6(6): 2681-2693. DOI: 10.1109/TSG.2015.2469631.

[4] Birge J R, Louveaux F. Introduction to Stochastic Programming[M]. New York: Springer, 1997. DOI: 10.1007/b97617.

[5] Pinson P, Madsen H, Nielsen H A, et al. From probabilistic forecasts to statistical scenarios of short-term wind power production[J]. Wind Energy, 2009, 12(1): 51-62. DOI: 10.1002/we.284.

[6] Hyndman R J, Athanasopoulos G. Forecasting: Principles and Practice[M/OL]. 3rd ed. Melbourne: OTexts, 2021. https://otexts.com/fpp3/.

[7] Künsch H R. The jackknife and the bootstrap for general stationary observations[J]. The Annals of Statistics, 1989, 17(3): 1217-1241. DOI: 10.1214/aos/1176347265.

[8] Sioshansi R, Denholm P, Jenkin T, et al. Estimating the value of electricity storage in PJM: Arbitrage and some welfare effects[J]. Energy Economics, 2009, 31(2): 269-277. DOI: 10.1016/j.eneco.2008.10.005.

[9] SciPy Developers. `scipy.optimize.linprog` and HiGHS methods[EB/OL]. SciPy 1.16.2 documentation. https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.optimize.linprog.html.

[10] 全国大学生数学建模竞赛组委会. 全国大学生数学建模竞赛论文格式规范（2026年修订稿）[EB/OL]. https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html.

[11] 全国大学生数学建模竞赛组委会. 全国大学生数学建模竞赛人工智能工具使用规定（2026年试行）[EB/OL]. https://www.mcm.edu.cn/html_cn/node/fef94648f2836ab6cc81586f4c38512b.html.

## 6 人工复核记录

以下各项在最终提交前由团队成员填写，不得由 AI 代签。

| 检查项 | 复核人 | 日期 | 结果 | 备注 |
|---|---|---|---|---|
| DOI、卷期和页码与原始页面一致 |  |  |  |  |
| 正文每个文献编号均有实际引用 |  |  |  |  |
| 没有把本文改编写成文献原方法 |  |  |  |  |
| 没有把风电结论直接当作光伏结论 |  |  |  |  |
| 软件版本与最终运行环境一致 |  |  |  |  |
| 竞赛格式和 AI 规则链接在提交日仍有效 |  |  |  |  |
