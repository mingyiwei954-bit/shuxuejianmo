# V3 实质改进版 · 当前队伍交接版本

本仓库根目录对应桌面 `V3实质改进_20260913/修订成果`，是进入队员人工核验阶段的最新候选版。GitHub 与 Gitee 的当前文件树一致，旧版文件已从当前分支移除；Git 提交历史用于回退。没有额外套一层 V3 文件夹，也不混入原版快照和本机工作记录。

## 先看这些文件

- [论文 PDF](C题论文_实质改进版.pdf) · [论文 DOCX](C题论文_实质改进版.docx)
- [五份正式结果工作簿](workbooks)
- [改进前后对照报告](改进前后对照报告.md)
- [支撑材料 ZIP](支撑材料.zip) · [源码、配置和复现说明](支撑材料/README.md)
- [交付核验](交付核验.json) · [桌面交付文件哈希](SHA256SUMS.json)

论文共115页：摘要独占第1页，含摘要与参考文献23页，附录从24页开始，包含指定结果表和完整源码。正式算法和五份工作簿未改变。本轮新增32段验证、32段正式期连续回放；人工核验、身份页及实际比赛提交仍须队员完成。AI详细说明与声明原样保留，未重新评价。

## 完整诊断 ZIP 的无损恢复

唯一的存储形式调整：桌面 `诊断完整明细.zip` 为115,504,865字节，超过GitHub普通Git单文件100 MiB限制。两个平台都保存相同的三段字节分卷；不需要Git LFS或额外Python包。论文、源码、工作簿和约18MB的比赛支撑包拉取后即可直接使用。

在仓库根目录运行：

```bash
python3 恢复完整诊断.py
```

Windows也可使用 `python 恢复完整诊断.py`。脚本先验证三个分卷，再恢复与桌面逐字节相同的ZIP，并核验桌面交付清单中的全部466个文件。已存在且相同的ZIP可重复校验；已有不同文件不会被覆盖。完整ZIP是研究复核明细，不是受20MB限制的比赛支撑上传包。

如需使用完整逐时轨迹，将恢复出的ZIP解压到 `支撑材料` 内，使ZIP中的 `diagnostics` 与已有同名目录合并。原始题目和Excel附件另从比赛原材料提供。

## 复现入口

在 `支撑材料` 目录运行，`--source-root` 指向其下包含 `C题/附件` 的父目录：

```bash
python reproduce.py restore
python reproduce.py audit --source-root '<原始输入父目录>'
```

其他数值、诊断、工作簿及当前论文生成入口见[复现说明](支撑材料/README.md)。数值计算和文档生成依赖不同，不能假定只安装Python即可重新生成PDF和工作簿。

`交付说明.md`、`交付核验.json` 中关于桌面绝对路径、快照和“本轮未上传”的文字记录的是先前本地交付时点；本次发布状态及相对路径以本README为准。文件保持桌面原字节，避免破坏已核验哈希。

两个仓库：[GitHub](https://github.com/mingyiwei954-bit/shuxuejianmo) · [Gitee](https://gitee.com/ming-yiwei/muzhi)。文件限制依据：[GitHub官方说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。
