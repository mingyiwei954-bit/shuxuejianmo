"""Recover full control trajectories for a run initially saved with daily controls."""
from pathlib import Path
import sys,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.model.config import load_config
from src.model.data import load_data
from src.model.experiments import write_csv
from src.model.rolling import simulate,RunSpec
cfg=load_config('config/final.yaml');F=Path(cfg['_output_root'])/'frozen';cfg.update(json.loads((F/'resolved_config.json').read_text()));data=load_data(cfg)
for mode in ['q2','q4_2']:
 for arm,point,nostore in [('mean_forecast',True,False),('no_storage',False,True)]:
  initial=float(pd.read_csv(F/f'{mode}_january_dispatch.csv').soc_end_kwh.iloc[-1]);r=simulate(data,cfg,RunSpec(mode,'S0',arm,collect_detail=False),initial_soc=initial,point=point,no_storage=nostore)
  old=pd.read_csv(F/f'{mode}_{arm}_daily.csv');expected=float(old.final_relative_cost_yuan.sum());actual=r['summary']['final_relative_cost_yuan']
  if abs(expected-actual)>1e-6:raise AssertionError((mode,arm,expected,actual))
  write_csv(F/f'{mode}_{arm}_dispatch.csv',r['dispatch']);write_csv(F/f'{mode}_{arm}_solver.csv',r['solve_stats']);print('Recovered verified control',mode,arm,actual,flush=True)
