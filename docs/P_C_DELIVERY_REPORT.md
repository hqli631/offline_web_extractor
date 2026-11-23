# P-C 交付报告：网页聚簇 + 同簇规则复用闭环（零调用）

> 状态：**已交付**。A→E 路线第三步。零模型调用、零网络采集（仅既有本地冻结快照）。
> 核心逻辑：同类布局网页共用一套抽取规则，把（未来）GPU/LLM 推理成本分摊到海量页面。本阶段在本地小语料验证该机制的工程可行性与诚实边界，**不宣称生产规模**（"千亿级"仅业务语境）。
> 预注册计划：`docs/P_C_CLUSTER_PLAN.md`（sha256 `ca3433b00e93d79156c958baa1cf9cd5479afa714a3dad181d08fdbb36ea0681`，含第 8 节 post-hoc 消融追加声明）。

## 1. 冻结参数（预注册，未调参）

threshold=0.7（继承 CLUSTER_ABLATION_PROTOCOL 冻结值）；feature_mode=full-counts（tag-path multiset Jaccard，文本/属性/URL/兄弟索引全排除）；MinHash num_perm=128、seed=20261123；LSH bands=16×rows=8；drift_threshold=0.7；complete-linkage 抗链式聚簇。

## 2. 复现命令与产物哈希

```powershell
# 主运行（预注册口径；v1 为 tool 1.0.0 原始运行，v2 为 1.1.0 复核，corpora 逐字节一致）
python -m tools.run_pc_cluster_loop --output outputs/pc.cluster_loop.v2
# 次要探索性消融（post-hoc，仅特征模式，阈值/链接/seed 全冻结）
python -m tools.run_pc_cluster_loop --output outputs/pc.cluster_ablation.v1 --ablation
# 全套件回归
.\run.cmd test   # Ran 604 tests ... OK（outputs/pc.suite.v1.log）
```

| 文件 | sha256 |
| --- | --- |
| src/webextractor/dom_lsh.py | `16bf7a0a18069f3121204df16446cd2a24de76a738e6825e4ea11afadeac1b70` |
| src/webextractor/dom_cluster.py | `78f0fca32eb75afe8263a8c55c2eb6f06693d7e87c0607d831b9be5b46e7aaa1` |
| src/webextractor/rule_cache.py | `1b1c37945452f7dd32e1fa5769306e2174690ab2df7df74ec5f8f0cbdd6341ba` |
| tools/run_pc_cluster_loop.py (1.1.0) | `fe18ec3f2cc15759a552d1c64d94ffe77a5d4f7ed23e2faed8072c80d857c692` |
| samples/dom_similarity.expanded_development.json | `dbb212a63113aea1…`（real 13 页） |
| samples/dom_similarity.controlled.json | `efe7a25465ecc068…`（synthetic 5 页） |
| outputs/pc.cluster_loop.v2/pc_cluster_loop.json | `4f2c1d06f52a92c04160b1716e757d2ded9e409497523b289b98ae0a4923e44c` |
| outputs/pc.cluster_ablation.v1/pc_cluster_ablation.json | `32062d94d7df6e87…` |

输出目录拒覆盖；运行确定性由测试锚定（两次 run_corpus 全等）。v1→v2 仅 harness 版本变化（新增消融路径与参数化），主路径行为不变（corpora 全等已程序验证）。

## 3. 主结果（预注册 full-counts / 0.7 / complete-linkage）——如实保留弱召回

### 3.1 真实语料（13 页，development）

- 簇：12 个（13 页）。**sphinx-documentation×5 全部单例**；iana-help 分裂为 {iana, iana-abuse} + {iana-whois}。
- 簇纯度：对精度 **1.0**、对召回 **0.0769**（1/13）、ARI **0.122**。
- 抗链式：CL 违规 0。对照连通分量（CC）：CC 把 iana 三页链式并簇（iana-abuse↔iana-whois 相似度 0.638<0.7 仍经由 iana 连通）——CL 正确拆分，**抗链式保证有真实语料反例支撑**。
- LSH：候选 3 / 全对 78；对精确≥0.7 正例召回 **1.0**（固定 seed 实测；概率性保证，非定理）。
- 规则复用：派生 12 次 / 13 页（节省代理 0.077）；应转移成员仅 1（iana-abuse），复用成功 1/1=1.0——**分母极小，比值不具统计意义**；回退 0、漂移 0。
- **诚实结论**：full-counts 多重集 Jaccard 长度敏感，同模板页段落/代码数量差异（README 明示应容忍的同簇内差异）使相似度跌破 0.7，complete-linkage 下过分裂。机制（抗链式/缓存/复用/回退/漂移）全部验证，但**预注册特征模式下聚簇召回差**，不回填、不改参重跑。

### 3.2 合成 controlled（drift_lab×5，与真实分母分离）

- 簇：{class-drift, content-moved, reference, role-drift} + {duplicate-main}。纯度：精度 0.5（content-moved 布局相近被并簇，人工组不同——如实报告）、召回 1.0、ARI 0.444。
- 复用 2/3=0.667；回退 2/5=0.4；漂移标记 2。

