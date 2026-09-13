# 当前论文排版重建

本目录对应正文与摘要、参考文献合计24页的修订版。原数值流水线中的文档生成器保留原样，不会生成本次新版；请使用本目录入口。

在支撑材料根目录安装原requirements.txt后执行：

```sh
python 论文修订源文件/build.py
```

输出在本目录：C题论文_v3.docx。该入口已从实际交付目录试跑，并核对解包后的Word XML与定稿一致。正文为body.md，摘要为abstract.txt；source/current_v3.docx仅作保留原公式、结果表和完整旧源码的构建底稿，不能误作本次定稿。新诊断数据从上一级research/parameter_perturbation读取，程序全文从上一级scripts读取。

figures保存已核验的两张新增图的PNG与SVG。需要重画时，先安装宋体和Times New Roman；可用环境变量SIMSUN_FONT指定合法宋体文件，再运行python 论文修订源文件/make_figures.py。图表字体需人工核对，缺字体时不应直接用替代字体导出比赛稿。

DOCX使用A4、四边2.5厘米、宋体与Times New Roman、单倍行距、正文12磅。定稿PDF是在安装相应字体的LibreOffice环境渲染并逐页检查的版本。其他Word/LibreOffice版本的字体度量可能改变分页；改动后请重新导出并确认附录仍从第25页开始。桌面顶层同名PDF是本次已核验的阅读版本。本目录提供可重建DOCX的全部输入，不承诺不同排版软件逐像素相同。
