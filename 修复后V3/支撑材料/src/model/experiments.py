from __future__ import annotations
import csv,json,hashlib,platform,sys,copy
from datetime import date,datetime,timedelta
from pathlib import Path
import numpy as np
from .rolling import simulate,RunSpec,summarize,interval
from .lp import solve_deterministic


def write_csv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:raise ValueError(f'No evidence rows: {path}')
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def q1(data,cfg):
    sol=solve_deterministic(data.q1_load_kw/6,data.q1_pv_kw/6,data.fixed_price,6000,np.full(144,np.nan),'force_target',6000,0,cfg)
    rows=[];starts=np.r_[6000,sol.soc_end[:-1]]
    for j in range(144):
        g=float(sol.grid[j]);c=float(sol.charge[j]);d=float(sol.discharge[j]);L=float(data.q1_load_kw[j]/6);V=float(data.q1_pv_kw[j]/6);p=float(data.fixed_price[j]);u=max(g+V+d-L-c,0)
        rows.append(dict(date='2025-01-01',position=j+1,source_timestamp=data.source_timestamps[j],physical_interval=interval(j),official_label=data.official_labels[j],plan_00_grid_kwh=g,final_adjusted_grid_kwh=g,adjustment_kwh=0,charge_kwh=c,discharge_kwh=d,soc_start_kwh=float(starts[j]),soc_end_kwh=float(sol.soc_end[j]),curtail_pv_kwh=min(u,V),planned_unused_nonpv_kwh=max(u-V,0),forecast_load_kwh=L,forecast_pv_kwh=V,actual_load_kwh=L,actual_pv_kwh=V,forecast_price=p,settlement_price=p,emergency_kwh=0,unused_surplus_kwh=u,plan_cost_yuan=p*g,adjustment_cost_yuan=0,emergency_cost_yuan=0,final_relative_cost_yuan=p*g,sequential_cost_yuan=p*g,decision_hour=0,history_cutoff_date='',model_arm='deterministic_q1',scenario='Q1'))
    return rows


def startup(data,cfg,mode):
    """Declared common January commissioning policy, independent of fitted model.
    Battery idle. With no completed day, scheduled purchase is zero and actual
    deficits are covered by the emergency contract. Thereafter use the empirical
    price-weighted 80% net-load quantile of completed days. No manufactured prior.
    """
    rows=[];soc=float(cfg['study']['initial_soc_kwh'])
    for di,day in enumerate(data.dates):
        if day>=date.fromisoformat(cfg['study']['official_start']):break
        hist=list(range(max(0,di-int(cfg['forecast']['scenario_count'])),di));B=np.zeros(144)
        if hist:
            nets=np.maximum((data.load_kw[hist]-data.pv_kw[hist])/6,0)
            P=data.realtime_price[hist] if mode.startswith('q4') else np.tile(data.fixed_price,(len(hist),1))
            for j in range(144):
                order=np.argsort(nets[:,j]);cum=np.cumsum(P[order,j]);ix=np.searchsorted(cum,.8*cum[-1]);B[j]=nets[order[ix],j]
        for j in range(144):
            L=float(data.load_kw[di,j]/6);V=float(data.pv_kw[di,j]/6);p=float(data.realtime_price[di,j] if mode.startswith('q4') else data.fixed_price[j]);Q=max(L-V-B[j],0);U=max(B[j]+V-L,0)
            rows.append(dict(mode=mode,date=str(day),position=j+1,physical_interval=interval(j),plan_grid_kwh=float(B[j]),charge_kwh=0.,discharge_kwh=0.,soc_start_kwh=soc,soc_end_kwh=soc,actual_load_kwh=L,actual_pv_kwh=V,emergency_kwh=Q,unused_surplus_kwh=U,settlement_price=p,cost_yuan=p*B[j]+5*p*Q,history_dates='|'.join(str(data.dates[i]) for i in hist),policy='zero_plan_no_history' if not hist else 'empirical_newsvendor_idle_battery'))
    return rows


def perfect(data,cfg):
    out=[];i=data.date_index[date.fromisoformat(cfg['study']['official_start'])];n=(len(data.dates)-i)*144
    for mode in ['q2','q4_2']:
        p=data.realtime_price[i:].reshape(-1) if mode.startswith('q4') else np.tile(data.fixed_price,len(data.dates)-i)
        sol=solve_deterministic(data.load_kw[i:].reshape(-1)/6,data.pv_kw[i:].reshape(-1)/6,p,6000,np.full(n,np.nan),'force_target',6000,0,cfg)
        out.append(dict(mode=mode,purchase_cost_yuan=float(p@sol.grid),initial_soc_kwh=6000,terminal_soc_kwh=6000,days=len(data.dates)-i,information='ex_post_lower_bound_not_executable'))
    return out


