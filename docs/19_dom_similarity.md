# 实操19：标签结构相似度与规则可复用的差别

Gate4的固定规则和漂移实验验收后，开始Gate5。当前只实现并运行第一版结构基线，尚未通过完整聚簇阶段验收。

## 特征与初始协议

将body下每个节点的相对标签路径计入Counter，例如 main/div/p。忽略正文、class、id、role、URL和兄弟序号；script/style/noscript/template跳过。用多重集合Jaccard（次数交集/次数并集）计算页面相似度。

阈值0.7是运行前声明的初始开发值，不是经验证得到的最佳阈值。阈值连边后取连通分量；若同一分量内存在低于阈值的页面对，单列链式聚簇警告。当前人工分组是布局假设，不是抽取正确性标签。

真实开发组7页，多数模板只有1页；仅两篇Python教程人工同组。合成组另存，不混合统计。web.dev已评分验证页不进入聚簇开发。

## 复现

    .\run.cmd cluster samples/dom_similarity.real_development.json --threshold 0.7 --output outputs/dom_similarity.real.reproduce.json --report outputs/dom_similarity.real.reproduce.md
    .\run.cmd cluster samples/dom_similarity.controlled.json --threshold 0.7 --output outputs/dom_similarity.controlled.reproduce.json --report outputs/dom_similarity.controlled.reproduce.md

原始结果：outputs/dom_similarity.real.v1.json/md、outputs/dom_similarity.controlled.v1.json/md。输出存在拒绝覆盖；HTML哈希不符逐项报错。即使修改清单split，也不能把registry中的封存/已评分验证页混进开发。

## 实测与反例

- Python课前甜点与解释器：相似度0.3741，人工同模板却被拆开，真实组漏聚1对。完整路径频次会受文章长度、代码与列表数量影响。
- reference与class-drift：相似度1.0，符合忽略class的特征定义，冻结role规则仍可用。
- reference与role-drift：相似度1.0，标签相同但role规则0匹配。这不是算法实现错误，而是丢弃语义属性导致无法推断规则兼容性。
- content-moved相似度0.7273，超过阈值，被并入原布局组，产生3个误聚页面对；Gate4同页只有2/3正文。因此结构接近仍会漏提。
- duplicate-main为0.6429，本轮分离；不能据一个合成例推断所有响应式重复都能识别。

真实组0误聚也没有可靠的普遍意义：组内正例只有1对，单例很多。未观察到链式聚簇不等于该风险不存在；定向测试已覆盖A-B、B-C连边但A-C不连边仍合并的情况。

## 下一步实验

先扩充每个模板的独立开发页，增加组内正例与同站点不同布局负例；再对照路径去频次/频次截断、路径尾部特征、正文候选局部结构和语义role信号。保留v1，记录每项变化的误聚/漏聚，不能仅降低阈值使现有Python页合并。

聚簇输出只产生候选共享规则组，必须另跑固定规则匹配与全文质量检查。现阶段不自动把聚簇标签当成SFT或RL奖励，也不将语义role变化例从数据删除来提高分数。
