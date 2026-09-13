from __future__ import annotations
from dataclasses import dataclass
from datetime import date,timedelta
import numpy as np
from .risk import cases,solve

@dataclass(frozen=True)
class RunSpec:
    mode:str
    scenario:str='S3'
    arm:str='joint_empirical'
    method:str='highs'
    start_date:date|None=None
    end_date:date|None=None
    collect_detail:bool=True


def interval(pos):
    a=pos*10;b=a+10
    return f'{a//60:02d}:{a%60:02d}-{b//60:02d}:{b%60:02d}'


def make_row(data,day,j,B,A,c,d,s0,s1,fl,fp,pricehat,owner,mode,scenario,seq,history,arm):
    di=data.date_index[day];L=float(data.load_kw[di,j]/6);V=float(data.pv_kw[di,j]/6)
    p=float(data.realtime_price[di,j] if mode.startswith('q4') else data.fixed_price[j])
    deficit=L+c-V-d-A;Q=max(deficit,0);U=max(-deficit,0);delta=A-B
    pc=p*B;ac=p*(delta+.5*abs(delta));em=5*p*Q
    forecast_unused=max(A+fp+d-fl-c,0)
    return dict(date=day.isoformat(),position=j+1,source_timestamp=data.source_timestamps[j],physical_interval=interval(j),official_label=data.official_labels[j],
        plan_00_grid_kwh=float(B),final_adjusted_grid_kwh=float(A),adjustment_kwh=float(delta),charge_kwh=float(c),discharge_kwh=float(d),soc_start_kwh=float(s0),soc_end_kwh=float(s1),
        curtail_pv_kwh=min(forecast_unused,fp),planned_unused_nonpv_kwh=max(forecast_unused-fp,0),forecast_load_kwh=float(fl),forecast_pv_kwh=float(fp),actual_load_kwh=L,actual_pv_kwh=V,
        forecast_price=float(pricehat),settlement_price=p,emergency_kwh=Q,unused_surplus_kwh=U,plan_cost_yuan=pc,adjustment_cost_yuan=ac,emergency_cost_yuan=em,
        final_relative_cost_yuan=pc+ac+em,sequential_cost_yuan=pc+seq+em,decision_hour=owner,history_cutoff_date=(day-timedelta(days=1)).isoformat(),model_arm=arm,scenario=scenario)


def summarize(rows,mode,scenario,arm):
    sums={k:float(sum(r[k] for r in rows)) for k in ['plan_cost_yuan','adjustment_cost_yuan','emergency_cost_yuan','final_relative_cost_yuan','sequential_cost_yuan','emergency_kwh','unused_surplus_kwh']}
    return dict(mode=mode,scenario=scenario,model_arm=arm,days=len({r['date'] for r in rows}),initial_soc_kwh=rows[0]['soc_start_kwh'],terminal_soc_kwh=rows[-1]['soc_end_kwh'],**sums)


