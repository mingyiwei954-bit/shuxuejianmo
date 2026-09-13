from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


@dataclass
class DispatchSolution:
    grid: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    curtail: np.ndarray
    emergency: np.ndarray
    soc_end: np.ndarray
    objective: float
    elapsed_seconds: float
    iterations: int
    max_balance_residual: float
    max_soc_residual: float


def _one_way(charge:np.ndarray,discharge:np.ndarray,unused:np.ndarray,eta:float) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """Remove simultaneous cycling while preserving SOC change and energy balance."""
    delta=eta*charge-discharge/eta
    c=np.maximum(delta,0)/eta
    d=np.maximum(-delta,0)*eta
    u=unused+(d-discharge)-(c-charge)
    u[np.abs(u)<1e-10]=0.0
    if np.min(u)<-1e-7: raise AssertionError(f"one-way normalization produced negative unused energy {np.min(u)}")
    return c,d,np.maximum(u,0.0)


def _method_options(method: str, tolerance: float) -> dict[str, Any]:
    options: dict[str, Any] = {"presolve": True}
    if method in {"highs", "highs-ds"}:
        options.update({"primal_feasibility_tolerance": tolerance, "dual_feasibility_tolerance": tolerance})
    if method in {"highs", "highs-ipm"}:
        options["ipm_optimality_tolerance"] = max(tolerance, 1e-10)
    return options


def solve_deterministic(
    load_kwh: np.ndarray,
    pv_kwh: np.ndarray,
    price: np.ndarray,
    initial_soc: float,
    baseline: np.ndarray,
    terminal_rule: str,
    terminal_target: float,
    terminal_penalty: float,
    cfg: dict[str, Any],
    method: str = "highs",
    tiebreak: float | None = None,
) -> DispatchSolution:
    load = np.asarray(load_kwh, float); pv = np.asarray(pv_kwh, float); price = np.asarray(price, float)
    base = np.asarray(baseline, float)
    T = len(load)
    if not (len(pv) == len(price) == len(base) == T):
        raise ValueError("LP input lengths differ")
    G=slice(0,T); C=slice(T,2*T); D=slice(2*T,3*T); U=slice(3*T,4*T)
    E=slice(4*T,5*T); DN=slice(5*T,6*T); UP=slice(6*T,7*T)
    ZP=7*T; ZN=7*T+1; n=7*T+2
    committed=np.isfinite(base)
    c=np.zeros(n)
    c[G]=np.where(committed,0.0,price)
    c[DN]=np.where(committed,-cfg["cost"]["down_adjustment_multiplier"]*price,0.0)
    c[UP]=np.where(committed,cfg["cost"]["up_adjustment_multiplier"]*price,0.0)
    tb=float(cfg["cost"]["throughput_tiebreak_yuan_per_kwh"] if tiebreak is None else tiebreak)
    c[C]=tb; c[D]=tb
    if terminal_rule == "soft_target": c[ZP]=terminal_penalty; c[ZN]=terminal_penalty
    rr:list[int]=[]; cc:list[int]=[]; vv:list[float]=[]; rhs:list[float]=[]; row=0
    for t in range(T):
        rr += [row]*4; cc += [G.start+t,C.start+t,D.start+t,U.start+t]; vv += [1,-1,1,-1]
        rhs.append(float(load[t]-pv[t])); row+=1
    eta=float(cfg["storage"]["charge_efficiency"])
    for t in range(T):
        rr += [row]*3; cc += [C.start+t,D.start+t,E.start+t]; vv += [-eta,1/eta,1]
        if t: rr.append(row); cc.append(E.start+t-1); vv.append(-1); rhs.append(0.0)
        else: rhs.append(float(initial_soc))
        row+=1
    for t in np.flatnonzero(committed):
        rr += [row]*3; cc += [G.start+t,DN.start+t,UP.start+t]; vv += [1,1,-1]
        rhs.append(float(base[t])); row+=1
    if terminal_rule == "soft_target":
        rr += [row]*3; cc += [E.stop-1,ZP,ZN]; vv += [1,-1,1]; rhs.append(float(terminal_target)); row+=1
    Aeq=coo_matrix((vv,(rr,cc)),shape=(row,n)).tocsr()
    st=cfg["storage"]; step=float(st["power_kw"])*float(st["interval_minutes"])/60
    bounds=(
        [(0,None)]*T+[(0,step)]*T+[(0,step)]*T+[(0,float(x)) for x in pv]
        +[(float(st["soc_min_kwh"]),float(st["soc_max_kwh"]))]*T
        +[(0,float(base[t])) if committed[t] else (0,0) for t in range(T)]
        +[(0,None) if committed[t] else (0,0) for t in range(T)]
        +([(0,None),(0,None)] if terminal_rule == "soft_target" else [(0,0),(0,0)])
    )
    if terminal_rule in {"daily_closed","state_cycle","force_target"}:
        target = initial_soc if terminal_rule == "state_cycle" else terminal_target
        bounds[E.stop-1]=(float(target),float(target))
    started=time.perf_counter()
    res=linprog(c,A_eq=Aeq,b_eq=np.asarray(rhs),bounds=bounds,method=method,
                options=_method_options(method,float(cfg["audit"]["feasibility_tolerance"])))
    elapsed=time.perf_counter()-started
    if not res.success: raise RuntimeError(f"LP infeasible ({method}): {res.message}")
    x=res.x; charge,discharge,unused=_one_way(x[C],x[D],x[U],eta); e0=np.r_[initial_soc,x[E][:-1]]
    bal=x[G]+pv+discharge-load-charge-unused
    soc=x[E]-e0-eta*charge+discharge/eta
    return DispatchSolution(x[G],charge,discharge,unused,np.zeros(T),x[E],float(res.fun),elapsed,int(res.nit),float(np.max(np.abs(bal))),float(np.max(np.abs(soc))))


