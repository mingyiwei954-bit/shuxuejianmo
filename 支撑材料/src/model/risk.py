"""Causal empirical scenarios and a nonanticipative stochastic storage LP.

Only emergency procurement is scenario recourse. All scheduled grid, charge,
discharge and SOC variables are shared across scenarios over the full horizon.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime,time,timedelta
import time as timer
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from .data import DataBundle

@dataclass
class Cases:
    load: np.ndarray
    pv: np.ndarray
    price: np.ndarray
    histories: list[str]
    observed_until: list[str]
    issue_time: str
    kind: str


def causal_profile(data,matrix,target_i,cutoff_i):
    ids=[i for i in range(cutoff_i) if data.dates[i].weekday()==data.dates[target_i].weekday()][-4:]
    if not ids:ids=list(range(max(0,cutoff_i-4),cutoff_i))
    if not ids:raise ValueError("No prequential baseline before first observation")
    return matrix[ids].mean(axis=0)


def point_horizon(data,matrix,day_i,issue,length):
    first=causal_profile(data,matrix,day_i,day_i)[issue*6:]
    if length>len(first):first=np.r_[first,causal_profile(data,matrix,day_i+1,day_i)]
    return first[:length]


def cases(data:DataBundle,cfg:dict,day:date,issue:int,length:int,mode:str,point:bool=False)->Cases:
    di=data.date_index[day];now=di*144+issue*6
    histories=[];ends=[];loads=[];pvs=[];prices=[]
    n=int(cfg['forecast']['scenario_count']); calibrated=cfg['forecast'].get('scenario_model')=='causal_residual'
    if calibrated:
        current_load=point_horizon(data,data.load_kw,di,issue,length)
        current_pv=point_horizon(data,data.pv_kw,di,issue,length) if mode in ('q2','q4_2') else None
        current_price=point_horizon(data,data.realtime_price,di,issue,length) if mode.startswith('q4') else None
    # Each donor is an actually observed 24h trajectory ending no later than now.
    for old_i in range(max(0,di-n),di):
        old=data.dates[old_i];g=old_i*144+issue*6
        if calibrated and old_i==0:continue
        if g+144>now:continue
        sl=slice(g,g+length)
        l=data.load_kw.reshape(-1)[sl]/6
        if calibrated:l=np.maximum(current_load+6*l-point_horizon(data,data.load_kw,old_i,issue,length),0)/6
        if mode in ('q3','q4_3'):
            old_actual=data.pv_kw.reshape(-1)[g:g+144].reshape(24,6).mean(axis=1)
            residual=old_actual-data.pv_forecast_kw[(old,issue)]
            # Forecast lead 1 represents the hour after publication (right endpoint
            # zero-order hold). No interpolation using future actual observations.
            pp=np.maximum(np.repeat(data.pv_forecast_kw[(day,issue)]+residual,6)[:length],0)/6
        else:
            pp=data.pv_kw.reshape(-1)[sl]/6
            if calibrated:pp=np.maximum(current_pv+6*pp-point_horizon(data,data.pv_kw,old_i,issue,length),0)/6
        p=data.realtime_price.reshape(-1)[sl] if mode.startswith('q4') else np.asarray([data.fixed_price[(issue*6+k)%144] for k in range(length)])
        if calibrated and mode.startswith('q4'):p=np.maximum(current_price+p-point_horizon(data,data.realtime_price,old_i,issue,length),0)
        loads.append(l);pvs.append(pp);prices.append(p);histories.append(old.isoformat())
        ends.append((datetime.combine(old,time())+timedelta(hours=issue+24)).isoformat(sep=' ',timespec='minutes'))
    if not loads:raise ValueError('No observed history: execute the declared startup policy; never substitute future actuals')
    L=np.array(loads);V=np.array(pvs);P=np.array(prices)
    if point:L=L.mean(axis=0,keepdims=True);V=V.mean(axis=0,keepdims=True);P=P.mean(axis=0,keepdims=True)
    return Cases(L,V,P,histories,ends,f'{day} {issue:02d}:00','historical_joint' if mode in ('q2','q4_2') else 'published_pv_plus_observed_residual')

@dataclass
class Solution:
    grid:np.ndarray
    charge:np.ndarray
    discharge:np.ndarray
    soc_end:np.ndarray
    objective:float
    seconds:float
    balance_residual:float
    soc_residual:float
    model_scenarios:int


def solve(cs:Cases,soc0:float,baseline:np.ndarray,cfg:dict,terminal:bool=False,lock:np.ndarray|None=None,method:str='highs',no_storage:bool=False)->Solution:
    L,V,P=cs.load,cs.pv,cs.price;S,T=L.shape;meanp=P.mean(axis=0)
    # Shared G,C,D,E,down,up, then scenario emergency variables and terminal slacks.
    n=(6+S)*T+2;G=0;C=T;D=2*T;E=3*T;DN=4*T;UP=5*T;Q=6*T;Z=n-2
    committed=np.isfinite(baseline);obj=np.zeros(n)
    obj[G:G+T]=np.where(committed,0,meanp)
    obj[DN:DN+T]=np.where(committed,-.5*meanp,0)
    obj[UP:UP+T]=np.where(committed,1.5*meanp,0)
    obj[Q:Q+S*T]=(5*P/S).reshape(-1)
    tb=float(cfg['cost']['throughput_tiebreak_yuan_per_kwh']);obj[C:C+T]=tb;obj[D:D+T]=tb
    penalty=float(np.median(meanp))*float(cfg['rolling']['selected_soft_penalty_multiplier'])
    obj[Z:Z+2]=penalty
    eta_c=float(cfg['storage']['charge_efficiency']);eta_d=float(cfg['storage']['discharge_efficiency'])
    cap=float(cfg['storage']['power_kw'])/6;low=cfg['storage']['soc_min_kwh'];high=cfg['storage']['soc_max_kwh']
    bounds=[(0,None)]*T+[(0,0 if no_storage else cap)]*(2*T)+[(low,high)]*T
    bounds += [(0,float(baseline[t])) if committed[t] else (0,0) for t in range(T)]
    bounds += [(0,None) if committed[t] else (0,0) for t in range(T)]
    bounds += [(0,None)]*(S*T+2)
    if lock is not None:
        for t,v in enumerate(lock):
            if np.isfinite(v):bounds[t]=(float(v),float(v))
    if terminal:bounds[E+T-1]=(cfg['study']['terminal_soc_kwh'],cfg['study']['terminal_soc_kwh'])
    er=[];ec=[];ev=[];b=[]
    def eq(pairs,rhs):
        r=len(b);b.append(rhs)
        for col,val in pairs:er.append(r);ec.append(col);ev.append(val)
    for t in range(T):
        pairs=[(E+t,1),(C+t,-eta_c),(D+t,1/eta_d)]
        if t:pairs.append((E+t-1,-1))
        eq(pairs,soc0 if t==0 else 0)
    for t in np.flatnonzero(committed):eq([(G+t,1),(DN+t,1),(UP+t,-1)],float(baseline[t]))
    eq([(E+T-1,1),(Z,-1),(Z+1,1)],float(cfg['study']['terminal_soc_kwh']))
    # G + D - C + Q_s >= L_s - PV_s. Surplus is allowed, never sold.
    rr=[];cc=[];vv=[]
    for s in range(S):
        for t in range(T):
            r=s*T+t;rr.extend([r]*4);cc.extend([G+t,D+t,C+t,Q+s*T+t]);vv.extend([-1,-1,1,-1])
    A=coo_matrix((vv,(rr,cc)),shape=(S*T,n)).tocsr();Aeq=coo_matrix((ev,(er,ec)),shape=(len(b),n)).tocsr()
    start=timer.perf_counter()
    res=linprog(obj,A_ub=A,b_ub=(V-L).reshape(-1),A_eq=Aeq,b_eq=np.array(b),bounds=bounds,method=method,options={'primal_feasibility_tolerance':1e-8,'dual_feasibility_tolerance':1e-8,'ipm_optimality_tolerance':1e-9})
    seconds=timer.perf_counter()-start
    if not res.success:raise RuntimeError(res.message)
    x=res.x;c=x[C:C+T].copy();d=x[D:D+T].copy();e=x[E:E+T].copy()
    # Exact dominance transformation: preserve SOC, reduce purchases needed by
    # removing simultaneous cycling; free disposal and no minimum flow assumed.
    delta=eta_c*c-d/eta_d;c=np.maximum(delta,0)/eta_c;d=np.maximum(-delta,0)*eta_d
    q=x[Q:Q+S*T].reshape(S,T)
    violation=float(np.maximum(L+c[None,:]-V-d[None,:]-x[:T][None,:]-q,0).max())
    sr=float(np.abs(e-np.r_[soc0,e[:-1]]-eta_c*c+d/eta_d).max())
    if violation>1e-7 or sr>1e-7:raise AssertionError('Post-solve physical residual')
    return Solution(x[:T].copy(),c,d,e,float(res.fun),seconds,violation,sr,S)
