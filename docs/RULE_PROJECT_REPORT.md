# 离线网页正文规则提取项目报告

版本：规则项目阶段交付；更新于2026-11-13。Gate 1—4证据已完成，聚簇、Agent、Rubrics、微调与强化学习仍在后续阶段；本文不宣称整个学习工程完成。

## 任务与实现范围

项目从保存的公开HTML快照中提取标题与正文，输出结构化JSON及便于VS Code预览的Markdown。实现独立于旧半成品web_extract_demo，没有复制其源码或样本。默认启发式选择候选容器，也允许手动指定XPath；HTML解析与XPath执行使用lxml。

处理链路是：读取原始HTML bytes → 解析DOM → 候选评分或执行指定XPath → 清理噪声 → 识别标题与摘要 → 按DOM顺序提取结构块 → 渲染并评测。CPU复用仍有解析、存储、执行与维护成本；本项目没有测量工业规模成本。

当前支持普通段落、基础有序/无序及嵌套列表、h2—h6标题、pre代码块、引用、定义列表、基础文本表格、语义脚注，以及通过数字引用链接识别的普通列表脚注。代码块保留换行缩进；表格仅保留文本行列，Markdown以文本围栏展示。损坏HTML产生的孤立li可恢复为列表项。

不支持任意JavaScript加载内容、图片OCR、复杂合并单元格、所有div裸正文或任意网站模板。没有p包装的复杂引用、任意字母/星号脚注编号和所有旁注边界也未完全覆盖。status=ok仅表示产生了支持的结构块。

## 数据、划分与标注

原始开发回归集为Python官网简介、Python中文课前甜点、IANA Example Domains三个真实页，加一个合成列表实验页。Python解释器页用于人工同模板迁移检查。W3C中文无障碍简介经过首轮诊断和修复，现为开发用途，不能继续作为未调参验证。

新增候选池有8个完整快照：

| 用途 | 页面 | 说明 |
| --- | --- | --- |
| 开发 | MDN HTML基础语法 | 141块，含表格与代码；已参与修复 |
| 开发 | GNU What is Free Software? | 133块，含History定义列表与脚注 |
| 开发 | NASA Voyager新闻 | 20块，正文RSVP邮箱保留，末尾记者联系排除 |
| 开发 | GitHub Copilot博客 | 20块，含摘要、引用、损坏HTML列表 |
| 开发 | W3C link text短文 | 22块，文章参考保留，系列介绍排除 |
| 封存验证 | web.dev Learn HTML课程总览 | 45块；冻结规则后首次评分，未用于调参 |
| 暂缓 | RFC 2616、WHATWG HTML全文 | 保留完整长快照，未截断，未算作完成评测页 |

当前用途以samples/sample_registry.json为准。历史initial清单记录历史首轮，不代表当前划分。HTML、来源URL、获取时间和SHA256保存在各页source.json；新标准答案、范围笔记及独立辅助脚本共同保留。

标准先审读原始HTML并确定范围，再用独立DOM脚本辅助转录，冻结expected哈希后首次预测。辅助脚本不导入生产抽取或渲染函数，也不读预测选择答案。另一次源文复核检查GNU、NASA、GitHub、W3C短页的声明范围块串与非空白原文顺序一致。这是助手独立审读与辅助转录，不是用户逐项确认或多人标注金标准。

结构协议v1.2继承v1.1，并将blockquote内实际p统一为quote。W3C短页有五处kind从paragraph迁移为quote，另存expected.v2.json，文字顺序不变；原v1答案和首次报告不覆盖。GitHub按语义重建损坏HTML中的三个孤立列表项，并排除伪标签碎片，该决定在预测前记录。旧paragraphs仅是实际p视图，不能替代全部结构块评测。

## 规则开发与失败复盘

首轮发现的问题分为：候选容器缺失或过宽、标题识别、噪声边界、结构支持不足，以及标注序列化差异。未采用“段落够长就是正文”作为唯一依据。

通用修改增加article、entry-content、post__content等精确class token及id=main候选；优先附近文章h1，再考虑开头h2，最后回退全站h1。较窄正文容器可关联语义header中的摘要。清理后通过节点身份处理标题，避免广告删除导致位置XPath错删。

