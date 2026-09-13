import unittest,copy,json
from dataclasses import replace
from datetime import date
from pathlib import Path
import numpy as np
from src.model.config import load_config
from src.model.data import load_data
from src.model.forecast import history_days
from src.model.risk import cases,solve
from src.model.rolling import simulate,RunSpec
from src.model.experiments import startup

class ClosedLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_config('config/final.yaml'); resolved=Path(cls.cfg['_output_root'])/'frozen/resolved_config.json'
        if resolved.exists():cls.cfg.update(json.loads(resolved.read_text()))
        cls.data=load_data(cls.cfg)
    def test_no_future_cold_start(self):
        with self.assertRaises(ValueError):history_days(self.data,date(2025,1,1),date(2025,1,1))
        data=self.data;mut=data.load_kw.copy();mut[0]+=2000
        a=startup(data,self.cfg,'q2')[:144];b=startup(replace(data,load_kw=mut),self.cfg,'q2')[:144]
        self.assertEqual([r['plan_grid_kwh'] for r in a],[r['plan_grid_kwh'] for r in b]);self.assertTrue(all(r['soc_end_kwh']==6000 for r in a))
    def test_future_observations_cannot_change_decision(self):
        for mode,issue in [('q2',0),('q4_2',0),('q3',12),('q4_3',18)]:
            day=date(2025,2,1);di=self.data.date_index[day];cut=di*144+issue*6;kw={}
            for field in ['load_kw','pv_kw','realtime_price']:
                x=getattr(self.data,field).copy();x.reshape(-1)[cut:]+=321;kw[field]=x
            alt=replace(self.data,**kw);a=cases(self.data,self.cfg,day,issue,144,mode);b=cases(alt,self.cfg,day,issue,144,mode)
            for field in ['load','pv','price']:np.testing.assert_array_equal(getattr(a,field),getattr(b,field))
            baseline=np.full(144,np.nan);x=solve(a,6000,baseline,self.cfg);y=solve(b,6000,baseline,self.cfg);np.testing.assert_array_equal(x.grid,y.grid)
    def test_later_forecasts_not_visible(self):
        day=date(2025,2,1); forecasts={k:v.copy() for k,v in self.data.pv_forecast_kw.items()}
        for key in forecasts:
            if key[0]>day or (key[0]==day and key[1]>0):forecasts[key]+=9876
        alt=replace(self.data,pv_forecast_kw=forecasts)
        a=cases(self.data,self.cfg,day,0,144,'q3');b=cases(alt,self.cfg,day,0,144,'q3');np.testing.assert_array_equal(a.pv,b.pv)

    def test_nonanticipativity_and_formal_ledger(self):
        data=self.data;cfg=self.cfg;st=date(2025,2,1);en=date(2025,2,2)
        ref=simulate(data,cfg,RunSpec('q3','S0'),initial_soc=6000,start_date=st,end_date=en)
        r=simulate(data,cfg,RunSpec('q3','S3'),initial_soc=6000,start_date=st,end_date=en,common_plans=ref['plans'])
        np.testing.assert_allclose([x['plan_00_grid_kwh'] for x in ref['dispatch']],[x['plan_00_grid_kwh'] for x in r['dispatch']],atol=1e-8)
        commitments={};fees={}
        for v in r['decision_versions']:
            if v['is_preview_next_day']:continue
            key=(v['target_date'],v['position']);new=v['new_commitment_kwh']
            if key in commitments:
                self.assertAlmostEqual(commitments[key],v['old_commitment_kwh']);delta=new-commitments[key];p=data.fixed_price[key[1]-1];fees[key]=fees.get(key,0)+p*(delta+.5*abs(delta))
            commitments[key]=new
        for x in r['dispatch']:
            key=(x['date'],x['position']);self.assertAlmostEqual(commitments[key],x['final_adjusted_grid_kwh']);self.assertAlmostEqual(x['sequential_cost_yuan'],x['plan_cost_yuan']+fees.get(key,0)+x['emergency_cost_yuan']);self.assertGreaterEqual(x['sequential_cost_yuan']-x['final_relative_cost_yuan'],-1e-7)
            self.assertAlmostEqual(x['soc_end_kwh'],x['soc_start_kwh']+.9*x['charge_kwh']-x['discharge_kwh']/.9);self.assertLess(min(x['charge_kwh'],x['discharge_kwh']),1e-7)
    def test_partition_does_not_impose_terminal_reset(self):
        st=date(2025,1,30);en=date(2025,1,31);cfg=self.cfg;d=self.data
        full=simulate(d,cfg,RunSpec('q2','S0'),initial_soc=6000,start_date=st,end_date=en)
        first=simulate(d,cfg,RunSpec('q2','S0'),initial_soc=6000,start_date=st,end_date=st)
        second=simulate(d,cfg,RunSpec('q2','S0'),initial_soc=first['summary']['terminal_soc_kwh'],start_date=en,end_date=en)
        np.testing.assert_allclose([r['final_adjusted_grid_kwh'] for r in full['dispatch']],[r['final_adjusted_grid_kwh'] for r in first['dispatch']+second['dispatch']],atol=1e-8)
    def test_separate_charge_discharge_efficiencies(self):
        cfg=copy.deepcopy(self.cfg);cfg['storage']['discharge_efficiency']=.85
        cs=cases(self.data,cfg,date(2025,2,1),0,144,'q2');x=solve(cs,6000,np.full(144,np.nan),cfg)
        np.testing.assert_allclose(x.soc_end-np.r_[6000,x.soc_end[:-1]],.9*x.charge-x.discharge/.85,atol=1e-8)
    def test_charge_limit_and_year_end(self):
        r=simulate(self.data,self.cfg,RunSpec('q4_3','S3'),initial_soc=1200,start_date=date(2025,12,31),end_date=date(2025,12,31))
        self.assertAlmostEqual(r['summary']['terminal_soc_kwh'],6000)
        for x in r['dispatch']:
            self.assertLessEqual(x['charge_kwh'],5000/6+1e-7);self.assertLessEqual(x['discharge_kwh'],5000/6+1e-7);self.assertGreaterEqual(x['soc_end_kwh'],1200-1e-7);self.assertLessEqual(x['soc_end_kwh'],10800+1e-7)

if __name__=='__main__':unittest.main(verbosity=2)
