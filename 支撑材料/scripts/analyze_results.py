from pathlib import Path
import sys,json,copy
from datetime import date
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.model.config import load_config
from src.model.data import load_data
from src.model.risk import cases,solve
from src.model.experiments import write_csv

def main():
    cfg=load_config('config/final.yaml');F=Path(cfg['_output_root'])/'frozen';E=F.parent/'evidence';cfg.update(json.loads((F/'resolved_config.json').read_text()));data=load_data(cfg);out=[];rng=np.random.default_rng(20260912)
    for mode in ['q3','q4_3']:
        base=pd.read_csv(F/f'{mode}_S0_daily.csv')
        for sc in ['S1','S2','S3']:
            d=pd.read_csv(F/f'{mode}_{sc}_daily.csv');delta=d.final_relative_cost_yuan.to_numpy()-base.final_relative_cost_yuan.to_numpy();samples=[]
            for _ in range(2000):
                starts=rng.integers(0,len(delta)-6,size=(len(delta)+6)//7);indices=np.concatenate([np.arange(x,x+7) for x in starts])[:len(delta)];samples.append(float(delta[indices].sum()))
            out.append(dict(mode=mode,comparison=sc+'_minus_S0',difference_yuan=float(delta.sum()),paired_days=len(delta),block_days=7,bootstrap_replicates=2000,ci_low=float(np.quantile(samples,.025)),ci_high=float(np.quantile(samples,.975))))
    write_csv(F/'comparison_stats.csv',out)
    sensitivity=[];solver=[]
    for mode in ['q2','q3','q4_2','q4_3']:
        d=pd.read_csv(F/f'{mode}_dispatch.csv');p=d.settlement_price.to_numpy();down=np.maximum(d.plan_00_grid_kwh-d.final_adjusted_grid_kwh,0)
        sensitivity.append(dict(mode=mode,main_cost=float(d.final_relative_cost_yuan.sum()),same_chain_sequential_cost=float(d.sequential_cost_yuan.sum()),no_refund_same_path_cost=float(d.final_relative_cost_yuan.sum()+np.dot(p,down)),note='same actions; no reoptimization; delivery-time prices'))
        if mode in ['q2','q4_2']:continue
        for daystr in cfg['experiments']['representative_dates']:
            day=date.fromisoformat(daystr);dd=d[d.date==daystr]
            for issue in [0,6,12,18]:
                pos=issue*6;length=min(144,len(data.dates)*144-(data.date_index[day]*144+pos));baseline=np.full(length,np.nan);baseline[:144-pos]=dd.plan_00_grid_kwh.to_numpy()[pos:];lock=np.full(length,np.nan)
                if issue==0:lock[:144]=baseline[:144]
                cs=cases(data,cfg,day,issue,length,mode);initial=float(dd.soc_start_kwh.iloc[pos]); sols=[]
                for method in ['highs','highs-ds','highs-ipm']:
                    r=solve(cs,initial,baseline,cfg,lock=lock,method=method);sols.append(r);solver.append(dict(mode=mode,date=daystr,issue=issue,method=method,objective=r.objective,objective_difference_vs_highs=r.objective-sols[0].objective,grid_l1_difference=float(abs(r.grid-sols[0].grid).sum()),soc_max_difference=float(abs(r.soc_end-sols[0].soc_end).max()),balance_residual=r.balance_residual,soc_residual=r.soc_residual))
    write_csv(F/'settlement_sensitivity.csv',sensitivity);write_csv(F/'solver_instance_sensitivity.csv',solver)
    # Explicit diagnosis remains a replay, never a trained test-period parameter.
    reserve=[]
    for mode in ['q2','q4_2']:
        d=pd.read_csv(F/f'{mode}_dispatch.csv')
        for delta in [0,10,20,50]:
            q=np.maximum(d.actual_load_kwh+d.charge_kwh-d.actual_pv_kwh-d.discharge_kwh-d.plan_00_grid_kwh-delta,0);cost=float(np.sum(d.settlement_price*(d.plan_00_grid_kwh+delta)+5*d.settlement_price*q));reserve.append(dict(mode=mode,delta_kwh=delta,total_cost=cost,difference_vs_current=cost-d.final_relative_cost_yuan.sum(),role='ex_post_diagnostic_not_parameter_selection'))
    write_csv(F/'reserve_diagnostic.csv',reserve)
    # Evidence source hashes include actual input bytes and active source code.
    sources=[]
    for p in (Path(cfg['_source_root'])/'C题').rglob('*'):
        if p.is_file():sources.append(dict(kind='original_input',path=str(p.relative_to(Path(cfg['_source_root']))),sha256=__import__('hashlib').sha256(p.read_bytes()).hexdigest()))
    for folder in ['src','scripts','tests','paper','config']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:sources.append(dict(kind='active_source',path=str(p.relative_to(ROOT)),sha256=__import__('hashlib').sha256(p.read_bytes()).hexdigest()))
    (E/'source_provenance.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2));print('Analysis and exact-instance solver diagnostics complete',flush=True)

if __name__=='__main__':main()
