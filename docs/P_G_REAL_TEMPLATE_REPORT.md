# P-G 交付报告：真实模板族 + LSH 规模 + 真实页泛化修复

> 状态：**G1/G2 完成 · G3 NO_REAL_TEMPLATE_SIGNAL（诚实负面）**。日期：2026-11-23。
> 批准：hqli631 目标预授权「完成 P-G 全周期+reward 接线，批准合理的预算」（G1 补充 ≤20 抓取；G3 ≤30 调用/400k）。
> 前置：P-D2 GENERALIZATION_SIGNAL（3304a30，合成夹具）；P-C 诚实负面（full-counts 过分裂）+ suffix-presence 消融（须独立预注册+新语料验证）。
> **核心诚实结论**：suffix-presence 采纳在既有语料精确复现消融（实现正确），但新真实族召回更弱；LSH 近阈值召回不足（硬检查 FAIL）；**真实页泛化修复回归率 0.4，收益未确立**——P-D2 预言的真实页噪声/过度排除风险兑现。judge 分数 reward 资格仍限受控合成范围。

## 1. 摘要

- **G1 采集**：正式 13 抓取 / 7 接受（apache 3、netbsd 4、**openbsd 0 降级**——security/innovations 抽取 0 块站点私有容器覆盖缺口，类 sqlite；goals 2987 字符略低窗口；index 无标题）。首轮探针 20 抓取/0 接受（诚实负面保留，触发接受标准+重试纪律细化，计划 §9）。
- **G2 聚簇**：22 页（7 新自然 + 2 变体 + 13 既有）。suffix-presence/0.7/CL/MinHash128/LSH16×8。**既有 13 页 pair recall 0.538 / ARI 0.660 精确复现 P-C 消融**（采纳实现正确性确认）；**新族 recall 0.3125 / ARI 0.336**（apache/netbsd 页长结构差异大→过分裂，precision 1.0 无误并）；全 22 页 recall 0.414 / ARI 0.552。**硬检查 FAIL**：LSH 正例召回 new 0.75 / all 0.867（<0.9；16×8 banding 对近阈值 0.7 对候选概率 ~0.62，概率性真实发现，非 bug）；CL 抗链式违规全 0。
- **G3 修复**：5 簇 9 成员（新族），paired n=5 → **improved 1 / regressed 2 / no_effect 2**，改善率 0.2 / 回归率 0.4 → **NO_REAL_TEMPLATE_SIGNAL**。apache var recall 0→1.0 异质簇回灌 accepted（机制在真实变体成立）；netbsd changes/index **回归**（模型 exclude_xpaths 误删 news/sect1 正文→completeness/title fail）；netbsd about/security no_effect（回退已好，冗余触发）；apache howitworks repair_failed（rule_ambiguous 复杂布局）；index-var skipped_budget（守卫近顶停止）。

## 2. 预注册与批准

- 计划 docs/P_G_REAL_TEMPLATE_PLAN.md（sha d046767f…，含 §9 G1 探针细化声明：字符窗口 30k→60k、确定性拒绝/4xx 不重试转下一 URL；聚簇协议未改）。
- G2 冻结 outputs/pg.cluster.freeze.v1.json（dcc76f10…）；G3 冻结 outputs/pg.repair.freeze.v1.json（125160ab…，记录目标批准原文）。
- 协议冻结：suffix-presence/threshold 0.7/CL/MinHash num_perm128 seed20261123/LSH16×8/drift 0.7；judge v1.4.1（25c154b9…，基座 v1.2 edd841ef…）/rubrics v2/rule_agent e60ec309…/rule_cache 1b1c3794…。运行前后校验 CLEAN。
- G3 触发/分类/回灌逐字复用 P-D 冻结；回灌 recall 校验仅对有 silver expected 的变体生效，自然页无 gold 仅结构校验+judge 分类（披露）。

## 3. 复现命令与产物哈希

环境：Windows PowerShell；QWEN_API_KEY 环境变量/env.local（不入库）；PYTHONIOENCODING=utf-8；输出拒覆盖。

