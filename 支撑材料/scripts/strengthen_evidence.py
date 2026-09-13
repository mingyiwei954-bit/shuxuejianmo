"""Prespecified diagnostic replays; never select the submitted policy on test data."""
from pathlib import Path
import sys, json, hashlib, time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.model.config import load_config
from src.model.data import load_data
from src.model.rolling import RunSpec, simulate

F=ROOT/'outputs/c_final_v1/frozen'
R=F.parent/'research'
R.mkdir(exist_ok=True)

def main():
    cfg=load_config('config/final.yaml')
    selected=json.loads((F/'resolved_config.json').read_text())
    for k in ('study','storage','forecast','rolling','cost','experiments'):cfg[k]=selected[k]
    data=load_data(cfg)
    protocol={'role':'post_selection_diagnostic; no policy replacement',
      'methods':['highs (existing frozen run)','highs-ipm'],
      'modes':['q3','q4_3'],'schedules':['S2','S3'],
      'period':['2025-02-01','2025-12-31'],'initial_soc':6000,
      'common_plan':'existing S0 reference plan, fixed across all methods and schedules',
      'selection':'January-selected configuration is frozen; all four IPM runs reported',
      'recorded_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
      'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/model').glob('*.py')}}
    protocol_path=R/'protocol.json'
    if not protocol_path.exists():protocol_path.write_text(json.dumps(protocol,ensure_ascii=False,indent=2))
    summaries=[];checks=[]
    for mode in ['q3','q4_3']:
        b=pd.read_csv(F/f'{mode}_S0_dispatch.csv')
        plans={day:z.plan_00_grid_kwh.to_numpy() for day,z in b.groupby('date',sort=False)}
        for sc in ['S2','S3']:
            existing=pd.read_csv(F/f'{mode}_{sc}_daily.csv')
            summaries.append({'mode':mode,'scenario':sc,'method':'highs','cost':float(existing.final_relative_cost_yuan.sum()),'emergency_kwh':float(existing.emergency_kwh.sum())})
            path=R/f'{mode}_{sc}_ipm.csv.xz'
            if not path.exists():
                print('START',mode,sc,'full-year IPM',flush=True)
                result=simulate(data,cfg,RunSpec(mode,sc,method='highs-ipm',collect_detail=False),initial_soc=6000,common_plans=plans)
                d=pd.DataFrame(result['dispatch'])
                cols=['date','position','final_adjusted_grid_kwh','charge_kwh','discharge_kwh','soc_start_kwh','soc_end_kwh','emergency_kwh','final_relative_cost_yuan']
                d[cols].to_csv(path,index=False,compression={'method':'xz','preset':9})
                pd.DataFrame(result['daily']).to_csv(R/f'{mode}_{sc}_ipm_daily.csv',index=False)
                pd.DataFrame(result['solve_stats']).to_csv(R/f'{mode}_{sc}_ipm_solvers.csv',index=False)
            d=pd.read_csv(path)
            # Independently reconstruct physical constraints and cost from raw arrays.
            ids=np.array([data.date_index[__import__('datetime').date.fromisoformat(x)] for x in d.date])
            pos=d.position.to_numpy()-1
            L=data.load_kw[ids,pos]/6;V=data.pv_kw[ids,pos]/6
            price=data.realtime_price[ids,pos] if mode.startswith('q4') else data.fixed_price[pos]
            B=np.concatenate(list(plans.values()));A=d.final_adjusted_grid_kwh.to_numpy()
            c=d.charge_kwh.to_numpy();dd=d.discharge_kwh.to_numpy();s=d.soc_start_kwh.to_numpy();e=d.soc_end_kwh.to_numpy()
            q=np.maximum(L+c-V-dd-A,0)
            cost=price*(B+(A-B)+.5*np.abs(A-B)+5*q)
            metrics={'rows':len(d),'cost_max_error':float(abs(cost-d.final_relative_cost_yuan).max()),'emergency_max_error':float(abs(q-d.emergency_kwh).max()),
                'soc_residual':float(abs(e-s-.9*c+dd/.9).max()),'continuity_residual':float(abs(s[1:]-e[:-1]).max()),
                'soc_min':float(min(s.min(),e.min())),'soc_max':float(max(s.max(),e.max())),
                'power_max':float(max(c.max(),dd.max())),'simultaneous_max':float(np.minimum(c,dd).max()),
                'start_soc':float(s[0]),'end_soc':float(e[-1])}
            ok=(len(d)==48096 and all(metrics[k]<1e-7 for k in ['cost_max_error','emergency_max_error','soc_residual','continuity_residual','simultaneous_max'])
                and metrics['soc_min']>=1200-1e-7 and metrics['soc_max']<=10800+1e-7 and metrics['power_max']<=5000/6+1e-7
                and abs(s[0]-6000)<1e-7 and abs(e[-1]-6000)<1e-7)
            assert ok,metrics
            checks.append({'mode':mode,'scenario':sc,'status':'PASS',**metrics})
            summaries.append({'mode':mode,'scenario':sc,'method':'highs-ipm','cost':float(cost.sum()),'emergency_kwh':float(q.sum())})
            print('DONE',mode,sc,'cost',cost.sum(),flush=True)
    pd.DataFrame(summaries).to_csv(R/'annual_solver_comparison.csv',index=False)
    (R/'annual_independent_checks.json').write_text(json.dumps(checks,indent=2))
    descriptive()

