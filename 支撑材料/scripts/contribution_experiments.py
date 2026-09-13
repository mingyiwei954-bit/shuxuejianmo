"""Fixed-protocol, sequential continuous re-solves; never changes formal outputs."""
from pathlib import Path
from datetime import date
import argparse, copy, hashlib, json, platform, subprocess, sys, time
import numpy as np
import pandas as pd
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.model.config import load_config
from src.model.data import load_data
from src.model import risk, rolling

OUT = ROOT / 'diagnostics'
FROZEN = ROOT / 'outputs/c_final_v1/frozen'
ORIGINAL_LINPROG = risk.linprog
LAST = {}


def measured_linprog(*args, **kwargs):
    """Observe the same solver result without modifying options or its solution."""
    result = ORIGINAL_LINPROG(*args, **kwargs)
    LAST.clear()
    LAST.update(status=int(result.status), success=bool(result.success),
                message=result.message, iterations=int(result.nit))
    if result.success:
        residuals = [np.max(np.abs(result.eqlin.residual), initial=0)]
        for key in ('ineqlin', 'lower', 'upper'):
            residuals.append(np.max(np.maximum(-getattr(result, key).residual, 0), initial=0))
        LAST['lp_residual'] = float(max(residuals))
    return result


def scenarios(data, cfg, day, issue, length, mode, variant):
    c = copy.deepcopy(cfg)
    c['forecast']['scenario_count'] = variant.get('span', 20)
    c['forecast']['scenario_model'] = variant.get('scenario_model', 'causal_residual')
    cs = risk.cases(data, c, day, issue, length, mode)
    if variant.get('thin'):
        ids = np.linspace(0, len(cs.histories)-1, min(variant['count'], len(cs.histories))).round().astype(int)
        cs.load, cs.pv, cs.price = [x[ids] for x in (cs.load, cs.pv, cs.price)]
        cs.histories = [cs.histories[i] for i in ids]
        cs.observed_until = [cs.observed_until[i] for i in ids]
    if 'shuffle_seed' in variant:
        gen = np.random.default_rng(np.random.SeedSequence([variant['shuffle_seed'], day.toordinal(), issue, int(mode.startswith('q4'))]))
        cs.pv = cs.pv[gen.permutation(len(cs.pv))]
        if mode.startswith('q4'):
            cs.price = cs.price[gen.permutation(len(cs.price))]
    assert max(cs.observed_until) <= cs.issue_time
    return cs


def physical_audit(frame, data, start, end):
    """Recalculate actual physics and bills from raw arrays and exported controls."""
    d = frame
    i = (pd.to_datetime(d.date)-pd.Timestamp('2025-01-01')).dt.days.to_numpy()
    j = d.position.to_numpy()-1
    load, pv = data.load_kw[i, j]/6, data.pv_kw[i, j]/6
    price = data.realtime_price[i, j] if d['mode'].iloc[0].startswith('q4') else data.fixed_price[j]
    c, dis, b, a = [d[k].to_numpy() for k in ('charge_kwh','discharge_kwh','plan_00_grid_kwh','final_adjusted_grid_kwh')]
    s0, s1 = d.soc_start_kwh.to_numpy(), d.soc_end_kwh.to_numpy()
    q = np.maximum(load+c-pv-dis-a, 0)
    u = np.maximum(a+pv+dis-load-c, 0)
    cost = price*b+price*((a-b)+.5*np.abs(a-b))+5*price*q
    errors = {'soc_recursion': np.max(abs(s1-s0-.9*c+dis/.9)),
              'continuity': np.max(abs(s0[1:]-s1[:-1])),
              'soc_bounds': max(0,1200-s0.min(),1200-s1.min(),s0.max()-10800,s1.max()-10800),
              'power_bounds': max(0,c.max()-5000/6,dis.max()-5000/6,-c.min(),-dis.min()),
              'grid_nonnegative': max(0,-a.min(),-b.min()),
              'mutual_exclusion': np.max(np.minimum(c,dis)),
              'emergency': np.max(abs(q-d.emergency_kwh)),
              'surplus': np.max(abs(u-d.unused_surplus_kwh)),
              'bill': np.max(abs(cost-d.final_relative_cost_yuan)),
              'endpoints': max(abs(s0[0]-6000),abs(s1[-1]-6000))}
    keys = [(str(day), pos) for day in pd.date_range(start,end).date for pos in range(1,145)]
    exact_keys = keys == list(zip(d.date,d.position))
    return dict(passed=exact_keys and max(errors.values())<1e-7,
                exact_interval_keys=exact_keys, **{k:float(v) for k,v in errors.items()})


