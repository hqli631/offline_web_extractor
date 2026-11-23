# P-D2 交付报告：异质簇共享规则泛化

> 状态：**基本完成 · GENERALIZATION_SIGNAL（8/8 预注册判据通过）**。受控合成语料机制验证，非真实站点泛化。
> 日期：2026-11-23 · 批准：hqli631「批准 P-D2 预算 20/200k」。
> 前置：P-D REPAIR_BENEFIT_SIGNAL（6d61761）及其诚实负面——成员特异修复规则不泛化到布局不同的多页簇（feedback blocked）。本实验解决该缺口：**跨异质多页簇的共享规则回灌首次成功**。judge 分数仍非训练奖励。

## 1. 摘要

把 P-D「成员特异修复」升级为「簇级泛化修复 + 内联回灌」：修复器看到全簇成员源（≤8 参考页），必须产出一条在所有参考页可执行的共享规则；回灌校验通过后立即更新簇共享规则，后续成员直接复用。

- 7 页受控 drift_lab v2（原 5 页字节不变 + 2 个新手写布局）；reference-layout 簇 5 成员 / 4 布局。
- **异质簇回灌成功**（P-D blocked 路径解决）：id-drift 触发泛化修复 → union 规则 `//div[contains(@class,'article-shell')] | //section[contains(@class,'article-shell')]` → 全 5 成员唯一匹配 recall 1.0 → **feedback accepted（multi_layout=1）**。
- **摊薄可见**：回灌后 role-drift / section-drift / reference 直接复用，`no_repair_needed`；该簇 2 次修复生成调用恢复 3 个成员（0.667 调用/恢复成员）。
- **新复用语义实战触发**：section-drift 指纹相似度 0.286（<0.7）但已校验泛化规则执行 ok → `generalized_override=True` 复用成功（P-C 原语义下会误回退）。
- paired n=3：**improved 2 / regressed 0 / no_effect 1**，improvement_rate 0.667；recall：id-drift 0→1.0，content-moved 0.667→1.0。
- 预算：**18 调用 / 45,622 tokens**（硬顶 20 / 200k）；无跳过。

## 2. 预注册与批准

- 计划：docs/P_D2_GENERALIZATION_PLAN.md（sha 4e65e604…，执行前冻结；零调用工程里程碑 ca2b305 先行交付）。
- 冻结：outputs/pd2.freeze.v1.json（sha 9536b513…，记录批准原文；check_freeze CLEAN，运行前后一致）。
- 协议冻结（逐字节沿用 P-D）：judge v1.4.1 模块 sha 25c154b9…（基座 v1.2 edd841ef…）；rubrics v2.0.0；rule_agent e60ec309…；rule_cache 1b1c3794…；模型 qwen3.8-27b；critic source_only。
- 触发/分类/回灌规则逐字复用 P-D 冻结；新增泛化修复参考语义与泛化复用语义（计划 §4/§5，执行前冻结）。
- P-D 冻结链复验 CLEAN：原 5 夹具、P-D 工具/报告/冻结哈希全部与 P-D 报告一致，零改写。

## 3. 复现命令与产物哈希

环境：Windows PowerShell；QWEN_API_KEY 环境变量/env.local（不入库）；PYTHONIOENCODING=utf-8；python 经运行时路径；输出拒覆盖。

```
python -m tools.run_pd2_generalize --freeze --freeze-path outputs/pd2.freeze.v1.json --approval-quote "批准 P-D2 预算 20/200k (hqli631, 2026-11-23)"
python -m tools.run_pd2_generalize --run --only id-drift --freeze-path outputs/pd2.freeze.v1.json --output outputs/pd2.smoke.v1.json
python -m tools.run_pd2_generalize --run --freeze-path outputs/pd2.freeze.v1.json --output outputs/pd2.run.v1.json --token-cap 190294
python -m tools.score_pd2 --run outputs/pd2.run.v1.json --freeze-path outputs/pd2.freeze.v1.json --output outputs/pd2.score.v1.json
.\run.cmd test
```

