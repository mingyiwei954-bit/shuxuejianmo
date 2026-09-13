from pathlib import Path
import json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'outputs/c_final_v1';R=F/'research'

def main():
    v=json.loads((F/'final_validation_v3.json').read_text())
    a=pd.read_csv(R/'annual_solver_comparison.csv');b=pd.read_csv(R/'block_sensitivity.csv')
    text='''# V3研究论证与提交格式修订报告

本次保留原正式模型及五份工作簿，补充独立诊断并修订论文。新增实验是在已查看正式结果后明确登记的诊断，不作为新的盲测或调参集；不因替代求解器的费用更低而替换正式结果。

## 实际新增工作

1. 两种电价下S2、S3各完成一次连续334天内点法回放，合计192384个十分钟执行时段。共同日前合同、初始SOC及模型参数固定；新增每段动作从原始附件独立复核供需、费用、SOC、功率和端点。
2. 计算四种模式的月度分解、预测误差、紧急时段比例、最高日费和上尾17日均费；以3/7/14/28天块长度重复检验S3相对S0和S2的费用差。
3. 论文补充方法来源、储能互斥变换的证明、信息价值与实现费用的区别；加入真实出版物引文及结果解释。
4. 摘要与正文分页，图表连续编号，源码逐文件完整收入附录，并检查其每一行与实际程序一致。代码原文件仍以支撑材料内版本运行。

## 全年替代求解器费用

| 模式 | 方法 | S2/元 | S3/元 | S3减S2/元 |
|---|---|---:|---:|---:|
'''
    for (mode,method),g in a.groupby(['mode','method'],sort=False):
        x=g.set_index('scenario').cost;text+=f'|{mode}|{method}|{x.S2:,.6f}|{x.S3:,.6f}|{x.S3-x.S2:,.6f}|\n'
    text+='''
两种求解方法下S2均略低于S3，但费用差的大小发生变化；原正式轨迹的S3减S2在全部四个块长度下区间均跨零。故保留日内更新相对S0的样本证据，不把18点更新或S2/S3的微小排序写成稳定的一般结论。

## 复核与状态

'''
    text+=f'文档及交付检查状态：{v["status"]}；共{len(v["checks"])}项。论文PDF共{v["metrics"]["pdf_pages"]}页，含完整源码附录；正文页数与摘要分页另有专门检查。数值复核记录见audit/independent_validation.json，补充实验复核见research/annual_independent_checks.json。\n'
    text+='''
新增参考书为75页扫描PDF，本轮实际查看目录与优化、检验、评价和附录相关页；采用其要求给出实证检验和完整来源的方向，不采用示例数据、保证获奖和缺乏依据的固定格式阈值。原有参考书未复制到交付包。

## 仍需真实人工完成的事项

本轮不承诺分数或奖项。参赛队员须独立核对题意、推导、代码、数值与AI采用记录，按真实贡献确认人工主导及符合本年度参赛规则；当前没有证据证明该人工核验已完成。AI使用详情如实说明AI参与核心修订。单年历史场景、保守一月启动和交易时刻电价解释仍是模型限制。格式检查通过不能覆盖参赛资格、队员主导、匿名及其他纪律要求。

本轮所有路径调整仅为可移植配置，未修改原始观测；正式结果与上次交付的差异核对见交付清单。支撑包中的完整源码与压缩轨迹可恢复复算。
'''
    (F/'evidence/本轮研究与交付修订报告.md').write_text(text)
    print('Improvement report written')

if __name__=='__main__':main()
