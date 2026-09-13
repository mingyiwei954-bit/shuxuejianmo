"""Current paper evidence tables and original-problem-shaped appendix tables."""
from pathlib import Path
import hashlib,json
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def number(value):
    rounded=Decimal(str(value)).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)
    return '0.0000' if rounded==0 else str(rounded)

def mechanisms(g):
    p=g['p'];out=g['SUPPORT']/'diagnostics'
    accounting=pd.read_csv(out/'cross_model_accounting.csv')
    for comp in ['q3 minus q2','q4_3 minus q4_2']:
        r=accounting[accounting.comparison==comp].iloc[0]
        p(f"在{r.date}，{comp.replace(' minus ','相对')}的实际费用差为{r.final_relative_cost_yuan:.2f}元，其中计划费差{r.plan_cost_yuan:.2f}元、调整费差{r.adjustment_cost_yuan:.2f}元、紧急费差{r.emergency_cost_yuan:.2f}元。这是分项加总的账面解释，不是预报价值的因果估计：两模型同时改变光伏场景中心、历史误差构造及参考合同。更新价值仍须回到共同合同的S0至S3比较。")
    r=pd.read_csv(out/'high_cost_days.csv').query('mode=="q4_2"').iloc[0]
    p(f"波动电价日前模型的最高费用日为{r.date}，费用{r.final_relative_cost_yuan:.2f}元，其中紧急费用{r.emergency_cost_yuan:.2f}元；当日负载{r.load_kwh:.2f}千瓦时、光伏{r.pv_kwh:.2f}千瓦时、区间电价均值{r.mean_price:.4f}元/千瓦时。月度总费与紧急费占比的峰值不在同月，说明采购规模、时点价格和缺口暴露需要分别观察。高影响日期仅用于解释，不回填参数或改写已发布决策。")