```
python -m tools.collect_pg_sources --output outputs/pg.collect.v2.json
python -m tools.build_pg_corpus --collect outputs/pg.collect.v2.json --output samples/pg_corpus.v1.json
python -m tools.run_pg_cluster --freeze --freeze-path outputs/pg.cluster.freeze.v1.json --corpus samples/pg_corpus.v1.json --approval-quote "..."
python -m tools.run_pg_cluster --run --freeze-path outputs/pg.cluster.freeze.v1.json --corpus samples/pg_corpus.v1.json --output outputs/pg.cluster.v1.json
python -m tools.run_pg_repair --freeze --freeze-path outputs/pg.repair.freeze.v1.json --approval-quote "..."
python -m tools.run_pg_repair --run --only pg_netbsd_index-var --freeze-path outputs/pg.repair.freeze.v1.json --output outputs/pg.smoke.v1.json
python -m tools.run_pg_repair --run --freeze-path outputs/pg.repair.freeze.v1.json --output outputs/pg.run.v1.json --token-cap 364352
python -m tools.score_pg --run outputs/pg.run.v1.json --freeze-path outputs/pg.repair.freeze.v1.json --output outputs/pg.score.v1.json
.\run.cmd test   # Ran 755 tests OK (outputs/pg.suite.v3.log)
```

| 产物 | sha256 |
| --- | --- |
| docs/P_G_REAL_TEMPLATE_PLAN.md | d046767f761e3483f5adc8051ee22243cdc3ed71331d94816c8d0f8431e3b7c6 |
| samples/pg_corpus.v1.json | b6c1628fc5adc061cf2f24b1b59f5771f73fcf01f383472b77e2bc25b72989d3 |
| outputs/pg.collect.v2.json | 7bff0c6704b824ce07d3e29c6c40dc9e5779315b5286fcfe31935ba67c0017d6 |
| outputs/pg.cluster.freeze.v1.json | dcc76f10b2d647f80cc547f0bff17ad54fbb75f25cd095682aa7f803402f9848 |
| outputs/pg.cluster.v1.json | 51dd3468c22117fd29bb1ed41a7d1919ca9ba71e0c85393769f785a0318cba50 |
| outputs/pg.repair.freeze.v1.json | 125160aba3d563365695eb6cf42cb73dc2b6f5c751021f1bc891810c04c0e11c |
| outputs/pg.run.v1.json | 29214f0e90bd2a1f889a13ec02c0c02343b4c47117328e6337c5f9a997623d9d |
| outputs/pg.score.v1.json | 76474f1bec17ebba576cd580de772de51448485eefc69b3c99a19d84499bae73 |
| tools/run_pg_repair.py | e6e164f97894b97780ae7b44573e5d0b09bc0deb8af3c4f5674cacc31d17639e |
| tools/score_pg.py | 22f5623f62efc8c8fc37572bb2551083674dd636363c3662970005e5e0afd5ae |

## 4. G3 逐例结果（正式运行）

| 案例 | 簇 | 状态 | 漂移 | 基线 critic | 修复规则 | recall Δ | 分类 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pg_apache_faq | c0 | no_repair_needed | 无 | uncertain/0 | — | — | 对照 |
| pg_apache_howitworks | c0 | **repair_failed** | 无（critic fail/2 触发） | fail/2 | rule_ambiguous 全参考 | — | 复杂布局多容器 |
| pg_apache_howitworks-var | c0 | repaired | rule_failure | fail/4 | //div[contains(@class,'inner inner--default py-xl')] | **0→1.0** | improved（delta 13） |
| pg_apache_license | c1 | no_repair_needed | 无 | uncertain/0 | — | — | 对照 |
| pg_netbsd_about | c2 | repaired | no_shared_rule | uncertain/0 | //div[@id='mainContent'] | — | no_effect（回退已好） |
| pg_netbsd_security | c2 | repaired | no_shared_rule | uncertain/1 | //div[@id='mainContent'] | — | no_effect |
| pg_netbsd_changes | c3 | repaired | no_shared_rule | uncertain/0 | //div[@id='mainContent'] −rowOfBoxes/h1 −sect1 | — | **regressed**（delta −6，completeness+title 新严重） |
| pg_netbsd_index | c4 | repaired | no_shared_rule | uncertain/0 | //div[@id='mainContent'] −//div[@id='news'] | — | **regressed**（delta −3，completeness 新严重） |
| pg_netbsd_index-var | c4 | **skipped_budget** | no_shared_rule | — | — | 0→— | 守卫近顶停止 |

