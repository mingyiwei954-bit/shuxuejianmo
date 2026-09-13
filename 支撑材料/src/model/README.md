# 正式模型与当前复现接口

当前统一入口为根目录 reproduce.py，run_pipeline.sh 转发对应阶段。`numeric` 从已冻结的一月解析配置重新求解，写入独立 outputs/recomputed_formal；`restore` 仅恢复原结果；`diagnostics` 运行本轮新实验。

risk.py 实现因果历史场景与共享动作随机LP；rolling.py 执行合同与连续储能状态；experiments.py 包含一月启动、原选择网格和正式期模型及对照。这些正式模型Python文件本轮未修改。scripts/run_model.py 为保留的旧数值接口，不承担当前论文生成。

config/final.yaml 保留原候选默认值，正式算法必须读取 frozen/resolved_config.json 中的一月选定结果。当前论文定义、假设、公式与新证据见论文修订源文件/body.md 和 scripts/revision_document.py，旧稿 paper/main.md 已移出交付，避免误用。

原始观测只读。价格按交付区间结算是本文明确披露的解释；同路径另一制度的重计费不等于该制度下重新优化。