| 产物 | sha256 |
| --- | --- |
| docs/P_D2_GENERALIZATION_PLAN.md | 4e65e604994f893845fef0350295fc19551102fd9925f2f2f59c89c2ba1ac3aa |
| samples/dom_similarity.controlled.v2.json | 03c93d5d9e8a1f251838a3d9a66e0f88495a0920663c2802dd178bc1da2b6069 |
| outputs/pd2.freeze.v1.json | 9536b5137b78bdb9d85e4a6918897fecae8825a64982a48e72682da0936ba644 |
| outputs/pd2.smoke.v1.json | e09cfd5e0e37d95ae206846a6de2db87a26e528b769458680d9146fc89e7cf84 |
| outputs/pd2.run.v1.json | 44e7ef47e6991e9f5d4fe86197ba46bce0e80f59008ed979da7cc79ea06508b8 |
| outputs/pd2.score.v1.json | 7b73c73bd07691cb9a00d146750d766b6ed3b8e83dc98e78121f64b44894e953 |
| tools/run_pd2_generalize.py | c27c044ce214c7497487d2dd935466e0276c4a797b06451174ae6ec92987f084 |
| tools/score_pd2.py | 26d930404f07d031958f17b27ed3fbeb134a9e9cf46daade57b580e8e567465a |
| tests/test_pd2_generalize.py | 096cc75a9b9d5be48d6abba3046298bc3a177e8e91e56ec59d31b5dcd1c9d55e |

## 4. 闭环设计（每簇，内联回灌）

derive_and_cache(rep) → v0 复用快照（零调用）→ 成员按字典序：reuse（泛化规则 override 语义）→ v1.4.1 source_only 基线 critic → 触发（P-D 冻结语义）→ **泛化修复** run_agent(reference_pages=全簇源, critic_feedback+baseline_preview 注入, 泄漏审计, max_attempts=2) → 可信执行（按成员 id 取结果）→ rejudge → classify_pair → **内联回灌校验**（改善 + rep+全簇唯一匹配+ok+非空+recall 不降）→ accepted 立即更新共享规则并标记 generalized_validated，后续成员复用；blocked 保留 member 级规则缓存 → 终态复用快照 + 恢复/摊薄度量 + 程序侧核（post-hoc）。

## 5. 逐例结果（正式运行）

| 案例 | 状态 | 漂移 | 基线 critic | 修复规则 | recall Δ | 分类 |
| --- | --- | --- | --- | --- | --- | --- |
| class-drift | no_repair_needed | 无 | uncertain/0 缺陷 | — | — | 对照 |
| **id-drift** | repaired | rule_failure | fail/3 缺陷 | union（div+section, contains article-shell） | **0→1.0** | improved（delta 12） |
| reference | no_repair_needed | 无 | uncertain/0 缺陷 | —（复用回灌规则） | — | 对照 |
| role-drift | no_repair_needed | 无（回灌后复用 ok） | uncertain/0 缺陷 | —（复用回灌规则） | 1.0（v0 为 0） | 恢复 |
| section-drift | no_repair_needed | **override**（sim 0.286） | uncertain/0 缺陷 | —（复用回灌规则） | 1.0（v0 为 0） | 恢复 |
| duplicate-main | repaired | no_shared_rule | uncertain/0 缺陷 | //div[@role='main'][contains(@class,'desktop-layout')] | 1.0→1.0 | no_effect（冗余触发，如实） |
| content-moved | repaired | 无（critic fail 触发） | fail/1 缺陷（missing-body 锚点） | //body −nav/footer | 0.667→1.0 | improved（delta 2） |

**泛化修复过程（id-drift，冒烟与正式一致机制）**：attempt 1 规则覆盖 div 布局但 section-drift rule_no_match → 运行时反馈驱动 attempt 2 产出跨标签 union 规则，全 5 参考页 ok（两次 finish_reason=stop）。这是 rule_agent 多参考页运行时接受约束的真实泛化压力，非提示词空谈。

**回灌**：3 次尝试 / 2 次 accepted：
- **reference-layout（异质 4 布局）：accepted** —— P-D blocked 路径解决；全 5 成员唯一匹配 recall 1.0；恢复 id-drift/role-drift/section-drift；2 生成调用/3 恢复 = 0.667。
- content-moved（单页）：accepted（平凡泛化，multi_layout=False，**不计入主判据**）。
- duplicate-main：blocked（not_improved，回退已恢复）。

## 6. 预注册判据核对（8/8）

