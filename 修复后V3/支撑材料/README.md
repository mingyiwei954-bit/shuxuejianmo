# V3闭环修订支撑材料

原始输入为官方C题及附件，未修改观测。先在config/final.yaml配置source_root（其下应含C题/附件），或设置CUMCM_SOURCE_ROOT。运行run_pipeline.sh即可重建；运行环境需Python及requirements.txt、Node与@oai/artifact-tool，DOCX转PDF使用Codex文档运行时。对冻结结果只读检查可先执行scripts/unpack_frozen.py。

frozen保存全精度结果，CSV按列去重后固实XZ压缩，未舍入任何数字。csv_manifest保存每份CSV的原始SHA256；unpack_frozen将逐字节恢复并校验，另恢复重复S3轨迹及正式子账本，输出到outputs/c_final_v1/frozen，随后可运行src/audit/audit_final.py --workbooks。主结果S3与S0/S1/S2共享参考日前承诺；所有年度状态来自一月可核验启动账本。训练配置见resolved_config，不能用未解析默认值替代。

论文费用按取消退原价保留50%违约费、交付物理区间价解释；同路径逐次与不退款费用另列。不声称其他结算解释下最优。历史场景为预测分布，非伪造的实际数据。未宣称团队已经完成提交签核。