def evidence(g):
    p,h,table=g['p'],g['h'],g['table'];root=g['SUPPORT'];out=root/'diagnostics'
    s=pd.read_csv(out/'summary.csv');s=s[s.phase=='formal']
    e=pd.read_csv(out/'effects.csv');e=e[e.phase=='formal']
    def delta(mode,var):return float(e[(e['mode']==mode)&(e.variant==var)].variant_minus_reference_yuan.iloc[0])
    def amount(mode,var):return float(s[(s['mode']==mode)&(s.variant==var)].total_cost_yuan.iloc[0])
    random=pd.read_csv(out/'shuffle_summary.csv').set_index('mode')
    controls=pd.read_csv(out/'reused_mean_controls.csv').set_index('mode')
    h('6.3 模块贡献与连续参数诊断',2)
    p('为分离改进来源，固定原始输入、设备边界和结算解释，分别改变场景配对、残差校准、终端惩罚或采样方式。日前实验允许合同随模型变化，估计完整日前策略的条件效应；日内窗口实验固定原S0合同。所有分支连续传递已执行储电量，统一6000千瓦时首末状态，使用实际结算费用评价，不比较权重不同的优化目标。')
    p('实验方案在运行前锁定。一月一日至七日提供初始历史，八日至三十一日向前验证；二月至十二月为新增事后诊断，未据此修改正式参数。一月验证与一月实际启动账本分开。新增32个方案各完成一段验证期和一段334天正式期连续求解，全部保留；既有均值对照只复核账本。')
    rows=[['改进模块','对照定义','Q2节省/万元','Q4日前节省/万元','代价与证据边界']]
    savings=[float(controls.loc[m,'total_cost_yuan'])-amount(m,'reference') for m in ['q2','q4_2']]
    rows.append(['风险采购','场景折叠为均值',*[f'{v/10000:.2f}' for v in savings],'既有有效对照；场景规模更大'])
    rows.append(['联合配对','保持整条轨迹，打乱跨变量配对',*[f"{random.loc[m,'joint_saving_mean_yuan']/10000:.2f}\n[{random.loc[m,'minimum']/10000:.2f},{random.loc[m,'maximum']/10000:.2f}]" for m in ['q2','q4_2']],'五种子均值及范围；配对影响不分解为各相关系数'])
    rows.append(['残差校准','原始历史场景，倍数固定1',*[f'{delta(m,"raw_history")/10000:.2f}' for m in ['q2','q4_2']],'只改变校准模块；不重新调其余参数'])
    rows.append(['终端近似','仅年末硬约束，软惩罚为0',*[f'{delta(m,"terminal_0")/10000:.2f}' for m in ['q2','q4_2']],'实际费用比较；0并不免除年末恢复'])
    table('module_effects','改进模块的条件贡献及边界',rows,[2.0,3.5,2.7,2.7,5.1])
    p('表中节省为对照费用减基准费用，负值表示该模块在本次对照下反而增加费用；各行对应不同条件实验，不可相加。联合关系实验以负载为锚，对光伏整条日轨迹及波动价格整条轨迹独立置换，保留各变量边际分布和内部时间结构。五个种子为20260913至20260917，每个决策按种子、日期、发布时间和模式确定置换；五次范围不是跨年份置信区间。')
    for m,label in [('q2','固定电价'),('q4_2','波动电价')]:
        a=random.loc[m]
        p(f'{label}下保留联合配对相对打乱配对的平均节省为{a.joint_saving_mean_yuan:.2f}元，五次范围为[{a.minimum:.2f}, {a.maximum:.2f}]元。因果残差相对原始历史的条件节省为{delta(m,"raw_history"):.2f}元，终端软惩罚相对取消该项的条件节省为{delta(m,"terminal_0"):.2f}元。这些数值只描述当前一年、既定其余参数下的实际费用，不证明模块在任意数据或组合下均有优势。')
    rows=[['方案','费用/万元','紧急量/MWh','紧急费/%','未用富余/MWh','吞吐/MWh','优化/s']]
    for m,label in [('q2','Q2'),('q4_2','Q4日前')]:
        for var,name in [('reference','基准'),('raw_history','原始历史'),('terminal_0','终端0')]:
            r=s[(s['mode']==m)&(s.variant==var)].iloc[0]
            rows.append([label+'\n'+name,f'{r.total_cost_yuan/10000:.2f}',f'{r.emergency_kwh/1000:.2f}',f'{100*r.emergency_cost_share:.2f}',f'{r.unused_surplus_kwh/1000:.2f}',f'{r.throughput_kwh/1000:.2f}',f'{r.solver_seconds:.2f}'])
    table('ablation_operation','主要消融方案的实际运行指标',rows,[2.3,2.2,2.2,2.0,2.5,2.5,2.3])
    p('运行指标同时反映采购风险和资源代价：紧急费占比以本方案实际总费用为分母，吞吐为交流侧充放电量之和，未用富余包含未消纳光伏及已付费富余。仅看紧急电量容易忽略过量采购和电池循环，因此按总费用评价经济性，其他指标用于解释。各行可行性均通过，全部候选及五种子明细随机器可读结果交付。')
    validation=pd.read_csv(out/'summary.csv');validation=validation[validation.phase=='validation']
    rows=[['一月验证候选','Q2费用/万元','Q4日前费用/万元','历史可用性']]
    for var,label in [('reference','20条、倍数1'),('count10_span20','10条覆盖20日'),('count10_span10','近期10条'),('count40_span40','最多40条'),('terminal_0','终端倍数0'),('terminal_05','终端倍数0.5'),('terminal_15','终端倍数1.5')]:
        rs=[validation[(validation['mode']==m)&(validation.variant==var)].iloc[0] for m in ['q2','q4_2']]
        rows.append([label,*[f'{r.total_cost_yuan/10000:.2f}' for r in rs],f'实际{int(rs[0].min_actual_scenarios)}—{int(rs[0].max_actual_scenarios)}条'])
    table('validation_parameters','新候选的一月时间向前验证',rows,[4.2,3.5,3.8,4.5])
    p('验证期早段历史有限，最多40条方案实际仅6—29条，不能把这一时期的结果理解为充分历史下40对20的比较。近期10条在一月也较便宜，但它不在原始参数选择网格中；本轮用于提出未来独立验证方向，没有事后把新增候选写成原先已经选定的正式策略。')
    rows=[['参数方案','Q2费用变化/%','Q4日前变化/%','固定项与解释']]
    for var,label,bound in [('count10_span20','10条覆盖20日','从共同20条中等距取10条'),('count10_span10','10条覆盖10日','数量相同但覆盖更近'),('count40_span40','40条覆盖40日','数量及跨度共同变化'),('terminal_0','终端倍数0','取消软价值，保留评价末状态'),('terminal_05','终端倍数0.5','原验证候选'),('terminal_15','终端倍数1.5','原验证候选')]:
        changes=[100*delta(m,var)/amount(m,'reference') for m in ['q2','q4_2']]
        rows.append([label,*[f'{v:+.3f}' for v in changes],bound])
    table('continuous_parameters','连续正式期的参数响应',rows,[3.4,3.0,3.0,6.6])
    p('基准为20条完整历史、终端倍数1。10条覆盖20日与20条覆盖20日比较识别固定候选池内的样本数与稀疏选样效应，不能将经验分布变化完全剥离；10条覆盖10日则改变历史覆盖。40条方案无法将数量与跨度效应完全分离，且二月初可用历史不足40条，实际数量随日志保存。用相对实际费用变化除以相对参数变化给出有限差分弹性，完整记录见连续参数结果；该量是本次离散变动响应，不是处处存在的导数。')
    p('近期10条方案在两种电价下均比原基准便宜，而40条方案更贵；波动电价下终端倍数0.5也略优于1。这说明增加场景或增强惩罚没有单调收益，不能由局部响应推断全年最优。上述正式期结果仅作诊断，仍保留原一月选定的参数。')
    rows=[['日内窗口/h','Q3费用变化/%','Q4滚动变化/%','信息与合同条件']]
    for hours in [18,12]:
        changes=[100*delta(m,f'horizon_{hours}')/amount(m,'horizon_24') for m in ['q3','q4_3']]
        rows.append([str(hours),*[f'{v:+.3f}' for v in changes],'零点仍计划全天；其后仅修改窗口内尚未交付部分'])
    table('horizon_parameters','固定共同合同下的日内窗口比较',rows,[2.4,3.1,3.1,7.4])
    p('窗口候选为12、18、24小时，零点均保留完整24小时以满足全天计划要求。缩短日内窗口时，窗口外既有合同不变，仍只执行至下一个六小时更新点；没有使用24小时以外的预报。与24小时基准的比较属于滚动近似的策略响应，不是改变预报发布日期。')
    r=s[(s['mode']=='q3')&(s.variant=='horizon_12')].iloc[0]
    p(f'18小时窗口的费用变化在两种价格条件下方向不同，12小时窗口则均略高于24小时。对Q3的12小时既有轨迹改用逐次收费，费用为{r.sequential_cost_yuan:.2f}元，比该轨迹最终净额多{r.sequential_cost_yuan-r.total_cost_yuan:.2f}元，提示短窗口下反复调整对结算规则更敏感；这仍是同路径重计费，未重新优化逐次收费制度。')
    p('既有32个固定窗口的288次参数求解另保留于支撑材料。其终端目标变化最大绝对值1.83%不能替代上述共同实际费用比较；功率降低20%时局部目标变化最大15.23%属于设备规格探索，正式功率始终为5000千瓦，未用改变设备后的结果替换答案。')


