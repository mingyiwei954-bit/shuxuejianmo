from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'work/python_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd
F=ROOT/'outputs/c_final_v1/frozen';C=F.parent/'charts';C.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
s=pd.read_csv(F/'experiment_summary.csv');official=s[(s.model_arm=='joint_empirical')&((s['mode'].isin(['q2','q4_2']))|(s.scenario=='S3'))]
fig,ax=plt.subplots(figsize=(8,3.6));x=np.arange(len(official));bottom=np.zeros(len(x))
for col,label,color in [('plan_cost_yuan','Scheduled','#35658a'),('adjustment_cost_yuan','Net revisions','#dfa04f'),('emergency_cost_yuan','Emergency','#b85450')]:
 vals=official[col].to_numpy()/1e6;ax.bar(x,vals,bottom=bottom,label=label,color=color);bottom+=vals
ax.set_xticks(x,official['mode']);ax.set_ylabel('Realized cost / million yuan');ax.legend(ncol=3,frameon=False);fig.tight_layout();fig.savefig(C/'cost_components.png');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(8,3.5))
for ax,mode in zip(axs,['q3','q4_3']):
 d=s[(s['mode']==mode)&(s.model_arm=='joint_empirical')].sort_values('scenario');ax.plot(d.scenario,d.final_relative_cost_yuan/1e6,'o-',color='#35658a');ax.set_title(mode.upper());ax.set_ylabel('Main cost / million yuan');ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(C/'schedule_comparison.png');plt.close(fig)
fig,axs=plt.subplots(2,1,figsize=(8,4.8),sharex=True);d=pd.read_csv(F/'q3_dispatch.csv');d=d[d.date=='2025-06-21'];h=(d.position.to_numpy()-1)/6
axs[0].plot(h,d.plan_00_grid_kwh,label='Common day-ahead');axs[0].plot(h,d.final_adjusted_grid_kwh,label='Final commitment');axs[0].fill_between(h,0,d.emergency_kwh,color='#b85450',alpha=.5,label='Emergency');axs[0].set_ylabel('Energy / kWh');axs[0].legend(ncol=3,frameon=False,fontsize=8)
axs[1].plot(h,d.soc_start_kwh,color='#35658a');axs[1].axhline(1200,ls='--',color='gray');axs[1].axhline(10800,ls='--',color='gray');axs[1].set_ylabel('SOC / kWh');axs[1].set_xlabel('Physical hour on 2025-06-21');fig.tight_layout();fig.savefig(C/'representative_dispatch.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.6))
for mode,color in [('q3','#35658a'),('q4_3','#b85450')]:
 a=pd.read_csv(F/f'{mode}_S0_daily.csv');b=pd.read_csv(F/f'{mode}_S3_daily.csv');delta=b.final_relative_cost_yuan-a.final_relative_cost_yuan;ax.plot(pd.to_datetime(a.date),delta.cumsum()/1000,label=mode,color=color)
ax.axhline(0,color='gray',lw=.8);ax.set_ylabel('Cumulative S3 - S0 / thousand yuan');ax.legend(frameon=False);fig.autofmt_xdate();fig.tight_layout();fig.savefig(C/'cumulative_difference.png');plt.close(fig)
print('Four data-derived figures written',flush=True)
monthly=pd.read_csv(F.parent/'research/monthly_mechanisms.csv')
fig,axs=plt.subplots(2,1,figsize=(8,5.0),sharex=True)
for mode,color in zip(['q2','q4_2','q3','q4_3'],['#35658a','#b85450','#548764','#9b6a9a']):
 z=monthly[monthly['mode']==mode];x=np.arange(len(z))
 axs[0].plot(x,z.cost/1e6,'o-',color=color,label=mode)
 axs[1].plot(x,z.emergency_cost/z.cost*100,'o-',color=color)
axs[0].set_ylabel('Monthly cost / million yuan');axs[0].legend(ncol=4,frameon=False)
axs[1].set_ylabel('Emergency cost share / %');axs[1].set_xticks(x,z.month.str[5:]);axs[1].set_xlabel('Month in 2025')
for ax in axs:ax.grid(axis='y',alpha=.2)
fig.tight_layout();fig.savefig(C/'monthly_risk.png');plt.close(fig)
