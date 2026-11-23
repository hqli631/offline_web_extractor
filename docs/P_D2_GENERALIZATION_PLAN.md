# P-D2 预注册计划：异质簇共享规则泛化

> 状态：预注册（执行前冻结）。前置：P-D REPAIR_BENEFIT_SIGNAL（commit 6d61761）；P-D 诚实负面：成员特异修复规则不泛化到布局不同的多页簇（feedback blocked）。本实验检验「泛化修复 → 跨布局共享规则 → 回灌复用摊薄」。judge 分数仍非训练奖励。

## 1. 目标与范围

把修复从「成员特异」升级为「簇级泛化」：修复时把全簇成员源（≤8 页）作为参考注入，要求一条共享规则（自然形态：union XPath）在所有参考页上可执行；回灌校验通过后后续成员直接复用，把修复推理成本摊薄到簇。
范围：受控合成 drift_lab v2（7 页），机制验证非真实站点泛化；描述性信号非奖励门槛。

## 2. 语料 v2（新文件，旧夹具零改写）

`samples/dom_similarity.controlled.v2.json` = 原 5 页（字节不变）+ 2 个新布局：
- **id-drift**：`div id="article-body"`（无 role；回退 no_candidate，recall 0；标签路径与 reference 一致 → rule_failure 漂移）
- **section-drift**：`<section class="article-shell-v4">`（回退 no_candidate，recall 0；标签路径变化 → 指纹/规则漂移）

reference-layout 簇扩为 5 成员（4 个不同布局）；duplicate-main / content-moved 单页对照保留。
新夹具 builder `build_fixtures_v2.py`：expected 由固定句手写（非 extractor 产出）；拒绝覆盖已变更文件。
布局标签（authored）：role-main-div / role-article-div / id-article-body-div / section-v4。**multi_layout 簇 = ≥2 个不同布局**。

## 3. 复用构件（零改写冻结件）

rule_cache（derive/apply/fallback/双机制漂移）、rule_agent.run_agent（1–8 参考页；运行时接受=全参考页非空；max_attempts=2 即 ≤1 干预）、node5 critic_feedback / CriticGuidedProvider / audit_repair_prompt / BudgetGuard / baseline_preview、rubrics_judge_v141 source_only、score_node5.classify_pair、bootstrap_stats。
P-D 工具/报告/冻结零改写；P-D2 为新工具 `run_pd2_generalize.py` / `score_pd2.py`。

## 4. 闭环设计（每簇，内联回灌）

1. derive_and_cache(rep) → v0 共享规则。
2. 成员按字典序：reuse（§5 语义）→ v1.4.1 source_only 基线 critic → 触发（§6）。
3. **泛化修复**：run_agent(reference_pages=全簇页源, critic_feedback+baseline_preview 注入, 泄漏审计)。参考含其他成员源（合法参考材料，source only，无 expected）。
4. 可信执行 → rejudge → classify_pair。
5. **内联回灌**：校验规则同 P-D 冻结（§7）；accepted → 更新簇共享规则并标记 generalized_validated；后续成员复用新规则（摊薄可见）；blocked → 保留 member 级规则缓存，记录原因。
6. 回灌后复用恢复 + 程序侧核（post-hoc 仅报告）。
摊薄度量：修复生成调用数 / 恢复成员数；对照 P-D 逐成员修复。

## 5. 泛化规则复用新语义（冻结）

对已回灌校验的 generalized_validated 规则：**仅 fingerprint_drift 不再使规则失效**（布局异质是泛化规则的设计目标）；规则执行 ok 且非空 → reuse（记 generalized_override=True 供审计）。rule_failure 仍触发漂移+回退。未校验的 v0 规则保持 P-C 原语义。

## 6. 触发语义（逐字复用 P-D 冻结）

repair iff drift_reasons 非空 OR critic decision==fail OR defects 非空（severity minor/major/critical 或已评分 score<4）。source_only 永不为 pass；零缺陷 uncertain 且无漂移 → no_repair_needed。

## 7. 回灌规则（逐字复用 P-D 冻结）

feedback_accepted iff 程序改善 AND 规则在 rep+全部 members 上 apply_rule 唯一匹配+ok+block_count>0 AND block_text_recall 不低于修复前。校验使用 dev expected（编排器侧，永不进 prompt；如实披露）。

## 8. 预注册判据（描述性信号，非奖励门槛）

- **multi_layout_feedback_accepted ≥ 1**（主新增判据）
- **reuse_recovery_after_feedback ≥ 2**（v0 复用失败 → 回灌后复用 ok）
- improvement_rate ≥ 1/3（paired n）；regression_rate ≤ 0.10
- leakage_audit_all_passed；unnecessary_repair_zero = 0；candidate/freeze integrity 无不符
- verdict：**GENERALIZATION_SIGNAL / NO_GENERALIZATION_SIGNAL**（n 小 CI 宽，如实降级）

## 9. 预算（待批准）

token_cap=200000；调用上限 20；reserve_judge=16000，reserve_rule=8000。
估算：冒烟 3（id-drift：critic+gen+rejudge）+ 正式 ≤13（7 critic + ≤3 gen + ≤3 rejudge）≈ ≤16 调用 / ~50k tokens。合成小页单次 token 低。守卫超顶前停止；跳过如实部分报告。零网络。模型 qwen3.8-27b。

## 10. 纪律与局限

协议 sha 冻结（v1.4.1 / 基座 v1.2 / rubrics v2 / rule_agent / rule_cache）；运行前后校验。
test/gold 不回传；critic source_only；prompt 白名单+禁词递归审计；修复 ≤1 干预/成员；不追加调参刷分；负结果如实交付。
局限：合成 7 页非泛化；union XPath 在真实复杂页的噪声风险未证；簇/布局标签 authored（纯度≠准确率）；judge 判改善≠真实改善；单标注者背景延续；judge 分数非训练奖励；回灌校验使用 dev expected（编排器侧，不进 prompt）。

## 11. 复现命令

```
python -m tools.run_pd2_generalize --freeze --freeze-path outputs/pd2.freeze.v1.json
python -m tools.run_pd2_generalize --run --only id-drift --output outputs/pd2.smoke.v1.json
python -m tools.run_pd2_generalize --run --freeze-path outputs/pd2.freeze.v1.json --output outputs/pd2.run.v1.json --token-cap <cap-smoke>
python -m tools.score_pd2 --run outputs/pd2.run.v1.json --freeze-path outputs/pd2.freeze.v1.json --output outputs/pd2.score.v1.json
.\run.cmd test
```
