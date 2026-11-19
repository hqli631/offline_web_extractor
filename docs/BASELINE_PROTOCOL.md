# 静态基线协议 v1

基线使用 Trafilatura 2.0.0，环境隔离在项目 .baseline-venv。run.cmd 和原Python环境不变。生产提取器与基线在同一个隔离解释器、同一个 lxml 版本下比较，以免把解释器差异当成算法差异。完整依赖版本在 requirements-baseline.txt 固定，每份结果再保存环境包清单、Python、系统和源码哈希。

## 安装与执行

已有本机隔离环境可直接运行。新环境使用可用Python创建 venv 后安装 requirements-baseline.txt：

    python -m venv .baseline-venv
    .\.baseline-venv\Scripts\python.exe -m pip install -r requirements-baseline.txt
    .\.baseline-venv\Scripts\python.exe tools/compare_baseline.py samples/evaluation_manifest.expanded_development.json --output outputs/baseline.development.v1.json --report outputs/baseline.development.v1.md

输出已存在时拒绝覆盖，改用新版本名。当前脚本只接受 development，且检查 sample_registry 中封存验证用途，不能通过改manifest标签偷偷纳入预留页。整个实验只读本地HTML，不抓取网络，不改变参考答案，也不按页面切换基线参数。

## 固定设置

Trafilatura调用 bare_extraction，输出Python Document及其body XML。固定：include_comments=False、include_tables=True、include_links=False、include_images=False、include_formatting=False、deduplicate=False、with_metadata=True、favor_precision=False、favor_recall=False、fast=False、no_fallback=False。保留其默认回退，禁止逐页设置不同的 precision/recall模式。网页元数据解析在耗时内，但元数据除了title不计入正文。

二者收到相同原始HTML bytes，各自负责解析与编码推断。没有按标准答案纠正乱码或提前清洗输入；编码处理差异属于方法结果。比较的目标是同一保存的HTML，不能把解码失败默默替换成清洗后的版本。

## 同口径文本投影

参考使用 expected.blocks 全部正文，生产使用 result.blocks 全部正文，不再只测旧p视图。Trafilatura使用body XML中的正文文本，不使用包含作者/日期等元数据的JSON或页面description。代码、列表、引用、定义项、脚注和表格的文字纳入正文。

- 所有方法合并空白；正文块/行/单元格边界插入空格，普通行内元素不强插空格。
- 不比较Markdown渲染标记、自动列表序号、表格人工分隔符。生产/参考 table 中的空格竖线空格分隔符转为空格；这个基础表格协议无法区分字面同形分隔符，属于已知限制。
- title单独比较：参考正文已不含标题。生产与Trafilatura仅删除等于各自预测title的heading；不用参考title作为清洗规则。匹配标题的多个重复heading均删除，JSON记录移除数量并保留原始输出；这意味着标题重复问题不会被正文指标完整惩罚，应同时查看移除数量。
- 引用和定义等包装样式不进入文本分数。生产blocks_exact仍对参考协议评分，Trafilatura结构全匹配记为null，因为二者结构schema不同；不伪造可比的结构准确率。代码缩进和表格布局正确性也不能由本文字投影分数证明。

字符precision/recall基于字符次数交集，能诊断多提和漏提但忽略顺序，重复字符会掩盖语义错误。另报有序token相似度：汉字逐字、拉丁词和标点分词，SequenceMatcher(autojunk=False)计算序列匹配比例。这是对顺序敏感的诊断，不是精确编辑距离、语义正确率或统计置信区间。大小写、标点、实体解码后的实际字符不放宽。保存正文投影与原始输出以便复核差异。

## 计时与错误

每方法每页预热1次，再串行执行5次（最低3次），记录全部样本及中位数。按页面交替方法顺序，减少固定顺序偏差。计时包含bytes解析和抽取，不含文件读取、导入、文本投影、指标计算或报告写入。两方法导出的结构和元数据工作量不同，耗时是本机端到端抽取成本，不能推算千亿级CPU/GPU成本或工业吞吐。

每页输入哈希和参考哈希写入结果；生产所有源码在运行前后校验，期间被编辑则拒绝保存实验结果。异常逐页报告、进程非零退出；empty_body/no_candidate保留为实际方法状态，不能删掉失败页后只报剩余平均值。当前不报告一个合并成功率，需先看每页和类型分布。

正式实验须等本轮开发源码定稿后执行。本文件和脚本准备完成不代表对比实验已经通过。最终验证未包含在此开发组实验中，课程总览页不能混报成普通文章泛化。