结构修改加入quote、dt/dd、被数字引用指向的普通列表脚注和孤立li。正文旁注不能因aside标签一律删除；明确complementary、navigation、toc和author-bio等信号用于去噪，但仍是启发式。

审查发现并修复三处实现回归：正文h2盖过祖先文章h1、header内部摘要重复，以及清理广告后按旧位置删除真实标题。每一处都有最小回归用例。最终记录64项测试通过；原开发集3真实+1合成仍结构全匹配。

## 同版本开发前后对照

以下均使用扩展开发组及同一参考版本（W3C引用v2）。前报告为expanded_development.frozen.json，后报告为expanded_development.after_review.json。它们是开发对照，不是未见测试成绩。

| 页面 | 标准块 | 修改前预测块 / 块文本P/R | 修改后预测块 / 块文本P/R | 修改后结构全匹配 |
| --- | ---: | --- | --- | --- |
| MDN | 141 | 145 / 0.9586 / 0.9858 | 145 / 0.9586 / 0.9858 | 否 |
| GNU | 133 | 100 / 0.7900 / 0.5940 | 133 / 1.0000 / 1.0000 | 是 |
| NASA | 20 | 35 / 0.5714 / 1.0000 | 23 / 0.8696 / 1.0000 | 否 |
| GitHub | 20 | 32 / 0.5000 / 0.8000 | 25 / 0.8000 / 1.0000 | 否 |
| W3C短文 | 22 | 0 / 0.0000 / 0.0000 | 26 / 0.8462 / 1.0000 | 否 |

修改后五页标题均正确，GNU133块结构匹配；其余失败未隐藏。MDN复杂列表中的说明—代码—续段与原参考拆分不同，不能将块文本漏匹配直接解释为全部文字丢失。NASA多提-end-和两段记者联系；GitHub多提伪标签碎片、标签与作者提示；W3C多提About QA Tips系列介绍。

## 成熟静态基线

基线为Trafilatura 2.0.0，完整依赖固定于requirements-baseline.txt，并安装在隔离.baseline-venv。两种方法在同一个Python/lxml解释器接收相同原始HTML bytes；未根据标准答案预清洗输入。固定参数包括不提评论、提表格、不展开链接、不提图片、保留默认回退、不开逐页precision/recall模式。

生产与参考使用全部blocks文字，基线使用其body XML文字。标题单列；只移除等于各自预测title的heading，不用答案修正预测。投影合并空白，排除Markdown标记、自动编号及表格序列化分隔符。生产结构全匹配单独计算；基线schema不同，结构指标为null。

| 页面 | 本项目字符P/R | Trafilatura字符P/R | 有序token相似度（本项目/基线） | 中位耗时ms（本项目/基线） |
| --- | --- | --- | --- | --- |
| MDN | 0.9999 / 1.0000 | 0.9946 / 0.9588 | 0.9933 / 0.9695 | 49.814 / 65.972 |
| GNU | 1.0000 / 1.0000 | 0.9908 / 1.0000 | 1.0000 / 0.9955 | 21.652 / 29.320 |
| NASA | 0.9413 / 1.0000 | 0.9528 / 0.9982 | 0.9624 / 0.9493 | 87.963 / 69.921 |
| GitHub | 0.9910 / 1.0000 | 0.9856 / 0.9443 | 0.9945 / 0.8562 | 57.113 / 54.257 |
| W3C短文 | 0.7089 / 1.0000 | 0.6951 / 1.0000 | 0.8434 / 0.8293 | 5.606 / 7.411 |

字符次数交集忽略顺序；重复字符可掩盖语义错误。有序token指标是SequenceMatcher诊断相似度，不是精确编辑距离或事实正确率。文本投影也不证明代码缩进、表格布局或列表层级正确。

每方法每页预热1次，串行测量5次，交替方法顺序，报告全部样本和中位数。计时含bytes解析与提取，不含导入、文件I/O、投影或评测；依赖本机负载、方法工作量也不同。本项目并非每页更快，不能推算工业吞吐或千亿级降本。正式逐页结果为outputs/baseline.development.v2.json/md，审查前v1报告保留。