def efficiency(g):
    p,table=g['p'],g['table'];out=g['SUPPORT']/'diagnostics'
    env=json.loads((out/'environment.json').read_text());s=pd.read_csv(out/'summary.csv');s=s[s.phase=='formal']
    p(f"新增实验使用{env['cpu']}，Python {env['python'].split()[0]}、NumPy {env['numpy']}、SciPy {env['scipy']}及HiGHS {env.get('highs','版本见环境记录')}。实验方案顺序执行，未并行运行多个策略；保持求解器原选项。机器同时承担一般审查工作，时间用于本机复现参考，不当作专用基准测试。未可靠测量峰值内存。")
    rows=[['方案','次数','优化合计/s','中位/ms','95%分位/ms','最大/ms']]
    for mode,var,label in [('q2','reference','Q2基准'),('q4_2','reference','Q4日前基准'),('q2','count40_span40','Q2的40条'),('q4_2','count40_span40','Q4日前40条'),('q3','horizon_24','Q3窗口24h'),('q4_3','horizon_24','Q4滚动24h'),('q3','horizon_12','Q3窗口12h'),('q4_3','horizon_12','Q4滚动12h')]:
        r=s[(s['mode']==mode)&(s.variant==var)].iloc[0]
        rows.append([label,str(int(r.solves)),f'{r.solver_seconds:.2f}',f'{1000*r.median_seconds:.2f}',f'{1000*r.p95_seconds:.2f}',f'{1000*r.max_seconds:.2f}'])
    table('runtime','同环境连续求解的运行时间',rows,[3.4,1.7,2.8,2.7,2.7,2.7])
    acc=json.loads((out/'acceptance_summary.json').read_text())
    p(f"64段方案回放合计{acc['total_solves']}次优化，失败{acc['failures']}次；最大执行层约束与费用残差为{acc['max_physical_residual']:.3g}。这些求解的状态、迭代次数和矩阵残差均已记录；另有48次验证期共同合同准备求解，未单独计时，不包含在上述时间统计内。数据读取耗时{env['data_read_seconds']:.2f}秒；仿真调度、独立审计、导出和文档生成另计，不能将整条流水线耗时全部归给优化器。")
    p('每个窗口有(6+S)T+2个变量，场景供需约束数为ST，稀疏构造的存储及组装量级为O(ST)；其中S为场景数、T为时段数。求解器迭代时间依赖矩阵与退化程度，不能据此宣称整个算法时间复杂度也是O(ST)。所有32个方案的时间分位数与统计均随机器可读结果交付。')


