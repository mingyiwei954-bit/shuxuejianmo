# V3支撑材料：本次正文24页修订

原始观测、正式模型、已解析配置、冻结CSV和五份工作簿保留。此次新增scripts/parameter_perturbation.py、research/parameter_perturbation及论文修订源文件。AI详细说明按用户要求暂未重审或补写。

## 数据恢复及数值复验

原题父目录下应包含C题/附件。设置环境变量CUMCM_SOURCE_ROOT指向该父目录，或配置config/final.yaml的source_root。在本支撑目录安装requirements.txt后执行：

```sh
python scripts/unpack_frozen.py
python src/audit/audit_final.py --workbooks
```

frozen/columns.tar.xz中的56份CSV按原始字节恢复并核对校验值，结果位于outputs/c_final_v1/frozen。恢复后原正式记录、真实承诺链和全年补充轨迹可供独立审查。完整数值流水线为run_pipeline.sh，工作簿导出另需Node与@oai/artifact-tool；该旧流水线的文档步骤仍生成旧版排版。

## 本次补充检验

在原题路径配置好、冻结CSV恢复后执行：

```sh
python scripts/parameter_perturbation.py
```

固定四个指定日期、两种电价、每日四个更新时点，共32个窗口。分别扰动终端惩罚倍数与额定功率，比例为80%、90%、100%、110%、120%；288次实际求解，基准复用后保存320条记录。该实验固定历史初始状态、日前合同和场景，不是全年重新优化，不用于重新选择正式参数。结果在research/parameter_perturbation中。

既有补充证据程序为scripts/strengthen_evidence.py。参数候选为evidence/january_parameter_validation.csv；正式锁定值为恢复后的frozen/resolved_config.json；源数据与源码来源为evidence/source_provenance.json。各历史记录的时间及范围保持原意，本轮没有重跑全部年度正式优化。

## 当前论文重建

```sh
python 论文修订源文件/build.py
```

详见论文修订源文件/README.md。底稿仅用于构建，顶层交付论文才是定稿。附录2.1收录原32个源码及配置，附录2.2收录新增扰动程序；两类源码清单分别见evidence/source_appendix_manifest.json及evidence/source_appendix_manifest_current.json。本次支持包哈希以根目录SHA256SUMS.json为准。
