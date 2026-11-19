# 执行记录

## 2026-11-13：Gate4验收与Gate5首轮结构实验

- reuse新增可选完整参考评测、expected哈希、源码前后指纹核验与非空输出拒绝覆盖；运行状态和质量分开。真实Sphinx2页唯一命中，16/32块；无完整迁移gold不报准确率。
- 合成漂移5页有独立字面标准与变异来源；真实/漂移命令子进程退出0/2均核验。末段移出容器仍status=ok，召回2/3；0/多匹配拒绝执行。最终报告目录rule_reuse_gate4_final、drift_lab_gate4_final。
- 规则项目完整报告已交付，Gate4通过。新增DOM相似度原型和cluster命令；7真实页、5合成页分开，阈值0.7运行前声明。真实漏聚1对、合成误聚3对；role变化相似1.0但规则不适用。
- 73项测试通过。下一步扩充组内正例及结构特征对照，再进入单Agent。总目标未完成。

## 2026-11-13：通用结构修复与成熟基线验收

- 生产：正文候选/标题优先级、header摘要、清理后标题节点身份；quote、定义列表、普通列表脚注与孤立li恢复。审查发现3处回归均已修复并加入测试。
- 验证：run.cmd test 64项通过；原开发集3真实+1合成结构保持匹配；扩展开发组5页标题一致，GNU133块结构全匹配；其余模板边界保留。
- 基线：Trafilatura2.0.0隔离安装，完整依赖固定；同Python/lxml、相同原始HTML、预热1次测5次、全文块文本与顺序指标。正式结果 outputs/baseline.development.v2.json/md；v1审查前结果保留。
- 冻结与验证：baselines/rules-validation-release-v1保存最终源码及web.dev答案哈希，再首次评分；47/45块、P0.9362/R0.9778、结构不全匹配。保持验证用途，不据此修规则。
- 文件核验：正式基线源码哈希与当前源码一致；10个方法/页面结果均无运行异常、各有5次耗时；check_corpus无错误。
- 闸门：Gate2/3实验交付通过（不等同所有页面提取通过）；当前Gate4固定规则复用与漂移报告。总目标仍未完成。详见docs/17_semantics_and_baseline.md。

## 2026-11-13：MDN 范围确认与 Gate 2 收尾

- 目标：落实用户三项 MDN 范围选择，保证状态记录和实际文件一致，推进样本扩充。
- 完成：MDN annotation/source 状态同步；保存历史 initial 记录；新增当前 sample_registry；W3C 历史记录中的 HTML 哈希转录纠错，HTML 与首次报告未改。
- 代码：补齐 table 渲染，采用文本围栏；3 项定向测试验证不重复提取、不变成列表及字面符号保留。
- 验证：run.cmd test 共52项通过；run.cmd batch --output outputs/batch_after_table.json --report outputs/batch_after_table.md，开发集3真实+1合成均结构匹配。
- MDN 当前评测：outputs/mdn.candidate.current_evaluation.json；历史 first/after_boundary 报告保留。expected 哈希未变；复杂列表序列化差异仍存在。
- 样本：已补 NASA Voyager 新闻与 GitHub Copilot 博客完整快照、来源哈希和范围模板；新增候选共7页。第二篇 web.dev 请求超时，未保存残缺响应。
- 下一步：完成 GNU 范围复核与独立标准答案；标注新闻、博客等其余6页；预留 web.dev 站点验证；先统一标注再预测。
- 闸门：Gate 2 未通过。已用于修复的页面不作为最终验证；候选 HTML 不等于完成评测。

## 2026-11-13：独立参考扩充与首轮错误

- 原文审读及DOM辅助独立转录：GNU133块、NASA20块、GitHub20块、W3C短页22块；均在各自首次预测前冻结答案和源码版本。web.dev45块课程总览参考已冻结，未运行预测。
- 独立复核：四份开发参考块串与声明范围非空白原文按顺序一致；发现GitHub/W3C引用口径差异，进入v2协议修订，保留旧答案报告。
- 首次发现：GNU标题/目录/定义列表，NASA元数据/记者联系/推荐，GitHub坏HTML列表/强调框，W3C短页no_candidate。没有据此修改生产提取器。
- 工具：tools/summarize_first_pass.py只读报告生成差异表；tools/check_corpus.py检查哈希、嵌入答案、预留验证用途，无错误。
- 规模取舍：RFC与WHATWG长页不截断，暂缓；补完整W3C短页。当前8快照中6页已标注可用，5开发首次报告+1封存验证。
- 环境：当前Python没有Trafilatura/Readability；成熟基线尚未运行。web.dev短教程URL再次超时，不保存残缺网页。
- 下一步：统一引用结构协议、同版本开发汇总、静态基线；验证评分等开发版本冻结后执行。Gate2仍不宣称全部通过。

本轮收尾：引用协议v1.2及W3C短页expected.v2已新增，仅5处kind改变，正文文字与顺序不变；历史first/expected保持原哈希。同版本开发manifest与 outputs/expanded_development.frozen.md 已执行：5页已评分、运行错误0、结构全匹配0。此处“运行错误0”不等于5页抽取成功，W3C返回no_candidate。生产源码逐文件校验与冻结快照一致，本轮未修改，因此没有重复运行代码回归测试。