| 夹具 | 机制验证 | 结果 |
| --- | --- | --- |
| class-drift | 指纹相同（属性不入指纹）、role 完好 → 共享规则复用 | reuse ok，quality 全 1.0 |
| role-drift | 指纹相似 1.0 但 `//*[@role='main']` 失效 → **规则执行失败触发漂移+回退**（指纹看不见的属性漂移靠第二机制捕获） | drift=[rule_failure]，fallback 触发；**但回退启发式 no_candidate（0 块）**——其候选选择器不覆盖 `role="article"`/`article-shell`。诚实负面：**回退触发≠恢复成功** |
| duplicate-main | 双 role=main → 派生不出唯一规则（no_rule）→ 回退 | 启发式完整恢复，quality 全 1.0 |
| content-moved | 规则 ok、唯一匹配，但正文被移出容器 | reuse=True 而 blocks_exact=False、召回 0.667——**唯一匹配≠正文完整**（quality 指标揭示） |

## 4. 次要探索性消融（post-hoc 追加，非阈值调参）

主运行观察到弱召回后追加（计划第 8 节声明时点）。同一 complete-linkage + 同一闭环，阈值 0.7/num_perm/bands/seed/drift_threshold 全冻结，仅遍历既有 6 种 FEATURE_MODES，仅真实语料：

| 模式 | 簇数 | 对精度 | 对召回 | ARI | 转移复用率 |
| --- | ---: | ---: | ---: | ---: | ---: |
| full-counts（预注册主模式） | 12 | 1.0 | 0.0769 | 0.122 | 1.0 (1/1) |
| full-presence / full-capped / semantic-presence | 11 | 1.0 | 0.1538 | 0.233 | 1.0 |
| suffix-capped / suffix-presence | 8 | 1.0 | **0.5385** | **0.660** | **1.0 (5/5)** |

suffix-presence 细节：iana-help **3/3 跨站家族完整恢复**；sphinx-documentation 5 页聚为 2 个子簇（appetite+library-index；controlflow+interpreter+introduction，仍非 5/5）；python-search 同站负例正确分离；5 个转移成员共享规则全部成功（回退 0、漂移 0）；LSH 候选 7/78、正例召回 1.0；派生 8/13（节省代理 0.385）。

解读：presence/suffix 特征容忍数量差异、聚焦容器路径尾部，召回显著改善；这是**特征选择的可解释影响**。本消融不构成新冻结协议；若采纳某模式须独立预注册 + 新校准语料，不得在本 development 语料选优后直接宣称泛化。

## 5. 验证节点汇总

| 节点 | 验证 | 结果 |
| --- | --- | --- |
| dom_lsh | 确定性签名、banding 候选、召回实测 | 10 测试 OK；两语料正例召回 1.0 |
| dom_cluster | 链式反例（CC 并 {A,B,C}，CL 拆）、簇内全对≥thr 不变式 | 10 测试 OK；真实语料 CL 违规 0 |
| rule_cache | 派生唯一性校验、复用、双机制漂移、回退 | 13 测试 OK；role-drift 关键路径实测 |
| harness 闭环 | 确定性、拒覆盖、指标回归锚、消融路径 | 12 测试 OK |
| 全套件 | `.\run.cmd test` | **Ran 604 tests, OK**（outputs/pc.suite.v1.log；P-B 559 + P-C 45） |

## 6. 局限（诚实边界）

- 小语料：real 13 + synthetic 5，非生产规模；复用率分母极小（主模式 1、suffix 5），比值波动大。
- iana-help 为跨站评估族（同属 development manifest），**非严格独立采集 holdout**；阈值 0.7 继承先前冻结消融，非本周期独立冻结。
- 确定性规则派生器是结构化启发式（4 个候选选择器 + 唯一性 + 文本量门槛），**非 LLM Agent**；真实 Agentic RL/GRPO 属 P-E（gated，需 GPU 与预算审批）。
- 指纹排除属性 → role-drift 类漂移靠规则执行校验捕获（双机制）；**回退触发≠恢复成功**（role-drift 夹具上启发式 no_candidate）。
- 簇纯度≠提取准确率；规则唯一匹配≠正文完整（content-moved 实证）。
- LSH 为概率候选过滤（固定 seed 实测召回 1.0，非定理）；本小语料 definitive 聚簇用精确全对，O(n²) 成本在海量页面才需 LSH 分摊——该规模收益**未实证**。
- 主结果弱召回如实保留；消融为 post-hoc 探索，不构成新冻结协议。

## 7. 与最终目标的差距 / 下一步（不自动启动）

1. **v1.4 评分协议周期**（reward 资格前置）：把 R1 reorder/R2 noise/missing/duplicate 锚定编入 judge prompt + 独立 dev 校准 + 新密封 v4，预注册 + 预算审批后执行。P-B gate FAIL（8/10）未解，judge v1.2 仍 reward-INELIGIBLE。
2. **P-D（gated）**：规则修复闭环与聚簇联动（漂移成员→修复→回灌簇规则），依赖 v1.4 通过后的合格 reward。
3. **P-E（gated）**：Agentic RL/GRPO 真实训练（GPU + 预算审批），以聚簇分摊推理成本为前提。
4. 聚簇协议改进候选（需独立预注册）：suffix/presence 特征正式化、新独立采集校准语料、更大规模 LSH 召回/成本实证、回退启发式覆盖 role=article 等容器。
