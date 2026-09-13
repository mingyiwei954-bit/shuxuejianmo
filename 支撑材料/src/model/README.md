# 当前模型接口

唯一正式入口为scripts/run_model.py及run_pipeline.sh。risk.py实现因果历史场景与共享动作随机LP；rolling.py执行正式承诺并从同一链计算逐次费用；experiments.py包含启动、训练和年度对照。config/final.yaml为候选配置，冻结后的resolved_config.json记录一月选型结果。未经显式传入启动状态的simulate调用会报错。

正文定义、假设和公式见paper/main.md。原始观测不被修改。所有价格按交付区间结算的假设已明确披露。旧实验分支已不属于当前可执行模型。
