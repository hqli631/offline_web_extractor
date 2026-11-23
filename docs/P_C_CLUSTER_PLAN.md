# P-C 预注册计划：网页聚簇 + 同簇规则复用闭环（零调用）

> 状态：预注册草案→实施。零模型调用、零网络采集（仅用既有本地快照）。A→E 路线第三步。
> 核心逻辑：同类布局网页共用一套抽取规则，把（未来）GPU/LLM 推理成本分摊到海量页面；本阶段在本地小语料验证该机制的工程可行性与诚实边界，不宣称生产规模。

## 1. 现状与缺口

- 已有：dom_similarity.py（tag-path multiset Jaccard，6 特征消融，**连通分量**聚簇，阈值 0.7 冻结）；rule_reuse.py（单冻结 XPath 跨页复用+结构校验+P/R，不聚簇/不回退）；rule_agent.py（provider 接口规则搜索循环，ReplayProvider 非推理）；agent_rules.execute_rule/validate_rule（受信子进程执行引擎）；drift_lab 合成漂移夹具×5。
- 缺口：① 连通分量会**链式聚簇**（A-B≥thr、B-C≥thr、A-C<thr 仍并簇）→ 需 complete-linkage 抗链式；② O(n²) 全对比较 → 需 MinHash-LSH 候选生成（分摊成本的关键）；③ 无"簇→共享规则→缓存→回退→漂移"闭环；④ 无跨站家族分离评估。

## 2. 冻结参数（实施前预注册，不调参）

| 参数 | 值 | 依据 |
| --- | --- | --- |
| 聚簇阈值 threshold | 0.7 | 继承先前冻结消融（CLUSTER_ABLATION_PROTOCOL），本周期不调 |
| 特征模式 | full-counts（tag-path multiset Jaccard） | 历史 v1 基线，文本/属性/URL/兄弟索引全排除 |
| MinHash num_perm | 128 | 固定 |
| LSH bands×rows | 16×8（=128） | 候选阈值≈(1/16)^(1/8)≈0.56，召回导向；最终聚簇用精确 Jaccard≥0.7 |
| 漂移阈值 drift_threshold | 0.7 | 成员与簇心指纹相似度<0.7 → 标记漂移，走回退 |
| MinHash seed | 20261123 | 固定，确定性 |

## 3. 语料与split（诚实标注）

- **clustering-development（sphinx 族）**：python-appetite/interpreter/introduction/controlflow/library-index（sphinx-documentation×5）+ python-search（sphinx-search 同站负例）。阈值历史在此族冻结。
- **cross-site 评估族（iana-help×3）**：iana/iana-abuse/iana-whois。跨站、未调参；**非严格独立采集 holdout**（同属 development manifest），如实标注为跨站评估。
- **单例族**：gnu-essay/github-blog/nasa-news/mdn-doc（各1页，无复用伙伴）。
- **synthetic controlled（drift_lab×5）**：reference/class-drift/role-drift（reference-layout）+ duplicate-main + content-moved。与真实分母分离。role-drift：tag 布局同 reference 但 //div[@role='main'] 失效 → 检验"指纹相似但规则失败→回退"。

## 4. 组件与验证节点

1. **dom_lsh.py**：MinHash 签名（确定性 seed）+ LSH banding 候选对。验证：候选召回（所有精确 Jaccard≥0.7 的对必被 LSH 捕获，概率性→用固定 seed 实测）+ 候选数<全对数；签名确定性。
2. **dom_cluster.py**：complete-linkage 凝聚聚簇（合并要求两簇所有跨对≥threshold）+ 抗链式保证 + 诊断（簇内最小相似度）。验证：链式反例（CC 并 {A,B,C}，CL 分 {A,B},{C}）；语料上 CL vs CC 对比；簇内任意对≥threshold 不变式。
3. **rule_cache.py**：确定性结构化规则派生器（从代表页选唯一内容容器，零调用，走 validate_rule）+ 簇规则缓存（键=簇指纹）+ 成员执行校验（execute_rule 唯一匹配+status ok+block>0）+ 回退（规则失败→逐页 extract_html 启发式）+ 漂移检测（指纹距簇心<drift_threshold 或规则失败→标记）。验证：drift_lab role-drift 触发回退；reference 复用 ok；duplicate-main/content-moved 分离。
4. **run_pc_cluster_loop.py**：闭环 harness（指纹→LSH→CL→派生/缓存→执行/校验/回退/漂移→指标）。指标：簇纯度（vs 人工组，对精度/召回/ARI）、规则复用率（共享规则成功提取成员/总成员）、回退率、漂移标记数、有 expected 页的提取质量（drift_lab 合成单独）。输出 JSON+MD，拒覆盖，哈希，确定性。

## 5. 指标定义（预注册）

- 簇纯度：同人工组对中被聚同簇的比例（召回）；聚同簇对中同人工组比例（精度）；ARI。真实/合成分开。
- 规则复用率 = 经共享规则成功提取（status ok 且 block>0 且唯一匹配）的成员数 / 应复用成员数（簇大小>1 的非代表页）。
- 回退率 = 走逐页启发式的成员数 / 总成员数。
- 成本分摊代理指标：共享规则派生次数（=簇数）vs 逐页派生次数（=页数）→ 复用节省比例。零调用，仅计规则派生/执行次数（未来 LLM 成本的代理）。

## 6. 局限（诚实）

- 小语料（real 13 + synthetic 5），非生产规模；"千亿级"仅业务语境。
- iana 为跨站评估族，非严格独立采集 holdout；阈值继承非本周期独立冻结。
- 确定性规则派生器是结构化启发式（非 LLM Agent）；真实 Agentic RL/GRPO 属 P-E（gated）。
- 指纹排除属性 → role-drift 类漂移靠规则执行校验捕获，非指纹；如实说明两类漂移检测机制。
- 簇纯度≠提取准确率；规则唯一匹配≠正文完整（沿用 rule_reuse 纪律）。

## 7. 交付

- 4 模块 + 4 测试文件 + harness；docs/P_C_DELIVERY_REPORT.md（命令+哈希+指标+局限）；全套件回归；secret scan→commit→push。

## 8. Post-hoc 追加：特征模式敏感性消融（探索性 / 次要，非调参）

> 追加时点：预注册主运行（full-counts / 0.7 / complete-linkage，`outputs/pc.cluster_loop.v1`）完成后，观察到真实语料对召回 0.0769（sphinx-documentation×5 全成单例）。此为**如实保留的预注册主结果**，不回填、不改参数重跑主结果。

- 目的：解释"counts 类特征长度敏感 → 同模板页段落/代码数量差异导致过分裂"这一可解释机制；对照 presence 类特征（忽略数量差异，README 明示应容忍的同簇内差异）。
- 设计：同一 complete-linkage + 同一闭环，阈值 0.7、num_perm=128、bands 16×8、seed=20261123、drift_threshold=0.7 全部冻结不变；仅遍历既有 `dom_similarity.FEATURE_MODES` 六模式（full-counts/full-presence/full-capped/semantic-presence/suffix-capped/suffix-presence）。仅真实语料；controlled 闭环保持主参数。
- 纪律：这是特征模式消融，**不是阈值调参**；结果标注为探索性/次要。若未来采纳某模式为正式协议，须独立预注册 + 新校准语料，不得在本 development 语料选优后直接宣称泛化。
- 输出：`outputs/pc.cluster_ablation.v1/`（pc_cluster_ablation.json + PC_CLUSTER_ABLATION_REPORT.md）。
