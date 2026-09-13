"""Summaries use realized bills, never variant-dependent optimization objectives."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'diagnostics';F=ROOT/'outputs/c_final_v1/frozen'


def main():
    files=sorted((OUT/'runs').glob('*/*/summary.json'))
    if len(files)!=64:raise SystemExit(f'Expected 64 continuous runs, found {len(files)}')
    rows=[json.loads(p.read_text()) for p in files];df=pd.DataFrame(rows)
    if not df.passed.all():raise SystemExit('A diagnostic physical audit failed')
    df.to_csv(OUT/'summary.csv',index=False)
    official=pd.read_csv(F/'official_summary.csv')
    refchecks=[]
    for mode,variant in [('q2','reference'),('q4_2','reference'),('q3','horizon_24'),('q4_3','horizon_24')]:
        new=df.query('phase=="formal" and mode==@mode and variant==@variant').iloc[0]
        expected=float(official.loc[official['mode']==mode,'final_relative_cost_yuan'].iloc[0])
        refchecks.append(dict(mode=mode,new_cost=float(new.total_cost_yuan),frozen_cost=expected,difference=float(new.total_cost_yuan-expected)))
    if any(abs(r['difference'])>1e-6 for r in refchecks):raise SystemExit(f'Baseline re-solve mismatch: {refchecks}')
    (OUT/'reference_equivalence.json').write_text(json.dumps(refchecks,indent=2))
    controls=[]
    for mode in ['q2','q4_2']:
        d=pd.read_csv(F/f'{mode}_mean_forecast_dispatch.csv')
        controls.append(dict(mode=mode,total_cost_yuan=float(d.final_relative_cost_yuan.sum()),
            emergency_kwh=float(d.emergency_kwh.sum()),emergency_cost_share=float(d.emergency_cost_yuan.sum()/d.final_relative_cost_yuan.sum()),
            unused_surplus_kwh=float(d.unused_surplus_kwh.sum()),throughput_kwh=float((d.charge_kwh+d.discharge_kwh).sum()),
            evidence='existing frozen continuous trajectory, reaudited this revision; not rerun'))
    pd.DataFrame(controls).to_csv(OUT/'reused_mean_controls.csv',index=False)
    effects=[];high_days=[];monthly=[]
    for r in df.itertuples():
        baseline='reference' if r.mode in ('q2','q4_2') else 'horizon_24'
        base=df.query('phase==@r.phase and mode==@r.mode and variant==@baseline').iloc[0]
        savings=r.total_cost_yuan-float(base.total_cost_yuan)
        effects.append(dict(phase=r.phase,mode=r.mode,variant=r.variant,reference=baseline,
             variant_minus_reference_yuan=savings,reference_saving_vs_variant_yuan=savings,
             reference_saving_vs_variant_percent=100*savings/r.total_cost_yuan,
             variant_cost_change_percent=100*savings/float(base.total_cost_yuan)))
        d=pd.read_csv(OUT/'runs'/r.phase/(r.mode+'__'+r.variant)/'daily.csv')
        b=pd.read_csv(OUT/'runs'/r.phase/(r.mode+'__'+baseline)/'daily.csv')
        diff=d.final_relative_cost_yuan-b.final_relative_cost_yuan
        for i in np.argsort(-abs(diff.to_numpy()))[:5]:
            high_days.append(dict(phase=r.phase,mode=r.mode,variant=r.variant,date=d.date[i],
                 variant_minus_reference_yuan=float(diff[i]),emergency_cost_difference=float(d.emergency_cost_yuan[i]-b.emergency_cost_yuan[i]),
                 plan_cost_difference=float(d.plan_cost_yuan[i]-b.plan_cost_yuan[i]),adjustment_difference=float(d.adjustment_cost_yuan[i]-b.adjustment_cost_yuan[i])))
        d['month']=d.date.str[:7]
        for month,g in d.groupby('month'):
            monthly.append(dict(phase=r.phase,mode=r.mode,variant=r.variant,month=month,
                 total_cost_yuan=float(g.final_relative_cost_yuan.sum()),emergency_cost_yuan=float(g.emergency_cost_yuan.sum()),
                 emergency_share=float(g.emergency_cost_yuan.sum()/g.final_relative_cost_yuan.sum())))
    effects=pd.DataFrame(effects);effects.to_csv(OUT/'effects.csv',index=False)
    pd.DataFrame(high_days).to_csv(OUT/'high_impact_days.csv',index=False)
    pd.DataFrame(monthly).to_csv(OUT/'monthly.csv',index=False)
    sensitivity=[]
    for r in effects.query('phase=="formal"').itertuples():
        rel={'terminal_0':-1,'terminal_05':-.5,'terminal_15':.5,'count10_span20':-.5,'count10_span10':-.5,'count40_span40':1,'horizon_12':-.5,'horizon_18':-.25}.get(r.variant)
        if rel is not None:sensitivity.append(dict(mode=r.mode,variant=r.variant,relative_parameter_change=rel,
            relative_realized_cost_change=r.variant_cost_change_percent/100,
            finite_difference_elasticity=(r.variant_cost_change_percent/100)/rel,
            caveat='count10_span10 and count40_span40 jointly change sample count and history coverage; horizons change only intraday windows'))
    pd.DataFrame(sensitivity).to_csv(OUT/'continuous_sensitivity.csv',index=False)
    random=[]
    for mode in ['q2','q4_2']:
        s=effects.query('phase=="formal" and mode==@mode and variant.str.startswith("shuffle_")',engine='python').reference_saving_vs_variant_yuan
        random.append(dict(mode=mode,repetitions=len(s),joint_saving_mean_yuan=float(s.mean()),minimum=float(s.min()),maximum=float(s.max()),sd=float(s.std(ddof=1)),
                           interpretation='finite five-seed randomization distribution; not a confidence interval over years'))
    pd.DataFrame(random).to_csv(OUT/'shuffle_summary.csv',index=False)
    summary=dict(continuous_validation_runs=int((df.phase=='validation').sum()),continuous_formal_runs=int((df.phase=='formal').sum()),
        total_solves=int(df.solves.sum()),solver_seconds=float(df.solver_seconds.sum()),failures=int(df.failures.sum()),
        validation_common_plan_preparation_solves=48,
        preparation_timing='48 preliminary S0 solves are outside per-scheme timing; not separately measured',
        max_lp_residual=float(df.max_lp_residual.max()),max_physical_residual=float(df.max_physical_residual.max()),
        formal_algorithm_changed=False,formal_workbooks_changed=False,baseline_equivalence=refchecks)
    (OUT/'acceptance_summary.json').write_text(json.dumps(summary,indent=2))
    accounting=[];tails=[]
    daily={}
    for mode in ['q2','q3','q4_2','q4_3']:
        d=pd.read_csv(F/f'{mode}_dispatch.csv')
        cols=['plan_cost_yuan','adjustment_cost_yuan','emergency_cost_yuan','final_relative_cost_yuan','emergency_kwh','unused_surplus_kwh']
        daily[mode]=d.groupby('date')[cols].sum()
        for dt in daily[mode].final_relative_cost_yuan.nlargest(3).index:
            z=d[d.date==dt];r=daily[mode].loc[dt]
            tails.append(dict(mode=mode,date=dt,**r.to_dict(),mean_price=float(z.settlement_price.mean()),
                load_kwh=float(z.actual_load_kwh.sum()),pv_kwh=float(z.actual_pv_kwh.sum()),
                forecast_pv_error_kwh=float((z.forecast_pv_kwh-z.actual_pv_kwh).sum())))
    for a,b in [('q3','q2'),('q4_3','q4_2')]:
        diff=daily[a]-daily[b]
        for dt in diff.final_relative_cost_yuan.abs().nlargest(5).index:
            accounting.append(dict(comparison=a+' minus '+b,date=dt,**diff.loc[dt].to_dict(),
                                  meaning='accounting decomposition, not a causal forecast-value estimate'))
    pd.DataFrame(accounting).to_csv(OUT/'cross_model_accounting.csv',index=False)
    pd.DataFrame(tails).to_csv(OUT/'high_cost_days.csv',index=False)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
