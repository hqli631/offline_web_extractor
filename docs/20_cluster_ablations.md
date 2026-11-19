# 实操20：固定阈值比较DOM特征

Gate5的开发实验交付已完成；这是可解释原型的验收，不是自动聚簇上线或独立泛化验证。Gate1—4的历史报告及聚簇v1均保留。

## 数据和固定设置

扩展清单共13个真实开发快照、78个页面对。其中5个Sphinx文档构成10对正例，3个IANA帮助页构成3对正例；其余65对为人工异组。另有5个合成漂移页，3对同组、7对异组，单独统计。正文金标准不参与结构特征计算；web.dev已评分验证页保持隔离。

人工分组先看正文容器和页面骨架，再运行相似度。Python标准库索引虽然以列表为主，但共享文档容器，最终并入文档组；搜索页的直接子节点是表单和结果区域，另作同站负例。原始采集假设和结构复核理由见samples/clustering/README.md，未根据分数改变标签。

五种特征、阈值0.7及连通分量算法见CLUSTER_ABLATION_PROTOCOL.md。扩展清单SHA256为dbb212a63113aea190eb698c57d64c2b84ba306f6ed000cee4bf513ec609cf53。

## 结果

| 模式 | 真实误聚/65 | 真实漏聚/13 | 合成误聚/7 | 合成漏聚/3 |
| --- | ---: | ---: | ---: | ---: |
| full-counts | 0 | 10 | 3 | 0 |
| full-presence | 0 | 9 | 7 | 0 |
| full-capped | 0 | 11 | 7 | 0 |
| semantic-presence | 0 | 11 | 5 | 2 |
| suffix-capped | 0 | 6 | 7 | 0 |

误聚/漏聚以最终连通分量的成员关系判定，不是直接阈值边数量。报告每项都有输入/实现哈希、逐对分数、分组及链式警告，位置outputs/clustering_v2/。

## 读懂三个失败

1. 长短差异：课前甜点与Python速览在full-counts下只有0.1036；代码、嵌套章节和列表数量会主导完整路径计数。去频次提高至0.3986，仍低于阈值，说明完整路径深度和形状也在影响结果。
2. 局部路径的代价：suffix-capped使解释器、速览和控制流三页聚到一起，但课前甜点和索引仍与它们分离；合成组全部合并，7对异组全部误聚。不能把真实小集合漏聚减少解释成泛化提升。
3. 链式合并：full-counts下IANA Example Domains分别与abuse/whois达到0.7244/0.7037，而abuse与whois只有0.6382，最终仍同簇。本例恰好符合人工同组，但同样的传递机制可以把错误边扩散。

role上下文能区分标签相同而role不同的页面，但该合成标签只描述布局相同，因此引入2对漏聚。它还把IANA的一页拆开。语义属性有助于解释规则适配性，却不能直接替代正文质量评价。Gate4的content-moved仍提醒我们：唯一命中、结构接近都可能只提取2/3正文。

## 复现与下一步

在项目目录运行（选择新的输出目录）：

    python tools/run_cluster_ablations.py --output-dir outputs/clustering_reproduce

若VS Code的python环境未装lxml，使用run.cmd所选择的项目环境，或直接运行单组：

    .\run.cmd cluster samples/dom_similarity.expanded_development.json --threshold 0.7 --feature-mode suffix-capped --output outputs/cluster_suffix.new.json --report outputs/cluster_suffix.new.md

这一小集合只有两种多页模板，其余模板为单例，0次真实误聚不足以说明可靠；没有新模板留出成绩。本轮不选择“最优通用模式”，不把聚簇分数作训练奖励。后续Agent先用明确的参考组生成受限规则，再独立检验0/1/多匹配和抽取内容；Gate7冻结独立参考/测试切分后才评估泛化。

学习任务：打开real.full-counts.json的chaining_warnings，对照三篇IANA的pair分数；再看controlled.suffix-capped.json的components，说明为什么“分到同簇”不能直接当“可以共享规则”的证据。
