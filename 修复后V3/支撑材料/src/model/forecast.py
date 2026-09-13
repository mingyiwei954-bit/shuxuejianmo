"""Strict causal forecast interface. See risk.py for joint scenario provenance."""
from datetime import date
import numpy as np

def history_days(data,target_day:date,cutoff_day:date,count=4):
    ids=[i for i,d in enumerate(data.dates) if d<cutoff_day and d.weekday()==target_day.weekday()]
    if not ids:ids=[i for i,d in enumerate(data.dates) if d<cutoff_day]
    if not ids:raise ValueError('No causal history: startup policy is required')
    return ids[-count:]

def profile_horizon(data,start_global,length,cutoff_day,kind,count):
    matrix={'load':data.load_kw,'pv':data.pv_kw,'price':data.realtime_price}[kind];out=[];used=set()
    for k in range(length):
        di,pos=divmod(start_global+k,144);hist=history_days(data,data.dates[di],cutoff_day,count);used.update(hist);out.append(matrix[hist,pos].mean())
    return np.array(out),[data.dates[i] for i in sorted(used)]

def published_pv_horizon(data,day,issue_hour,length):
    return np.repeat(data.pv_forecast_kw[(day,issue_hour)],6)[:length].copy()