def solve_stochastic(
    load_kwh: np.ndarray,
    pv_scenarios_kwh: np.ndarray,
    price: np.ndarray,
    initial_soc: float,
    baseline: np.ndarray,
    execute_intervals: int,
    terminal_rule: str,
    terminal_target: float,
    terminal_penalty: float,
    cfg: dict[str, Any],
    method: str = "highs",
    tiebreak: float | None = None,
) -> DispatchSolution:
    """Two-stage extensive-form LP; current executable block is nonanticipative."""
    load=np.asarray(load_kwh,float); pvs=np.asarray(pv_scenarios_kwh,float); price=np.asarray(price,float); base=np.asarray(baseline,float)
    S,T=pvs.shape
    if len(load)!=T or len(price)!=T or len(base)!=T: raise ValueError("stochastic LP input lengths differ")
    # Per scenario: grid, charge, discharge, curtail/unused, emergency, SOC, down, up.
    per=8*T; soft=terminal_rule=="soft_target"; n=S*per+(2*S if soft else 0)
    committed=np.isfinite(base); c=np.zeros(n); prob=1.0/S
    st=cfg["storage"]; eta=float(st["charge_efficiency"]); step=float(st["power_kw"])*float(st["interval_minutes"])/60
    down_mult=float(cfg["cost"]["down_adjustment_multiplier"]); up_mult=float(cfg["cost"]["up_adjustment_multiplier"]); em_mult=float(cfg["cost"]["emergency_multiplier"])
    tb=float(cfg["cost"]["throughput_tiebreak_yuan_per_kwh"] if tiebreak is None else tiebreak)
    bounds:list[tuple[float,float|None]]=[]
    def slices(s:int):
        o=s*per
        return tuple(slice(o+i*T,o+(i+1)*T) for i in range(8))
    for s in range(S):
        G,C,D,U,H,E,DN,UP=slices(s)
        c[G]=prob*np.where(committed,0.0,price); c[C]=prob*tb; c[D]=prob*tb
        c[H]=prob*em_mult*price
        c[DN]=prob*np.where(committed,-down_mult*price,0.0); c[UP]=prob*np.where(committed,up_mult*price,0.0)
        bounds += [(0,None)]*T+[(0,step)]*T+[(0,step)]*T+[(0,None)]*T+[(0,None)]*T
        bounds += [(float(st["soc_min_kwh"]),float(st["soc_max_kwh"]))]*T
        bounds += [(0,float(base[t])) if committed[t] else (0,0) for t in range(T)]
        bounds += [(0,None) if committed[t] else (0,0) for t in range(T)]
    if soft:
        for s in range(S):
            c[S*per+2*s:S*per+2*s+2]=prob*terminal_penalty
            bounds += [(0,None),(0,None)]
    rr:list[int]=[]; cc:list[int]=[]; vv:list[float]=[]; rhs:list[float]=[]; row=0
    for s in range(S):
        G,C,D,U,H,E,DN,UP=slices(s)
        for t in range(T):
            rr += [row]*5; cc += [G.start+t,C.start+t,D.start+t,U.start+t,H.start+t]; vv += [1,-1,1,-1,1]
            rhs.append(float(load[t]-pvs[s,t])); row+=1
        for t in range(T):
            rr += [row]*3; cc += [C.start+t,D.start+t,E.start+t]; vv += [-eta,1/eta,1]
            if t: rr.append(row); cc.append(E.start+t-1); vv.append(-1); rhs.append(0.0)
            else: rhs.append(float(initial_soc))
            row+=1
        for t in np.flatnonzero(committed):
            rr += [row]*3; cc += [G.start+t,DN.start+t,UP.start+t]; vv += [1,1,-1]
            rhs.append(float(base[t])); row+=1
        if soft:
            rr += [row]*3; cc += [E.stop-1,S*per+2*s,S*per+2*s+1]; vv += [1,-1,1]
            rhs.append(float(terminal_target)); row+=1
        elif terminal_rule in {"daily_closed","state_cycle","force_target"}:
            target=initial_soc if terminal_rule=="state_cycle" else terminal_target
            bounds[E.stop-1]=(float(target),float(target))
    k=min(int(execute_intervals),T)
    for s in range(1,S):
        a=slices(0); b=slices(s)
        for block in (0,1,2):
            for t in range(k):
                rr += [row,row]; cc += [a[block].start+t,b[block].start+t]; vv += [1,-1]; rhs.append(0.0); row+=1
    Aeq=coo_matrix((vv,(rr,cc)),shape=(row,n)).tocsr()
    started=time.perf_counter()
    res=linprog(c,A_eq=Aeq,b_eq=np.asarray(rhs),bounds=bounds,method=method,
                options=_method_options(method,float(cfg["audit"]["feasibility_tolerance"])))
    elapsed=time.perf_counter()-started
    if not res.success: raise RuntimeError(f"stochastic LP infeasible ({method}): {res.message}")
    x=res.x; G,C,D,U,H,E,_,_=slices(0); charge,discharge,unused=_one_way(x[C],x[D],x[U],eta); e0=np.r_[initial_soc,x[E][:-1]]
    bal=x[G]+pvs[0]+discharge+x[H]-load-charge-unused
    soc=x[E]-e0-eta*charge+discharge/eta
    return DispatchSolution(x[G],charge,discharge,unused,x[H],x[E],float(res.fun),elapsed,int(res.nit),float(np.max(np.abs(bal))),float(np.max(np.abs(soc))))
