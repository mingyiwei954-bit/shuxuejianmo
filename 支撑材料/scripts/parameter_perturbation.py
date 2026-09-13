"""固定窗口参数扰动；只新增诊断文件，不改变正式模型及结果。

运行前按README恢复冻结CSV，设置CUMCM_SOURCE_ROOT指向原题父目录。
两类参数分别施加-20%、-10%、0、+10%、+20%扰动。
每次固定同一状态、日前合同、场景和窗口；不解释为全年策略回放。
"""
from pathlib import Path
from datetime import date
import sys, json, copy, hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.model.config import load_config
from src.model.data import load_data
from src.model.risk import cases, solve


def main():
    cfg = load_config('config/final.yaml')
    frozen = Path(cfg['_output_root']) / 'frozen'
    cfg.update(json.loads((frozen / 'resolved_config.json').read_text()))
    data = load_data(cfg)
    output = ROOT / 'research' / 'parameter_perturbation'
    output.mkdir(parents=True, exist_ok=True)
    # 输入质量检查采用实际读取矩阵，不删除真实高峰或填造观测。
    arrays = {'负载功率': data.load_kw, '光伏实测功率': data.pv_kw,
              '实时电价': data.realtime_price,
              '光伏预报功率': np.stack(list(data.pv_forecast_kw.values()))}
    quality = []
    for name, a in arrays.items():
        quality.append(dict(variable=name, values=int(a.size),
                            missing=int((~np.isfinite(a)).sum()),
                            negative=int((a < 0).sum()),
                            minimum=float(a.min()), maximum=float(a.max())))
    (output / 'input_quality.json').write_text(
        json.dumps(quality, ensure_ascii=False, indent=2))
    rows = []
    for mode in ['q3', 'q4_3']:
        dispatch = pd.read_csv(frozen / f'{mode}_dispatch.csv')
        for daystr in cfg['experiments']['representative_dates']:
            day = date.fromisoformat(daystr)
            dd = dispatch[dispatch.date == daystr]
            for issue in [0, 6, 12, 18]:
                pos = issue * 6
                length = min(144, len(data.dates)*144
                             - data.date_index[day]*144 - pos)
                baseline = np.full(length, np.nan)
                baseline[:144-pos] = dd.plan_00_grid_kwh.to_numpy()[pos:]
                lock = np.full(length, np.nan)
                if issue == 0:
                    lock[:144] = baseline[:144]
                cs = cases(data, cfg, day, issue, length, mode)
                initial = float(dd.soc_start_kwh.iloc[pos])
                reference = solve(cs, initial, baseline, cfg, lock=lock)
                # 求解器省略已支付日前合同的常数项；比较费用幅度时补回。
                committed = np.isfinite(baseline)
                constant = float(np.dot(cs.price.mean(axis=0)[committed],
                                        baseline[committed]))
                # 两参数逐一变化，其他输入均保持相同；0档直接复用基线。
                for parameter in ['terminal_multiplier', 'power_kw']:
                    for ratio in [0.8, 0.9, 1.0, 1.1, 1.2]:
                        perturbed = copy.deepcopy(cfg)
                        if parameter == 'terminal_multiplier':
                            original = cfg['rolling']['selected_soft_penalty_multiplier']
                            perturbed['rolling']['selected_soft_penalty_multiplier'] = original*ratio
                        else:
                            original = cfg['storage']['power_kw']
                            perturbed['storage']['power_kw'] = original*ratio
                        solution = (reference if ratio == 1.0 else
                                    solve(cs, initial, baseline, perturbed, lock=lock))
                        # 窗口目标可能为负或接近零，统一用绝对基值作分母。
                        denominator = max(abs(reference.objective + constant), 1.0)
                        rows.append(dict(
                            mode=mode, date=daystr, issue=issue,
                            parameter=parameter, ratio=ratio,
                            parameter_value=original*ratio,
                            base_objective=reference.objective + constant,
                            objective=solution.objective + constant,
                            objective_change_pct=100*(solution.objective-reference.objective)/denominator,
                            grid_l1_kwh=float(abs(solution.grid-reference.grid).sum()),
                            soc_max_change_kwh=float(abs(solution.soc_end-reference.soc_end).max()),
                            balance_residual=solution.balance_residual,
                            soc_residual=solution.soc_residual))
    frame = pd.DataFrame(rows)
    frame.to_csv(output / 'instances.csv', index=False)
    # 汇总保留最大动作变化，避免只用小目标变化掩盖并列解敏感性。
    grouped = frame.groupby(['parameter', 'ratio'], sort=False)
    summary = grouped.agg(
        instances=('objective', 'size'),
        mean_objective_change_pct=('objective_change_pct', 'mean'),
        max_abs_objective_change_pct=('objective_change_pct', lambda x: abs(x).max()),
        max_grid_l1_kwh=('grid_l1_kwh', 'max'),
        max_soc_change_kwh=('soc_max_change_kwh', 'max'),
        max_balance_residual=('balance_residual', 'max'),
        max_soc_residual=('soc_residual', 'max')).reset_index()
    summary.to_csv(output / 'summary.csv', index=False)
    protocol = dict(
        scope='32 fixed LP windows; not annual policy reoptimization',
        ratios=[0.8, 0.9, 1.0, 1.1, 1.2],
        solves=288, recorded_rows=len(frame),
        historical_states='formal S3 dispatch at the same decision time',
        baseline='same S0 reference day-ahead contract',
        parameters_selected_again=False,
        config_sha256=hashlib.sha256((frozen/'resolved_config.json').read_bytes()).hexdigest())
    (output/'protocol.json').write_text(json.dumps(protocol, indent=2))
    print(summary.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
