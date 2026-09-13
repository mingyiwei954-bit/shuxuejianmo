# 当前论文构建源

当前入口在支撑材料根目录：`python reproduce.py paper`。它读取本目录的 body.md、abstract.txt、build.py，读取已冻结的正式结果和 diagnostics 本轮实验，再生成 publication 中的当前 DOCX/PDF。最终页数以 publication/structural_checks.json 为准，不沿用旧版页数记录。

source/current_v3.docx 是保留原生公式、已核验结果表和图的构建底稿；不是最终论文。当前完整源码附录从实际项目文件逐行生成，哈希见 evidence/source_appendix_manifest_revision.json。旧 manifest 仅用于保留原源码文件清单，旧文档生成器不参与当前入口。

需要先执行 restore，并保留完成的 diagnostics 汇总、research 既有证据和 figures。只运行本目录 build.py 可以生成 DOCX，但不包含 PDF 渲染与交付门禁，故推荐根目录统一入口。

正文采用 A4、四边2.5厘米、宋体与 Times New Roman、正文12磅。PDF 渲染需要合法安装且可见的中文字体；本机入口会生成字体目录配置。可指定 FONTCONFIG_FILE；缺字时必须修复字体后重渲染。不同 Word/LibreOffice 环境可能改变分页，改动后应重新检查摘要专页、正文页数和表格。

figures 中包含保留的绘图源与图片。实际采用的插图由 build_meta.json 列示；没有采用的旧图只是构建资源，不代表新增实验。

本轮AI声明来自ai_statement.txt，详情文字来自上级evidence/ai_usage.json；附录完整列出evidence/support_file_list.json的文件。请使用支撑根目录reproduce.py paper一起生成论文和AI详情，不能再从旧底稿复制AI声明。