def descriptive():
    monthly=[];risks=[];calibration=[];bootstrap=[]
    for mode in ['q2','q4_2','q3','q4_3']:
        d=pd.read_csv(F/f'{mode}_dispatch.csv')
        for month,z in d.groupby(d.date.str[:7]):
            monthly.append({'mode':mode,'month':month,'cost':z.final_relative_cost_yuan.sum(),'emergency_cost':z.emergency_cost_yuan.sum(),'emergency_kwh':z.emergency_kwh.sum(),
                'unused_kwh':z.unused_surplus_kwh.sum(),'throughput_kwh':(z.charge_kwh+z.discharge_kwh).sum(),'low_soc_fraction':float((z.soc_start_kwh<1200.001).mean())})
        daily=d.groupby('date').agg(cost=('final_relative_cost_yuan','sum'),q=('emergency_kwh','sum'),ecost=('emergency_cost_yuan','sum'))
        costs=daily.cost.to_numpy();n_tail=max(1,int(np.ceil(.05*len(costs))))
        risks.append({'mode':mode,'emergency_interval_fraction':float((d.emergency_kwh>1e-7).mean()),'emergency_days':int((daily.q>1e-7).sum()),'max_daily_cost':float(costs.max()),'p95_daily_cost':float(np.quantile(costs,.95)),
            'tail5_mean_cost':float(np.sort(costs)[-n_tail:].mean()),'emergency_cost_share':float(d.emergency_cost_yuan.sum()/d.final_relative_cost_yuan.sum())})
        for var,a,b in [('load','forecast_load_kwh','actual_load_kwh'),('pv','forecast_pv_kwh','actual_pv_kwh'),('price','forecast_price','settlement_price')]:
            err=d[a]-d[b];calibration.append({'mode':mode,'variable':var,'mae':float(abs(err).mean()),'rmse':float(np.sqrt((err**2).mean())),'bias':float(err.mean()),'scope':'executed-interval scenario mean; mixed available decision times'})
    rng=np.random.default_rng(20260913)
    for mode in ['q3','q4_3']:
        s0=pd.read_csv(F/f'{mode}_S0_daily.csv').final_relative_cost_yuan.to_numpy()
        s2=pd.read_csv(F/f'{mode}_S2_daily.csv').final_relative_cost_yuan.to_numpy()
        s3=pd.read_csv(F/f'{mode}_S3_daily.csv').final_relative_cost_yuan.to_numpy()
        for name,delta in [('S3-S0',s3-s0),('S3-S2',s3-s2)]:
            for block in [3,7,14,28]:
                starts=rng.integers(0,len(delta)-block+1,size=(2000,(len(delta)+block-1)//block))
                ix=(starts[:,:,None]+np.arange(block)).reshape(2000,-1)[:,:len(delta)]
                sampled=delta[ix].sum(axis=1)
                bootstrap.append({'mode':mode,'comparison':name,'block_days':block,'replicates':2000,'difference':float(delta.sum()),'ci_low':float(np.quantile(sampled,.025)),'ci_high':float(np.quantile(sampled,.975))})
    for name,rows in [('monthly_mechanisms',monthly),('tail_risk',risks),('prediction_error',calibration),('block_sensitivity',bootstrap)]:pd.DataFrame(rows).to_csv(R/f'{name}.csv',index=False)
    import lzma,shutil
    for p in R.glob('*_ipm.csv.xz'):
        with lzma.open(p,'rb') as src,(F/('research_'+p.name.removesuffix('.csv.xz')+'_dispatch.csv')).open('wb') as dst:shutil.copyfileobj(src,dst)
    print('All diagnostic outputs completed',flush=True)

if __name__=='__main__':main()
