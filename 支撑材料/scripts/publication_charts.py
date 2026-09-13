"""Rebuild Chinese publication charts from frozen results; never run optimization."""
from pathlib import Path
import hashlib, json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
F = ROOT / 'outputs/c_final_v1/frozen'
OUT = ROOT / '论文修订源文件/figures'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    font = os.environ.get('CHART_FONT')
    mac = Path('/Applications/Microsoft Excel.app/Contents/Resources/DFonts/SimHei.ttf')
    if not font and mac.exists(): font = str(mac)
    if font:
        fm.fontManager.addfont(font)
        family = fm.FontProperties(fname=font).get_name()
    else:
        path = fm.findfont('SimHei', fallback_to_default=False)
        family = fm.FontProperties(fname=path).get_name()
    plt.rcParams.update({'font.family':family,'font.size':13,'axes.unicode_minus':False,
        'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160,
        'savefig.dpi':300,'axes.linewidth':0.8,'legend.frameon':False})
    OUT.mkdir(exist_ok=True)
    inputs = [F/'experiment_summary.csv',F/'q3_dispatch.csv',ROOT/'research/monthly_mechanisms.csv']
    def finish(fig, name):
        fig.savefig(OUT/(name+'.png'),bbox_inches='tight',facecolor='white')
        plt.close(fig)
    names = {'q2':'问题2','q4_2':'问题4-2','q3':'问题3','q4_3':'问题4-3'}
    colors = {'q2':'#4c72b0','q4_2':'#dd8452','q3':'#55a868','q4_3':'#c44e52'}
    raw = pd.read_csv(F/'experiment_summary.csv',float_precision='round_trip')
    joint = raw[raw.model_arm=='joint_empirical']
    # Annual strategy values use February--December and final-net settlement.
    fig,axes = plt.subplots(1,2,figsize=(9,3.55),layout='constrained')
    totals = {}
    for ax,mode in zip(axes,['q3','q4_3']):
        z=joint[joint['mode']==mode].sort_values('scenario');y=z.final_relative_cost_yuan.to_numpy()/10000
        assert list(z.scenario)==['S0','S1','S2','S3']
        ax.plot(np.arange(4),y,'o-',color=colors[mode],lw=2,ms=6)
        ax.set_xticks(np.arange(4),z.scenario);ax.set_xlim(-0.2,3.35)
        ax.set_ylim(y.min()-4,y.max()+5);ax.set_title(names[mode]);ax.set_ylabel('正式期费用（万元）')
        ax.grid(axis='y',alpha=.17);ax.ticklabel_format(axis='y',style='plain',useOffset=False)
        for i,v in enumerate(y):ax.annotate(f'{v:.2f}',(i,v),xytext=(0,9),textcoords='offset points',ha='center',fontsize=11)
        delta=float(z.final_relative_cost_yuan.iloc[-1]-z.final_relative_cost_yuan.iloc[-2])
        ax.text(.04,.07,f'S3比S2多 {delta:.2f} 元',transform=ax.transAxes,fontsize=11)
        totals[mode]={'S3_minus_S2_yuan':delta,'costs_yuan':list(z.final_relative_cost_yuan)}
    finish(fig,'frequency')
    # Monthly plotting uses yuan / 10000; it must not label million-yuan numbers as 万元.
    monthly=pd.read_csv(ROOT/'research/monthly_mechanisms.csv',float_precision='round_trip')
    fig,axes=plt.subplots(2,1,figsize=(9,5.3),sharex=True,layout='constrained')
    for mode in names:
        z=monthly[monthly['mode']==mode].sort_values('month');x=z.month.str[-2:].astype(int)
        assert list(x)==list(range(2,13))
        target=joint[(joint['mode']==mode)&(joint.scenario==('S3' if mode in ['q3','q4_3'] else 'S0'))].iloc[0]
        assert abs(z.cost.sum()-target.final_relative_cost_yuan)<1e-5
        axes[0].plot(x,z.cost/10000,'o-',color=colors[mode],label=names[mode],lw=1.8,ms=4)
        axes[1].plot(x,100*z.emergency_cost/z.cost,'o-',color=colors[mode],lw=1.8,ms=4)
    axes[0].set_ylabel('月度费用（万元）');axes[0].legend(ncol=4,fontsize=11,loc='upper left')
    axes[1].set_ylabel('紧急购电费占比（%）');axes[1].set_xticks(range(2,13),[f'{m}月' for m in range(2,13)])
    axes[1].set_xlabel('2025年正式期');axes[1].set_xlim(1.8,12.2)
    for ax in axes:ax.grid(axis='y',alpha=.17)
    finish(fig,'monthly')
    # Ten-minute energy and start-of-interval SOC; append the actual 24:00 state.
    z=pd.read_csv(F/'q3_dispatch.csv',float_precision='round_trip');z=z[z.date=='2025-06-21'].sort_values('position')
    assert len(z)==144
    h=(z.position.to_numpy()-1)/6
    fig,axes=plt.subplots(2,1,figsize=(9,5.3),sharex=True,layout='constrained')
    axes[0].plot(h,z.plan_00_grid_kwh,color='#777777',label='共同日前计划',lw=1.6)
    axes[0].plot(h,z.final_adjusted_grid_kwh,color='#dd8452',label='最终承诺购电',lw=1.8)
    axes[0].fill_between(h,0,z.emergency_kwh,color='#c44e52',alpha=.45,label='紧急购电')
    axes[0].set_ylabel('区间电量（kWh）');axes[0].legend(ncol=3,fontsize=11,loc='upper left')
    axes[1].plot(np.r_[h,24],np.r_[z.soc_start_kwh,z.soc_end_kwh.iloc[-1]],color='#4c72b0',lw=2)
    for value,label in [(1200,'下限1200'),(10800,'上限10800')]:
        axes[1].axhline(value,color='#888888',ls='--',lw=1)
        axes[1].annotate(label,(24,value),xytext=(-4,3),textcoords='offset points',ha='right',fontsize=10,color='#666666')
    axes[1].set_ylabel('储电量（kWh）');axes[1].set_xlabel('2025-06-21物理时刻（小时）')
    axes[1].set_xticks(range(0,25,4));axes[1].set_xlim(0,24);axes[1].set_ylim(600,11900)
    for ax in axes:ax.grid(axis='y',alpha=.17)
    finish(fig,'dispatch')
    fig,ax=plt.subplots(figsize=(9,3.65),layout='constrained')
    cumulative={}
    for mode in ['q3','q4_3']:
        a,b=[pd.read_csv(F/f'{mode}_{s}_daily.csv',float_precision='round_trip') for s in ['S0','S3']]
        inputs.extend([F/f'{mode}_{s}_daily.csv' for s in ['S0','S3']])
        assert list(a.date)==list(b.date) and len(a)==334
        y=(b.final_relative_cost_yuan-a.final_relative_cost_yuan).cumsum()/10000
        target=joint[(joint['mode']==mode)&(joint.scenario=='S3')].final_relative_cost_yuan.iloc[0]-joint[(joint['mode']==mode)&(joint.scenario=='S0')].final_relative_cost_yuan.iloc[0]
        assert abs(y.iloc[-1]*10000-target)<1e-5
        dates=pd.to_datetime(a.date);ax.plot(dates,y,color=colors[mode],lw=2,label=names[mode])
        ax.annotate(f'{y.iloc[-1]:.4f}万元',(dates.iloc[-1],y.iloc[-1]),xytext=(-6,9 if mode=='q3' else -16),textcoords='offset points',ha='right',fontsize=11,color=colors[mode])
        cumulative[mode]=float(y.iloc[-1]*10000)
    ax.axhline(0,color='#888888',lw=1);ax.grid(axis='y',alpha=.17)
    ax.set_ylabel('累计费用差 S3 - S0（万元）');ax.set_xlabel('2025年正式期（负值表示S3节省）')
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[2,4,6,8,10,12]));ax.xaxis.set_major_formatter(mdates.DateFormatter('%m月'))
    ax.legend(loc='lower left',fontsize=11);ax.set_ylim(-18,1)
    finish(fig,'cumulative')
    report={'role':'publication-only; no new numerical experiment','fee_unit':'万元 = yuan / 10000',
        'frequency':totals,'cumulative_final_yuan':cumulative,'input_hashes':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'output_hashes':{p.name:sha(p) for p in OUT.glob('*.png') if p.stem in ['route','dispatch','monthly','frequency','cumulative']},
        'font_family':family,'status':'PASS'}
    (ROOT/'publication/chart_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('Four Chinese data-derived charts rebuilt; totals and unit conversions PASS',flush=True)

if __name__=='__main__':main()