## 封存验证

开发源码与web.dev HTML/expected哈希先冻结于baselines/rules-validation-release-v1/manifest.json，随后保存webdev-learn-html.candidate.validation_first.json；当前标记validation_scored、tuning_used=false。

标题Learn HTML正确。预测47块、参考45块，块文本P=0.9362、R=0.9778，blocks_exact=false。开头混入Go back导致原句不再精确匹配，另多提Quiz和领徽章说明；不是完全漏掉开头。验证结果保留，不据此调参。

该页是课程总览，课程卡片主题和摘要即其主要内容，不能混报为普通文章验证。只有一个封存站点页面，无法代表新闻/博客泛化，也未在该验证页比较Trafilatura，不能扩大对比结论。

## 固定规则复用与漂移

已有sphinx-main-v1规则为//div[@role='main']，来自已检查的课前甜点参考页；同一条规则应用到解释器页，不自动修复或回退评分器。两个页面曾用于实现开发，因此即使复用命中，也不是新的未见验证。

真实页报告：outputs/rule_reuse_gate4_final/report.json/md。规则指纹为2befe90e5d3f3fe904ca8135d0e7dba26f511230eb6e53c864a7ceee11f52446，两页各命中1个容器，输出16/32块。迁移页6个代码块、5个子标题、1个脚注；没有完整独立参考，quality=null，不报告正文准确率。

受控漂移报告：outputs/drift_lab_gate4_final/report.json/md。原始参考和仅class变化为1匹配、3/3段结构一致；role改名为0匹配，响应式重复为2匹配，分别拒绝执行。末段移出容器仍1匹配且status=ok，但仅2/3段，块文本P=1、R=2/3，blocks_exact=false。这是合成受控变异，不是真实网站自然漂移或泛化准确率。

规则从参考冻结，不逐页修复或回退；expected哈希不符拒绝评分，源码前后哈希不一致拒绝报告，非空输出目录拒绝覆盖。CLI返回0只说明所有运行状态ok，不表示全文质量正确。漂移集合预期退出2，最终核验以Python子进程返回码和JSON断言为准。详细复盘见docs/18_rule_drift.md。

## 可复现操作

在PowerShell执行，使用.cmd入口，无需更改系统脚本策略：

    Set-Location 'D:\codex project\offline_web_extractor'
    .\run.cmd test
    .\run.cmd batch --output outputs/reproduction.old_dev.json --report outputs/reproduction.old_dev.md
    .\run.cmd batch samples/evaluation_manifest.expanded_development.json --output outputs/reproduction.expanded_dev.json --report outputs/reproduction.expanded_dev.md
    .\run.cmd reuse samples/sphinx_reuse.json --output-dir outputs/reproduction.sphinx_reuse

成熟基线使用独立环境；已存在输出名拒绝覆盖，应使用新版本名：

    .\.baseline-venv\Scripts\python.exe tools/compare_baseline.py samples/evaluation_manifest.expanded_development.json --output outputs/baseline.reproduction.json --report outputs/baseline.reproduction.md

新电脑先用Python 3.10+安装requirements.txt；基线另建venv并安装requirements-baseline.txt。run.cmd优先项目.venv，其次本机Codex Python，再寻找系统Python。输入文件、清单和source哈希须一致；tools/check_corpus.py只核验文件身份和用途，不证明标注质量或真实时间顺序。

## 后续阶段与面试表述

Gate 4完成后进入DOM结构特征与聚簇；以误聚/漏聚证据决定规则共享，再实现单Agent生成受限XPath/JSON、执行反馈与有限修复。Rubrics需人工对照与稳定性校准后才作为奖励；SFT、LoRA和小型RL实验仍未执行，不能在简历中写成已完成。

当前可据实讲述的项目是：独立实现lxml结构化正文提取与评测，对多类真实HTML保存来源和版本，保留首轮失败并修复通用容器/结构问题，在5页开发组与Trafilatura固定设置对比，并保留一个课程总览页的封存验证失败。任何分数必须附上样本、切分与指标口径。