**回灌**：4 次尝试 / 1 次 accepted（c0 apache 异质簇，var 改善+全成员唯一匹配；自然页结构校验、变体 silver recall 校验）；c2/c3/c4 blocked（not_improved，回退已恢复或回归）。
**回归根因**：netbsd 自然页回退已完整（uncertain/0 缺陷），no_shared_rule 漂移仍触发修复；模型为「修复」添加 exclude_xpaths 误删 news/sect1 正文 → v1.4.1 completeness/title 锚点判 fail。**冗余触发 + 过度排除**在真实页放大为回归。

## 5. 预注册判据核对

| 检查 | 阈值 | 实际 | 通过 |
| --- | --- | --- | --- |
| multi_layout_feedback_accepted_ge | ≥1 | 1（c0 apache） | ✓ |
| reuse_recovery_after_feedback_ge | ≥1 | 1 | ✓ |
| improvement_rate_ge | ≥1/3 | 0.2（1/5） | ✗ |
| regression_rate_le | ≤0.10 | 0.4（2/5） | ✗ |
| leakage_audit_all_passed | 全通过 | 全通过 | ✓ |
| unnecessary_repair_zero | =0 | 0 | ✓ |
| candidate_integrity | 无不符 | 无 | ✓ |
| freeze_integrity | 无漂移 | 无 | ✓ |

→ **NO_REAL_TEMPLATE_SIGNAL**（改善/回归两判据未过；描述性信号，非奖励门槛；paired n=5，mean delta CI [−4.2, 7.2] 宽）。
G2 硬检查：CL 违规 0 ✓；LSH 正例召回 new 0.75 / all 0.867 < 0.9 ✗（G2_HARD_CHECKS_FAIL，概率性近阈值发现，不调参）。

## 6. 预算 accounting

| 阶段 | 抓取/调用 | tokens |
| --- | --- | --- |
| G1 探针（细化前） | 20 抓取 / 0 接受 | 0 |
| G1 正式 | 13 抓取 / 7 接受 | 0 |
| G2 建集+聚簇 | 0 | 0 |
| G3 冒烟（netbsd index-var） | 3 调用 | 35,648 |
| G3 正式（5 簇 9 成员） | 23 调用 | 352,255 |
| **G3 合计** | **26 调用**（≤30） | **387,903**（≤400k） |

守卫近顶停止 1 例（index-var skipped_budget，如实部分）；无模型调参。

## 7. 纪律与审计核验

- 封存集未碰（frozen_test v1–v4 未进入）；既有 13 快照字节不变（仅聚簇/复用，无 critic）。
- 协议 sha 运行前后 CLEAN；触发/分类/回灌冻结未改；G2 硬检查 FAIL 不调参、G3 FAIL 不复测。
- critic source_only；silver expected（变体=rep 抽取块）仅编排器侧，永不进 prompt；自然页无 gold；泄漏审计全过。
- 修复 ≤1 干预/成员；全轨迹落盘；拒覆盖；秘密扫描 NONE；755 tests OK。

## 8. 如实局限（关键）

1. **真实页修复收益未确立**：回归率 0.4（过度排除误删正文）；合成夹具的 P-D2 信号**不迁移**到复杂真实页。reward 资格仍限 P-F 受控合成范围，**真实页 judge 奖励未验证**。
2. **触发语义冗余**：no_shared_rule/回退已成功仍触发修复 → 真实页 no_effect/regressed。改进候选（需独立预注册）：回退质量高时抑制修复触发。
3. **聚簇召回弱**：新族 suffix-presence recall 0.31（页长结构差异）；LSH 近阈值召回不足（硬检查 FAIL）。特征/ banding 改进需独立预注册+新语料，不调参。
4. **覆盖缺口**：openbsd（0 块）/sqlite（P-F）站点私有容器未覆盖；apache 复杂布局 rule_ambiguous。
5. 22 页非生产规模；LSH O(n²) 规避收益描述性；簇标签 authored（纯度≠准确率）；自然页无 gold（judge 代理≠准确率）；单标注者背景延续；一致率≠准确率。
6. judge 分数仍**非训练奖励**（reward 接线为后续工程，资格范围受限）。

## 9. 下一步（本目标内）

reward 接线：v1.4.1 合格 judge 分数 → 冻结奖励映射接口 + 离线验证（复用 P-D2/P-G run 工件，零/低调用），**强化披露受控范围资格边界与真实页回归负面**。完成后停止于 P-E（Agentic RL/GRPO 真实训练，gated，不启动）之前。

---

*G1/G2/G3 交付完毕。冻结工件零改写；秘密扫描 NONE；755 tests OK。GitHub：github.com/hqli631/offline_web_extractor main。*