def run_all(data,cfg,stage='all'):
    root=Path(cfg['_output_root']);frozen=root/'frozen';ev=root/'evidence';frozen.mkdir(parents=True,exist_ok=True);ev.mkdir(parents=True,exist_ok=True)
    # The input configuration never changes in place. Chosen January parameters
    # live in a resolved copy and are reused by every later branch.
    cfg=copy.deepcopy(cfg)
    if stage in ('all','train'):
        training=[]
        for scenario_model in ['raw_history','causal_residual']:
            for mult in cfg['rolling']['soft_penalty_multipliers']:
                trial=copy.deepcopy(cfg);trial['rolling']['selected_soft_penalty_multiplier']=mult;trial['forecast']['scenario_model']=scenario_model
                for mode in ['q2','q3','q4_2','q4_3']:
                    r=simulate(data,trial,RunSpec(mode,'S0',collect_detail=False),initial_soc=6000,start_date=date(2025,1,8),end_date=date(2025,1,31),evaluation_terminal=True)
                    training.append(dict(scenario_model=scenario_model,penalty_multiplier=mult,**r['summary']));print('TRAIN',scenario_model,mode,mult,r['summary']['final_relative_cost_yuan'],flush=True)
        scenario_model,selected=min([(sm,m) for sm in ['raw_history','causal_residual'] for m in cfg['rolling']['soft_penalty_multipliers']],key=lambda pair:sum(r['final_relative_cost_yuan'] for r in training if r['scenario_model']==pair[0] and r['penalty_multiplier']==pair[1]))
        cfg['forecast']['scenario_model']=scenario_model
        cfg['rolling']['selected_soft_penalty_multiplier']=selected;write_csv(ev/'january_parameter_validation.csv',training)
        (frozen/'resolved_config.json').write_text(json.dumps({k:v for k,v in cfg.items() if not k.startswith('_')},ensure_ascii=False,indent=2))
        if stage=='train':return
    else:
        cfg.update(json.loads((frozen/'resolved_config.json').read_text()))
    if stage in ('all','official'):
        write_csv(frozen/'time_index.csv',data.time_rows());write_csv(frozen/'q1_dispatch.csv',q1(data,cfg));write_csv(frozen/'perfect_information_summary.csv',perfect(data,cfg))
        summary=[];versions=[];stats=[];startup_summary=[]
        for mode in ['q2','q4_2','q3','q4_3']:
            jan=startup(data,cfg,mode);write_csv(frozen/f'{mode}_january_dispatch.csv',jan);initial=jan[-1]['soc_end_kwh'];startup_summary.append(dict(mode=mode,initial_soc_kwh=jan[0]['soc_start_kwh'],terminal_soc_kwh=initial,cost_yuan=sum(x['cost_yuan'] for x in jan),policy='common_causal_commissioning'))
            if mode in ('q2','q4_2'):
                r=simulate(data,cfg,RunSpec(mode,'S0'),initial_soc=initial);write_csv(frozen/f'{mode}_dispatch.csv',r['dispatch']);summary.append(r['summary']);stats.extend(r['solve_stats'])
                for arm,point,nostore in [('mean_forecast',True,False),('no_storage',False,True)]:
                    control=simulate(data,cfg,RunSpec(mode,'S0',arm,collect_detail=False),initial_soc=initial,point=point,no_storage=nostore);write_csv(frozen/f'{mode}_{arm}_daily.csv',control['daily']);write_csv(frozen/f'{mode}_{arm}_dispatch.csv',control['dispatch']);write_csv(frozen/f'{mode}_{arm}_solver.csv',control['solve_stats']);summary.append(control['summary'])
                print('OFFICIAL',mode,r['summary']['final_relative_cost_yuan'],flush=True)
            else:
                ref=simulate(data,cfg,RunSpec(mode,'S0'),initial_soc=initial);write_csv(frozen/f'{mode}_S0_dispatch.csv',ref['dispatch']);write_csv(frozen/f'{mode}_S0_daily.csv',ref['daily']);write_csv(frozen/f'{mode}_S0_decisions.csv',ref['decision_versions']);summary.append(ref['summary']);stats.extend(ref['solve_stats'])
                for sc in ['S1','S2','S3']:
                    r=simulate(data,cfg,RunSpec(mode,sc),initial_soc=initial,common_plans=ref['plans']);write_csv(frozen/f'{mode}_{sc}_dispatch.csv',r['dispatch']);write_csv(frozen/f'{mode}_{sc}_daily.csv',r['daily']);write_csv(frozen/f'{mode}_{sc}_decisions.csv',r['decision_versions']);summary.append(r['summary']);stats.extend(r['solve_stats'])
                    if sc=='S3':write_csv(frozen/f'{mode}_dispatch.csv',r['dispatch']);write_csv(frozen/f'{mode}_decision_versions.csv',r['decision_versions']);versions.extend(r['decision_versions'])
                    print('OFFICIAL',mode,sc,r['summary']['final_relative_cost_yuan'],flush=True)
        write_csv(frozen/'decision_versions.csv',versions);write_csv(frozen/'experiment_summary.csv',summary);write_csv(frozen/'official_summary.csv',[r for r in summary if r['model_arm']=='joint_empirical' and (r['mode'] in ('q2','q4_2') or r['scenario']=='S3')]);write_csv(frozen/'startup_summary.csv',startup_summary);write_csv(frozen/'solver_decisions.csv',stats)
        (frozen/'model_run_summary.json').write_text(json.dumps(dict(generated_at=datetime.now().astimezone().isoformat(),environment=dict(python=sys.version,platform=platform.platform()),results=summary,training_selected_multiplier=cfg['rolling']['selected_soft_penalty_multiplier'],official_scenario='S3',comparison_contract='identical_reference_midnight_grid_plans; common_January_idle_battery_startup; same_terminal_SOC'),ensure_ascii=False,indent=2))
    return cfg