def simulate(data,cfg,spec:RunSpec,*,initial_soc:float,start_date=None,end_date=None,common_plans=None,point=False,no_storage=False,evaluation_terminal=False):
    start=start_date or spec.start_date or date.fromisoformat(cfg['study']['official_start']);end=end_date or spec.end_date or date.fromisoformat(cfg['study']['official_end'])
    if initial_soc is None:raise ValueError('Explicit state from startup ledger required')
    soc=float(initial_soc);rows=[];versions=[];daily=[];stats=[];plans={}
    schedule=cfg['experiments']['schedules'][spec.scenario] if spec.mode in ('q3','q4_3') else [0]
    total=(data.date_index[end]+1)*144 if evaluation_terminal else len(data.dates)*144
    for day in data.dates:
        if not start<=day<=end:continue
        di=data.date_index[day];B=None;committed=None;seq=np.zeros(144);dayrows=[]
        for ix,issue in enumerate(schedule):
            pos=issue*6;remaining=144-pos;length=min(144,total-(di*144+pos)) if spec.mode in ('q3','q4_3') else 144
            cs=cases(data,cfg,day,issue,length,spec.mode,point)
            base=np.full(length,np.nan);lock=np.full(length,np.nan)
            if issue==0 and common_plans is not None:
                B=np.asarray(common_plans[day.isoformat()],float).copy();base[:144]=B;lock[:144]=B
            elif issue>0:base[:remaining]=B[pos:]
            terminal=di*144+pos+length==total
            sol=solve(cs,soc,base,cfg,terminal=terminal,lock=lock,method=spec.method,no_storage=no_storage)
            if issue==0:
                if B is None:B=sol.grid[:144].copy()
                committed=B.copy();plans[day.isoformat()]=B.copy()
            else:
                old=committed[pos:].copy();delta=sol.grid[:remaining]-old
                p=data.realtime_price[di,pos:] if spec.mode.startswith('q4') else data.fixed_price[pos:]
                seq[pos:]+=p*(delta+.5*np.abs(delta))
            # Every shared current-day quantity is a genuine commitment; tomorrow
            # is a nonbinding preview. No deterministic alternate settlement path.
            for k in range(length):
                tdi,tj=divmod(di*144+pos+k,144);target=data.dates[tdi];preview=target!=day
                value=(B[k] if issue==0 else sol.grid[k]) if not preview else ''
                previous='' if preview or issue==0 else float(committed[pos+k])
                if spec.collect_detail:
                    versions.append(dict(date=str(day),target_date=str(target),mode=spec.mode,scenario=spec.scenario,model_arm=spec.arm,decision_time=cs.issue_time,forecast_issue_time=cs.issue_time,
                        effective_start=cs.issue_time,effective_end=f'{day+timedelta(days=1)} 00:00',history_cutoff_date=str(day-timedelta(days=1)),position=tj+1,physical_interval=interval(tj),official_label=data.official_labels[tj],
                        old_commitment_kwh=previous,new_commitment_kwh=float(value) if value!='' else '',sensitivity_old_commitment_kwh=previous,sensitivity_new_commitment_kwh=float(value) if value!='' else '',preview_grid_kwh=float(sol.grid[k]) if preview else '',
                        decision_basis='joint_nonanticipative_lp' if not preview else 'next_day_preview',soc_at_decision_kwh=soc,
                        load_history_dates='|'.join(cs.histories) if k==0 else '',price_history_dates='|'.join(cs.histories) if k==0 and spec.mode.startswith('q4') else '',pv_bias_history_dates='|'.join(cs.histories) if k==0 else '',residual_scenario_dates='|'.join(cs.histories) if k==0 else '',
                        latest_observation_time=max(cs.observed_until),is_preview_next_day=int(preview),is_preview_recourse=int(preview)))
            if issue>0:committed[pos:]=sol.grid[:remaining]
            nxt=schedule[ix+1] if ix+1<len(schedule) else 24;execute=(nxt-issue)*6
            sstarts=np.r_[soc,sol.soc_end[:-1]]
            for k in range(execute):
                j=pos+k
                dayrows.append(make_row(data,day,j,B[j],sol.grid[k],sol.charge[k],sol.discharge[k],sstarts[k],sol.soc_end[k],cs.load[:,k].mean(),cs.pv[:,k].mean(),cs.price[:,k].mean(),issue,spec.mode,spec.scenario,seq[j],cs.histories,spec.arm))
            soc=float(sol.soc_end[execute-1])
            stats.append(dict(mode=spec.mode,scenario=spec.scenario,date=str(day),issue_hour=issue,solver_method=spec.method,seconds=sol.seconds,objective=sol.objective,max_balance_residual_kwh=sol.balance_residual,max_soc_residual_kwh=sol.soc_residual,scenario_count=sol.model_scenarios,latest_observation_time=max(cs.observed_until),decision_time=cs.issue_time,history_dates='|'.join(cs.histories),common_action_intervals=length))
        rows.extend(dayrows);daily.append(dict(date=str(day),**summarize(dayrows,spec.mode,spec.scenario,spec.arm)))
    summary=summarize(rows,spec.mode,spec.scenario,spec.arm);summary.update(solver_seconds=sum(s['seconds'] for s in stats),solver_runs=len(stats),constraint_violation_count=sum(s['max_balance_residual_kwh']>1e-7 or s['max_soc_residual_kwh']>1e-7 for s in stats))
    return dict(dispatch=rows,decision_versions=versions,daily=daily,summary=summary,solve_stats=stats,plans=plans)
