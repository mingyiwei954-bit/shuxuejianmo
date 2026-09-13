"""Counterfactual information and scenario-marginal tests for the new diagnostics."""
from pathlib import Path
from datetime import date
from dataclasses import replace
import copy, json, sys, unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import contribution_experiments as ex


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=ex.load_config('config/final.yaml')
        cls.cfg.update(json.loads((ROOT/'frozen/resolved_config.json').read_text()))
        cls.data=ex.load_data(cls.cfg)

    def test_shuffle_preserves_whole_trajectory_marginals(self):
        day=date(2025,6,21)
        for mode in ('q2','q4_2'):
            original=ex.scenarios(self.data,self.cfg,day,0,144,mode,{'id':'reference'})
            shuffled=ex.scenarios(self.data,self.cfg,day,0,144,mode,{'id':'shuffle','shuffle_seed':20260913})
            for a,b in zip((original.load,original.pv,original.price),(shuffled.load,shuffled.pv,shuffled.price)):
                self.assertEqual(sorted(row.tobytes() for row in a),sorted(row.tobytes() for row in b))
            self.assertEqual(original.histories,shuffled.histories)
            self.assertFalse(np.array_equal(original.pv,shuffled.pv))

    def test_unobserved_future_does_not_change_scenarios_or_action(self):
        day=date(2025,6,21);di=self.data.date_index[day]
        for mode,issue,length in [('q4_2',0,144),('q4_3',6,72)]:
            arrays={}
            for field in ('load_kw','pv_kw','realtime_price'):
                a=getattr(self.data,field).copy();a.reshape(-1)[di*144+issue*6:]*=7
                arrays[field]=a
            forecasts={k:v.copy() for k,v in self.data.pv_forecast_kw.items()}
            for (d,h) in forecasts:
                if d>day or (d==day and h>issue): forecasts[(d,h)]*=9
            changed=replace(self.data,**arrays,pv_forecast_kw=forecasts)
            variant={'id':'shuffle','shuffle_seed':20260913} if issue==0 else {'id':'short','horizon':12}
            a=ex.scenarios(self.data,self.cfg,day,issue,length,mode,variant)
            b=ex.scenarios(changed,self.cfg,day,issue,length,mode,variant)
            for x,y in zip((a.load,a.pv,a.price),(b.load,b.pv,b.price)):np.testing.assert_array_equal(x,y)
            sa=ex.risk.solve(a,6000,np.full(length,np.nan),self.cfg)
            sb=ex.risk.solve(b,6000,np.full(length,np.nan),self.cfg)
            np.testing.assert_allclose(sa.grid,sb.grid,atol=1e-8,rtol=0)
            np.testing.assert_allclose(sa.soc_end,sb.soc_end,atol=1e-8,rtol=0)

    def test_count_changes_do_not_admit_unfinished_histories(self):
        for count,span,thin in [(10,20,True),(10,10,False),(40,40,False)]:
            cs=ex.scenarios(self.data,self.cfg,date(2025,1,8),18,72,'q4_3',{'id':'count','count':count,'span':span,'thin':thin})
            self.assertLessEqual(len(cs.histories),count)
            self.assertLessEqual(max(cs.observed_until),cs.issue_time)
            self.assertEqual(cs.load.shape[1],72)


if __name__=='__main__':unittest.main()
