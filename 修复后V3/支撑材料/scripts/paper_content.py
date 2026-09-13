from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import json,re
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'outputs/c_final_v1/frozen'

def fmt(x,places=2):
    rounded=Decimal(str(float(x))).quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
    return format(abs(rounded) if rounded==0 else rounded,f',.{places}f')

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def emergency(z):
    groups=[];active=[]
    def add():
        a=(active[0].position-1)*10;b=active[-1].position*10;groups.append([f'{a//60}:{a%60:02d}-{b//60}:{b%60:02d}',fmt(sum(x.emergency_kwh for x in active),4)])
    for x in z.itertuples():
        if x.emergency_kwh>=.00005:active.append(x)
        elif active:add();active=[]
    if active:add()
    return groups

def specified():
    lines=[];checks=[]
    for mode in ['q1','q2','q3','q4_2','q4_3']:
        d=pd.read_csv(F/f'{mode}_dispatch.csv');days=['2025-01-01'] if mode=='q1' else ['2025-03-20','2025-06-21','2025-09-23','2025-12-21']
        for day in days:
            z=d[d.date==day].sort_values('position');lines.append(f'#### {mode.upper()} {day} 指定结果')
            rows=[]
            for h in [10,12,14,16,18,20]:
                physical=f'{h:02d}:00-{h:02d}:10';selected=z[z.physical_interval==physical]
                if len(selected)!=1:raise ValueError('Nonunique physical interval')
                x=selected.iloc[0];rows.append([physical,fmt(x.plan_00_grid_kwh,4),fmt(x.final_adjusted_grid_kwh,4)])
                checks.append(dict(mode=mode,date=day,kind='ten_minute',key=physical,plan_grid=float(x.plan_00_grid_kwh),final_grid=float(x.final_adjusted_grid_kwh)))
            lines.append(table(['物理区间','0点计划量','最终承诺量'],rows))
            lines.append(table(['全天计划量','全天最终量','全天总购电费'],[[fmt(z.plan_00_grid_kwh.sum(),4),fmt(z.final_adjusted_grid_kwh.sum(),4),fmt(z.final_relative_cost_yuan.sum())]]))
            rows=[]
            for b in range(6):
                zz=z[(z.position>b*24)&(z.position<=(b+1)*24)];span=f'{b*4}:00-{(b+1)*4}:00';rows.append([span,fmt(zz.charge_kwh.sum(),4),fmt(zz.discharge_kwh.sum(),4)]);checks.append(dict(mode=mode,date=day,kind='four_hour',key=span,charge=float(zz.charge_kwh.sum()),discharge=float(zz.discharge_kwh.sum())))
            lines.append(table(['物理区间','充电量','放电量'],rows));lines.append(table(['0点SOC','24点SOC'],[[fmt(z.soc_start_kwh.iloc[0],4),fmt(z.soc_end_kwh.iloc[-1],4)]]))
            if mode!='q1':lines.append(table(['紧急购电物理区间','紧急购电量'],emergency(z) or [['无正缺口','0.0000']]))
    (F/'paper_specified_values.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    return '\n\n'.join(lines)

def generate():
    cfg=json.loads((F/'resolved_config.json').read_text());exp=pd.read_csv(F/'experiment_summary.csv');official=pd.read_csv(F/'official_summary.csv');training=pd.read_csv(F.parent/'evidence/january_parameter_validation.csv');perfect=pd.read_csv(F/'perfect_information_summary.csv');jan=pd.read_csv(F/'startup_summary.csv');ci=pd.read_csv(F/'comparison_stats.csv');settle=pd.read_csv(F/'settlement_sensitivity.csv');solver=pd.read_csv(F/'solver_instance_sensitivity.csv');audit=json.loads((F.parent/'audit/independent_validation.json').read_text());q1=pd.read_csv(F/'q1_dispatch.csv')
    def row(mode,scenario='S0',arm='joint_empirical'):
        z=exp[(exp['mode']==mode)&(exp.scenario==scenario)&(exp.model_arm==arm)]
        if len(z)!=1:raise ValueError((mode,scenario,arm,len(z)))
        return z.iloc[0]
    values={'Q1_COST':fmt(q1.final_relative_cost_yuan.sum()),'Q2_COST':fmt(row('q2').final_relative_cost_yuan),'Q42_COST':fmt(row('q4_2').final_relative_cost_yuan),'Q3_DIFF':fmt(row('q3','S3').final_relative_cost_yuan-row('q3').final_relative_cost_yuan),'Q43_DIFF':fmt(row('q4_3','S3').final_relative_cost_yuan-row('q4_3').final_relative_cost_yuan),'SELECTED_MODEL':{'raw_history':'原始历史联合场景','causal_residual':'逐日前推因果残差场景'}[cfg['forecast']['scenario_model']],'SELECTED_MULT':str(cfg['rolling']['selected_soft_penalty_multiplier'])}
    baseline=float(np.sum(q1.settlement_price*np.maximum(q1.actual_load_kwh-q1.actual_pv_kwh,0)))
    values['Q1_TABLE']=table(['方案','全天购电量','全天费用'],[['储能LP',fmt(q1.plan_00_grid_kwh.sum(),4),values['Q1_COST']],['无储能',fmt(np.maximum(q1.actual_load_kwh-q1.actual_pv_kwh,0).sum(),4),fmt(baseline)]])
    tr=training.groupby(['scenario_model','penalty_multiplier']).final_relative_cost_yuan.sum();values['TRAIN_TABLE']=table(['场景候选','惩罚倍数','四模式一月验证合计费用'],[[sm,str(mult),fmt(cost)] for (sm,mult),cost in tr.items()])
    rows=[]
    for mode in ['q2','q4_2']:
        for arm,label in [('joint_empirical','联合场景风险采购'),('mean_forecast','均值预测'),('no_storage','无储能')]:
            r=row(mode,arm=arm);rows.append([mode,label,fmt(r.final_relative_cost_yuan),fmt(r.emergency_kwh,4)])
        p=perfect[perfect['mode']==mode].iloc[0];rows.append([mode,'完全信息事后下界',fmt(p.purchase_cost_yuan),'0.0000'])
    values['RISK_TABLE']=table(['模式','方案','正式期总费用','紧急购电量'],rows)
    values['SETTLEMENT_TABLE']=table(['模式','最终净额','同链逐次','不退原价同路径'],[[r['mode'],fmt(r.main_cost),fmt(r.same_chain_sequential_cost),fmt(r.no_refund_same_path_cost)] for _,r in settle.iterrows()])
    values['STARTUP_TABLE']=table(['模式','一月启动费用','一月末SOC','二月初SOC'],[[r['mode'],fmt(r.cost_yuan),fmt(r.terminal_soc_kwh,4),fmt(pd.read_csv(F/f'{r["mode"]}_dispatch.csv').soc_start_kwh.iloc[0],4)] for _,r in jan.iterrows()])
    values['OFFICIAL_TABLE']=table(['模式','计划费','调整净费','紧急费','总费用'],[[r['mode'],fmt(r.plan_cost_yuan),fmt(r.adjustment_cost_yuan),fmt(r.emergency_cost_yuan),fmt(r.final_relative_cost_yuan)] for _,r in official.iterrows()])
    values['SCHEDULE_TABLE']=table(['模式','时点策略','主费用','逐次费用','紧急购电量'],[[mode,sc,fmt(row(mode,sc).final_relative_cost_yuan),fmt(row(mode,sc).sequential_cost_yuan),fmt(row(mode,sc).emergency_kwh,4)] for mode in ['q3','q4_3'] for sc in ['S0','S1','S2','S3']])
    statements=[]
    for mode in ['q3','q4_3']:
        costs={sc:float(row(mode,sc).final_relative_cost_yuan) for sc in ['S0','S1','S2','S3']};winner=min(costs,key=costs.get);diff=costs['S3']-costs['S0'];statements.append(f'{mode.upper()}在本样本共同日前合同下，主费用最低为{winner}，费用{fmt(costs[winner])}元；S3相对S0'+('增加' if diff>=0 else '减少')+f'{fmt(abs(diff))}元。该差额来自本算法在更新信息下选择的后续采购和储能，不能推广成信息本身必然有害或必然有益。')
    values['SCHEDULE_NARRATIVE']='\n\n'.join(statements);values['CI_TABLE']=table(['模式','比较','配对差额','95%区间下端','95%区间上端'],[[r['mode'],r.comparison,fmt(r.difference_yuan),fmt(r.ci_low),fmt(r.ci_high)] for _,r in ci.iterrows()])
    values['SOLVER_NARRATIVE']=f'共完成{len(solver)}次固定实例复求。相对HiGHS自动法的目标最大绝对差为{solver.objective_difference_vs_highs.abs().max():.6g}元，窗口采购量最大L1差为{solver.grid_l1_difference.max():.6g} kWh；最大SOC递推残差为{solver.soc_residual.max():.3e} kWh。目标接近而动作不一致时应视为并列解敏感性，全年策略排序仍需额外完整回放才能确认。'
    failures=[c for c in audit['checks'] if c['status']!='PASS'];values['AUDIT_NARRATIVE']=f'本轮独立检查共{len(audit["checks"])}项，失败{len(failures)}项。检查覆盖逐时段原数据匹配、物理区间、设备边界、真实缺口及费用、正式承诺连续性、共同日前合同和一月衔接。测试还覆盖未来观测隔离、分段状态不重置、不同充放电效率和年末边界。该结果是所列检查范围内的证据，不是模型最优性或外推有效性的证明。'
    if failures:raise RuntimeError('Refusing to publish paper over failed independent checks')
    values['SPECIFIED_TABLES']=specified();values['REPRODUCTION_TABLE']=table(['证据','位置'],[['正式明细','frozen/q*_dispatch.csv（解包后）'],['真实承诺链','frozen/decision_versions.csv（解包后）'],['训练与解析配置','evidence/january_parameter_validation.csv及frozen/resolved_config.json'],['独立复核','audit/independent_validation.json'],['源码与输入校验','evidence/source_provenance.json'],['可执行入口','run_pipeline.sh'],['数学约束测试','tests/test_closed_loop.py']])
    text=(ROOT/'paper/main.md').read_text()
    for key,val in values.items():text=text.replace('{{'+key+'}}',val)
    if re.search(r'\{\{[^}]+\}\}',text):raise ValueError('Unresolved result macro')
    ai='''# AI工具使用详情

## 使用范围与责任边界

本轮在OpenAI Codex任务中使用基于GPT-6的智能体，辅助独立复核、程序修订、实验组织、数值审计及文档生成。此前会话的具体模型版本无法由现存材料完整验证，未猜填。用户于本轮明确授权修复，并要求使用真实数据、避免未来信息泄漏、遵守数学模型约束。

## 输入与操作

输入包括原题PDF、附件1至5、V3源码与交付文件、两份历史审查报告。本轮保留修订前快照，停止旧模型后台重算后建立新的正式运行。核心改动包括因果联合场景、共享决策约束、真实承诺逐次计费、共同日前计划比较、可核验一月启动、物理时间抽取及独立交付校验。

## 数据与预测

原始观测不作伪造或未来回填。残差场景由已观测历史构造，属于明确标记的预测分布；移动块重采样用于统计区间，不当作新观测数据。没有历史时不使用当天实际曲线预测当天。一月训练选择完成后再评价二月至十二月。

## 可核查记录

运行日志位于logs；配置为frozen/resolved_config.json；训练表为evidence/january_parameter_validation.csv；一月和正式期轨迹、各策略承诺均位于frozen；独立复算位于audit；源码与原始输入哈希在evidence/source_provenance.json；数学约束和反事实测试见tests/test_closed_loop.py。

## 尚需人工审阅的内容

退费和交付时段价格是题意解释，不能冒充额外给定的市场规则。经验场景与有限窗口不保证覆盖所有极端情形。团队需人工审阅假设、策略选择、公式、程序、引文与最终提交要求。本文件只登记可验证的本轮操作，不声称此前全部记录已恢复，也不声称已完成团队签核。
'''
    return text,ai
