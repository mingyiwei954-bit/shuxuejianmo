from pathlib import Path
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from matplotlib.font_manager import FontProperties
import pandas as pd
W=Path(__file__).resolve().parent;out=W/'figures';out.mkdir(exist_ok=True)
SUPPORT=W/'support' if (W/'support').exists() else W.parent
cn=FontProperties(fname=os.environ['SIMSUN_FONT'],size=12) if os.environ.get('SIMSUN_FONT') else FontProperties(family='SimSun',size=12)
plt.rcParams.update({'font.family':'Times New Roman','font.size':12,'axes.unicode_minus':False})
fig,ax=plt.subplots(figsize=(9,5.4));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
boxes=[(.2,4.6,2.6,.9,'原题数据与参数\n单位 时间轴 缺失核对'),(3.5,4.6,2.8,.9,'一月验证与连续启动\n锁定配置 保存期末状态'),(7,4.6,2.7,.9,'正式期信息截取\n完成观测 已发布预报'),(7,2.5,2.7,.95,'联合场景与共享动作\n物理约束 风险购电目标'),(3.5,2.5,2.8,.95,'HiGHS求解与动作核验\n只执行至下一更新时刻'),(.2,2.5,2.6,.95,'实际缺口与合同结算\n记录费用和下一储电量'),(.2,.35,9.5,.95,'独立检验与结果输出\n物理残差 信息隔离 误差分析 参数扰动 算法对照 分块统计')]
for x,y,w,h,t in boxes:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='square,pad=0.04',linewidth=1,facecolor='white',edgecolor='black'))
 ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontproperties=cn,linespacing=1.5)
for a,b in [((2.85,5.05),(3.45,5.05)),((6.35,5.05),(6.95,5.05)),((8.35,4.55),(8.35,3.5)),((6.95,2.975),(6.35,2.975)),((3.45,2.975),(2.85,2.975)),((1.5,2.45),(1.5,1.35))]:
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=13,color='black'))
ax.plot([1.5,1.5,8.35,8.35],[3.5,4.0,4.0,4.5],color='black',lw=.8,ls='--');ax.text(4.8,4.02,'状态反馈至下一决策时刻',fontproperties=cn,ha='center',va='bottom')
fig.savefig(out/'route.png',dpi=400,bbox_inches='tight',pad_inches=.07);fig.savefig(out/'route.svg',bbox_inches='tight');plt.close(fig)
d=pd.read_csv(SUPPORT/'research/parameter_perturbation/summary.csv');fig,axes=plt.subplots(1,2,figsize=(9,3.4))
for a,key,title in zip(axes,['terminal_multiplier','power_kw'],['Terminal penalty multiplier','Battery power rating']):
 s=d[d.parameter==key];a.plot((s.ratio-1)*100,s.mean_objective_change_pct,'o-',color='black',label='Mean change')
 a.plot((s.ratio-1)*100,s.max_abs_objective_change_pct,'s--',color='#555555',label='Maximum absolute change')
 a.axhline(0,color='#999999',lw=.5);a.set(title=title,xlabel='Parameter change (%)',ylabel='Window objective change (%)');a.grid(alpha=.16);a.set_xticks([-20,-10,0,10,20])
axes[0].legend(fontsize=9,loc='best');fig.tight_layout();fig.savefig(out/'sensitivity.png',dpi=400,bbox_inches='tight');fig.savefig(out/'sensitivity.svg',bbox_inches='tight');plt.close(fig)