def appendix(g):
    p,h,table=g['p'],g['h'],g['table'];root=g['SUPPORT'];f=root/'outputs/c_final_v1/frozen'
    h('附录',1).paragraph_format.page_break_before=True
    h('附录一 题目规定结构的结果表',2)
    p('以下按题面第一至第三张表的横向结构给出结果。区间购电栏区分零点计划B与最终承诺A，紧急量Q单独列出；实际总购电量为A与Q之和。计划费用仅计pB，全天总费用另含合同调整及紧急费用。单位为千瓦时和元，四位小数只用于展示。')
    for mode,label in [('q1','问题一'),('q2','问题二'),('q3','问题三'),('q4_2','问题四日前'),('q4_3','问题四滚动')]:
        d=pd.read_csv(f/f'{mode}_dispatch.csv',float_precision='round_trip')
        dates=['2025-01-01'] if mode=='q1' else ['2025-03-20','2025-06-21','2025-09-23','2025-12-21']
        for dt in dates:
            z=d[d.date==dt];h(label+' '+dt,3)
            for col,name in [('plan_00_grid_kwh','零点计划')]+([('final_adjusted_grid_kwh','最终承诺')] if mode in ('q3','q4_3') else []):
                rows=[['时间段','购电量','时间段','购电量','时间段','购电量']]
                for hours in [[10,12,14],[16,18,20]]:
                    row=[]
                    for hour in hours:
                        val=z[z.position==hour*6+1][col].iloc[0];row.extend([f'{hour}:00-{hour}:10',number(val)])
                    rows.append(row)
                fee=z.plan_cost_yuan.sum() if col=='plan_00_grid_kwh' and mode in ('q3','q4_3') else z.final_relative_cost_yuan.sum()
                rows.append(['全天'+('计划量' if col=='plan_00_grid_kwh' else '承诺量'),number(z[col].sum()),'', '计划购电费' if col=='plan_00_grid_kwh' and mode in ('q3','q4_3') else '全天总费用',number(fee),''])
                t=table('annex_'+mode+dt+col,'题面表1结构 '+name,rows,[2.7,2.6,2.7,2.7,2.6,2.7])
                t.rows[-1].cells[1].merge(t.rows[-1].cells[2]);t.rows[-1].cells[4].merge(t.rows[-1].cells[5])
            rows=[['时间段','充电量','放电量','时间段','充电量','放电量']]
            for pair in [[0,4],[8,12],[16,20]]:
                row=[]
                for hour in pair:
                    part=z[(z.position>hour*6)&(z.position<=(hour+4)*6)]
                    row.extend([f'{hour}:00-{hour+4}:00',number(part.charge_kwh.sum()),number(part.discharge_kwh.sum())])
                rows.append(row)
            rows.append(['0:00储电量',number(z.soc_start_kwh.iloc[0]),'','24:00储电量',number(z.soc_end_kwh.iloc[-1]),''])
            t=table('annex_storage'+mode+dt,'题面表2结构 储能充放电与端点状态',rows,[2.7,2.6,2.7,2.7,2.6,2.7])
            t.rows[-1].cells[1].merge(t.rows[-1].cells[2]);t.rows[-1].cells[4].merge(t.rows[-1].cells[5])
            p(f'当日紧急购电{z.emergency_kwh.sum():.4f}千瓦时，含紧急量的实际总购电{(z.final_adjusted_grid_kwh+z.emergency_kwh).sum():.4f}千瓦时，全天总费用{z.final_relative_cost_yuan.sum():.4f}元。')
        if mode!='q1':
            groups=[]
            for dt in dates:
                z=d[d.date==dt];entries=[];active=[]
                def emit():
                    a=(active[0].position-1)*10;b=active[-1].position*10
                    entries.append([f'{a//60}:{a%60:02d}-{b//60}:{b%60:02d}',number(sum(r.emergency_kwh for r in active))])
                for r in z.itertuples():
                    if r.emergency_kwh>=.00005:active.append(r)
                    elif active:emit();active=[]
                if active:emit()
                groups.append(entries)
            rows=[sum(([dt,''] for dt in dates),[]),['时间段','购电量']*4]
            for i in range(max(map(len,groups))):rows.append(sum((a[i] if i<len(a) else ['—','—'] for a in groups),[]))
            t=table('annex_emergency'+mode,'题面表3结构 '+label+'指定日期紧急购电',rows,[2.2,1.8]*4)
            for i in range(0,8,2):t.rows[0].cells[i].merge(t.rows[0].cells[i+1])
            for row in t.rows[:2]:row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    h('附录二 支撑文件与完整源码',2).paragraph_format.page_break_before=True
    p('数值重算入口为reproduce.py numeric，原始冻结结果恢复为restore，审计为audit，新增实验为diagnostics，工作簿为workbooks，当前论文为paper；run_pipeline.sh统一转交该入口。数值重算写入独立目录，不覆盖正式冻结答案。具体依赖、环境及命令见README.md。')
    p('正式数据在frozen中无损保存；新增实验方案、配置、逐次求解状态、逐日费用和统计位于diagnostics。完整运行轨迹另存诊断明细包，支撑包提供汇总、日志和可重算源码。现有AI声明及文件保留，真实人工审阅仍为提交前待办。')
    manifest=json.loads((root/'evidence/source_appendix_manifest.json').read_text())
    paths=[x['path'] for x in manifest]
    paths += ['scripts/parameter_perturbation.py','scripts/contribution_experiments.py','scripts/summarize_revision.py','scripts/revision_document.py','scripts/check_revision_delivery.py','tests/test_diagnostics.py','reproduce.py','论文修订源文件/build.py','diagnostics/protocol.json']
    actual=[]
    for path in dict.fromkeys(paths):
        src=root/path
        if not src.exists():raise FileNotFoundError(src)
        digest=hashlib.sha256(src.read_bytes()).hexdigest();actual.append({'path':path,'sha256':digest,'lines':len(src.read_text().splitlines())})
        h(path,3);p('SHA256 '+digest)
        for line in src.read_text().splitlines():g['code_ids'].add(p(line)._p)
    (root/'evidence/source_appendix_manifest_revision.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2))