| 检查 | 阈值 | 实际 | 通过 |
| --- | --- | --- | --- |
| multi_layout_feedback_accepted_ge | ≥1 | **1**（reference-layout） | ✓ |
| reuse_recovery_after_feedback_ge | ≥2 | **3** | ✓ |
| improvement_rate_ge | ≥1/3 | 0.667（2/3） | ✓ |
| regression_rate_le | ≤0.10 | 0.0 | ✓ |
| leakage_audit_all_passed | 全通过 | 6/6 prompts | ✓ |
| unnecessary_repair_zero | =0 | 0 | ✓ |
| candidate_integrity | 无不符 | 无 | ✓ |
| freeze_integrity | 无漂移 | 无 | ✓ |

→ **GENERALIZATION_SIGNAL**（描述性信号，非奖励门槛；paired n=3，mean delta CI [0,12] 宽，如实降级）。

## 7. 预算 accounting（硬顶 20 调用 / 200k）

| 阶段 | 调用 | tokens |
| --- | --- | --- |
| 冒烟（id-drift：critic+2 生成+rejudge） | 4 | 9,706 |
| 正式（7 critic + 4 生成 + 3 rejudge） | 14 | 35,916 |
| **合计** | **18** | **45,622** |

无跳过；双守卫（token+调用数）未触发。

## 8. 纪律与审计核验

- **封存集未碰**：仅受控 drift_lab v2；frozen_test v1/v2/v3/v4 均未进入；原 5 夹具字节不变（测试断言）。
- **协议未改**：v1.4.1/rule_agent/rule_cache/rubrics sha 运行前后一致；P-D 冻结链复验 CLEAN。
- **test/gold 不回传**：critic 强制 source_only；修复 prompt 白名单+禁词递归审计 6/6 通过；参考页仅源 HTML；回灌校验用 dev expected 仅在编排器侧（计划披露）。
- **修复 ≤1 干预/成员**：max_attempts=2；id-drift 2 次生成（运行时反馈修复），其余各 1 次。
- **不追加调参刷分**：冻结后单次正式运行；duplicate-main no_effect 如实交付。
- **全轨迹落盘**：prompts/哈希/usage/attempts/审计/回灌校验/override 事件均在 run json；拒覆盖。
- **测试**：18 项 P-D2 测试；全量 **733 tests OK**（outputs/pd2.suite.v1.log；最终里程碑复跑见 pd2.suite.v2.log）。

## 9. 如实局限

1. 合成 7 页、paired n=3、CI [0,12]：**描述性信号，非统计证明，非真实站点泛化**。
2. 模型发现的 union 规则依赖 `contains(@class,'article-shell')` 子串匹配——夹具内合法，但真实复杂页可能过度匹配噪声容器；**噪声风险未证**。
3. 簇/布局标签 authored（manual_group）；真实 LSH 聚簇的纯度与异质簇边界未实证（P-C 完整计数弱召回局限延续）。
4. duplicate-main 冗余触发延续 P-D 诚实负面（回退已成功仍触发修复，no_effect）。
5. judge 判改善≠真实改善（程序 recall 佐证一致，但程序诊断未校准）；一致率≠准确率；单标注者背景延续。
6. 摊薄度量仅计修复生成调用；critic/rejudge 成本未摊薄（每成员仍各 1 次基线 critic）；海量页面规模收益未实证。
7. judge 分数仍**非训练奖励**（reward 接线属后续独立工程）。

## 10. 与最终目标的差距 / 下一步（不自动启动）

P-D2 解决了 P-D 的核心缺口：**异质簇共享规则回灌成功 + 复用恢复 + 摊薄信号**。「同类布局共用抽取代码、修复成本摊薄到簇」的机制在受控语料上闭环成立。剩余：

1. **P-G：真实模板族 + 规模**——真实站点漂移修复、LSH 聚簇质量、海量页面摊薄收益（需新采集网络预算 + 模型预算，独立审批）。
2. **reward 接线**——v1.4.1 受控范围 reward 资格已成立（P-F），judge 分数接入训练奖励为独立工程。
3. **P-E（gated）**——Agentic RL / GRPO 真实训练（GPU + 预算审批）；目前仅 toy_rl/dom_rl 脚手架。
4. 抽取器 lua/sqlite 站点私有容器覆盖缺口（P-F 披露）延续。

---

*本报告交付后 P-D2 基本完成。P-G / P-E 不自动启动。冻结工件零改写；秘密扫描 NONE；全量 733 tests OK。GitHub：github.com/hqli631/offline_web_extractor main。*