def execute(data, cfg, variant, mode, phase, period, common=None):
    start,end = map(date.fromisoformat,period)
    c=copy.deepcopy(cfg)
    c['rolling']['selected_soft_penalty_multiplier']=variant.get('penalty',1.0)
    soc=6000.;rows=[];stats=[];versions=[]
    schedules=[0,6,12,18] if mode in ('q3','q4_3') else [0]
    stop=(data.date_index[end]+1)*144
    beginning=time.perf_counter()
    for day in data.dates:
        if not start<=day<=end: continue
        di=data.date_index[day];B=None;committed=None;seq=np.zeros(144)
        for index,issue in enumerate(schedules):
            pos=issue*6
            length=min(144 if issue==0 else variant.get('horizon',24)*6,stop-di*144-pos)
            cs=scenarios(data,c,day,issue,length,mode,variant)
            base=np.full(length,np.nan);lock=np.full(length,np.nan)
            if issue==0 and common is not None:
                B=common[str(day)].copy();base[:]=B;lock[:]=B
            elif issue>0:
                n=min(length,144-pos);base[:n]=B[pos:pos+n]
            terminal=(di*144+pos+length==stop)
            sol=risk.solve(cs,soc,base,c,terminal=terminal,lock=lock)
            n=min(length,144-pos)
            if issue==0:
                if B is None: B=sol.grid.copy()
                committed=B.copy()
            else:
                previous=committed[pos:pos+n].copy()
                delta=sol.grid[:n]-previous
                price=data.realtime_price[di,pos:pos+n] if mode.startswith('q4') else data.fixed_price[pos:pos+n]
                seq[pos:pos+n]+=price*(delta+.5*abs(delta))
                committed[pos:pos+n]=sol.grid[:n]
            # Compact actual contract chain; next-day previews never enter it.
            for k in range(n):
                versions.append((str(day),issue,pos+k+1,float(committed[pos+k])))
            next_issue=schedules[index+1] if index+1<len(schedules) else 24
            count=(next_issue-issue)*6
            assert count<=length
            starts=np.r_[soc,sol.soc_end[:-1]]
            for k in range(count):
                row=rolling.make_row(data,day,pos+k,B[pos+k],sol.grid[k],sol.charge[k],sol.discharge[k],starts[k],sol.soc_end[k],cs.load[:,k].mean(),cs.pv[:,k].mean(),cs.price[:,k].mean(),issue,mode,'S3' if len(schedules)>1 else 'S0',seq[pos+k],cs.histories,variant['id'])
                row['mode']=mode;rows.append(row)
            soc=float(sol.soc_end[count-1])
            stats.append(dict(date=str(day),issue_hour=issue,seconds=sol.seconds,objective=sol.objective,
                 horizon_intervals=length,scenarios=sol.model_scenarios,variables=(6+sol.model_scenarios)*length+2,
                 history_dates='|'.join(cs.histories),latest_observation=max(cs.observed_until),decision_time=cs.issue_time,
                 max_soc_residual=sol.soc_residual,max_balance_residual=sol.balance_residual,**LAST))
    simulation_seconds=time.perf_counter()-beginning
    audit_start=time.perf_counter();frame=pd.DataFrame(rows);checks=physical_audit(frame,data,start,end)
    # Independent reconstruction of same-path net and sequential settlement.
    chain={};fees={};lookup=frame.set_index(['date','position']);chain_error=0.
    for dt,issue,pos,new in versions:
        key=(dt,pos)
        if key in chain:
            delta=new-chain[key];price=float(lookup.loc[key,'settlement_price'])
            fees[key]=fees.get(key,0)+price*(delta+.5*abs(delta))
        chain[key]=new
        assert (pos-1)*10>=issue*60
    computed=np.array([fees.get(k,0) for k in lookup.index])+frame.plan_cost_yuan+frame.emergency_cost_yuan
    checks['chain_final']=float(max(abs(chain[k]-lookup.loc[k,'final_adjusted_grid_kwh']) for k in lookup.index))
    checks['chain_bill']=float(np.max(abs(computed-frame.sequential_cost_yuan)))
    checks['common_contract']=float(np.max(abs(frame.plan_00_grid_kwh.to_numpy()-np.concatenate([common[str(d)] for d in pd.date_range(start,end).date])))) if common is not None else 0.
    checks['passed']=bool(checks['passed'] and max(checks['chain_final'],checks['chain_bill'],checks['common_contract'])<1e-7)
    elapsed_audit=time.perf_counter()-audit_start
    costs=float(frame.final_relative_cost_yuan.sum());s=pd.DataFrame(stats)
    result=dict(phase=phase,mode=mode,variant=variant['id'],days=(end-start).days+1,intervals=len(frame),
          total_cost_yuan=costs,emergency_kwh=float(frame.emergency_kwh.sum()),
          emergency_cost_yuan=float(frame.emergency_cost_yuan.sum()),emergency_cost_share=float(frame.emergency_cost_yuan.sum()/costs),
          unused_surplus_kwh=float(frame.unused_surplus_kwh.sum()),throughput_kwh=float((frame.charge_kwh+frame.discharge_kwh).sum()),
          net_adjustment_yuan=float(frame.adjustment_cost_yuan.sum()),sequential_cost_yuan=float(frame.sequential_cost_yuan.sum()),
          initial_soc=float(frame.soc_start_kwh.iloc[0]),terminal_soc=float(frame.soc_end_kwh.iloc[-1]),
          solves=len(s),solver_seconds=float(s.seconds.sum()),median_seconds=float(s.seconds.median()),p95_seconds=float(s.seconds.quantile(.95)),max_seconds=float(s.seconds.max()),
          simulation_seconds=simulation_seconds,audit_seconds=elapsed_audit,failures=int((s.status!=0).sum()),
          max_lp_residual=float(s.lp_residual.max()),min_actual_scenarios=int(s.scenarios.min()),max_actual_scenarios=int(s.scenarios.max()),
          max_physical_residual=max(float(v) for k,v in checks.items() if k not in ('passed','exact_interval_keys')),passed=checks['passed'])
    folder=OUT/'runs'/phase/(mode+'__'+variant['id']);folder.mkdir(parents=True,exist_ok=False)
    start_export=time.perf_counter()
    frame.to_csv(folder/'trajectory.csv.xz',index=False,compression='xz')
    pd.DataFrame(versions,columns=['date','issue_hour','position','new_commitment_kwh']).to_csv(folder/'contracts.csv.xz',index=False,compression='xz')
    s.to_csv(folder/'solvers.csv',index=False)
    frame.groupby('date')[['final_relative_cost_yuan','plan_cost_yuan','adjustment_cost_yuan','emergency_cost_yuan','emergency_kwh','unused_surplus_kwh','charge_kwh','discharge_kwh']].sum().to_csv(folder/'daily.csv')
    result['export_seconds']=time.perf_counter()-start_export
    (folder/'audit.json').write_text(json.dumps(checks,indent=2))
    (folder/'resolved_config.json').write_text(json.dumps(dict(base=c,variant=variant,phase=phase,period=period),indent=2))
    (folder/'summary.json').write_text(json.dumps(result,indent=2))
    if not checks['passed']: raise AssertionError(checks)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only');args=ap.parse_args()
    protocol=json.loads((OUT/'protocol.json').read_text())
    assert hashlib.sha256((OUT/'protocol.json').read_bytes()).hexdigest()==(OUT/'protocol.sha256').read_text().split()[0]
    cfg=load_config('config/final.yaml');cfg.update(json.loads((FROZEN/'resolved_config.json').read_text()))
    started=time.perf_counter();data=load_data(cfg);read_seconds=time.perf_counter()-started
    env=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
        cpu=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),
        logical_cpus=subprocess.check_output(['sysctl','-n','hw.logicalcpu'],text=True).strip(),
        execution='sequential experiment processes; solver default options unchanged',data_read_seconds=read_seconds,memory='not measured')
    try:
        from scipy.optimize._highspy._core import _Highs
        env['highs']=_Highs().version()
    except Exception as exc: env['highs_version_unavailable']=str(exc)
    (OUT/'environment.json').write_text(json.dumps(env,indent=2))
    risk.linprog=measured_linprog
    common={}
    for mode in protocol['rolling_modes']:
        d=pd.read_csv(FROZEN/f'{mode}_S0_dispatch.csv')
        common[(mode,'formal')]={day:g.plan_00_grid_kwh.to_numpy() for day,g in d.groupby('date')}
        begin,end=map(date.fromisoformat,protocol['phases']['validation'])
        ref=rolling.simulate(data,cfg,rolling.RunSpec(mode,'S0',collect_detail=False),initial_soc=6000,start_date=begin,end_date=end,evaluation_terminal=True)
        common[(mode,'validation')]=ref['plans']
        folder=OUT/'validation_common';folder.mkdir(exist_ok=True)
        pd.DataFrame(ref['dispatch']).to_csv(folder/f'{mode}.csv.xz',index=False,compression='xz')
    jobs=[(m,v) for v in protocol['variants'] for m in protocol['dayahead_modes']]
    jobs += [(m,{'id':f'horizon_{h}','horizon':h}) for h in protocol['horizon_candidates'] for m in protocol['rolling_modes']]
    errors=[]
    for phase,period in protocol['phases'].items():
        for mode,variant in jobs:
            key=mode+'__'+variant['id']
            if args.only and args.only not in key: continue
            saved=OUT/'runs'/phase/key/'summary.json'
            if saved.exists():
                print('CACHED',phase,key,flush=True);continue
            print('START',phase,key,flush=True)
            try:
                result=execute(data,cfg,variant,mode,phase,period,common.get((mode,phase)))
                print('DONE',phase,key,json.dumps(result),flush=True)
            except Exception as exc:
                import traceback
                errors.append(dict(phase=phase,job=key,error=repr(exc),traceback=traceback.format_exc()))
                (OUT/'failures.json').write_text(json.dumps(errors,indent=2));print('FAILED',errors[-1],flush=True)
    summaries=[json.loads(p.read_text()) for p in sorted((OUT/'runs').glob('*/*/summary.json'))]
    pd.DataFrame(summaries).to_csv(OUT/'summary.csv',index=False)
    (OUT/'run_completion.json').write_text(json.dumps(dict(expected=2*len(jobs),completed=len(summaries),failed=errors),indent=2))
    if errors: raise SystemExit(1)


if __name__=='__main__': main()
