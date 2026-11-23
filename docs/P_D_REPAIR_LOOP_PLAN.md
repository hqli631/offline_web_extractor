# P-D 预注册计划：漂移 → 修复 → 回灌簇规则闭环

> 状态：预注册（执行前冻结）。目标授权：hqli631「开始P-D…批准合理的计划+预算，直至P-D基本完成」。
> 前置：P-F gate PASS（commit 20cddf1）→ judge v1.4.1 在受控范围内 reward 资格成立。本实验把合格 critic 接入簇修复闭环，**仍不产生训练奖励**（reward 接线属后续独立工作）。

## 1. 目标与范围

把 P-C 的「漂移→回退」升级为「漂移→critic 引导修复→回灌簇规则→复用」闭环，并在**退化候选**上检验修复能力（补 node5 NO_BENEFIT 的缺口：node5 dev 基线质量已高、可修复空间极小）。核心逻辑：同簇网页共用抽取规则，修复后的规则回灌簇缓存以摊薄推理成本。

**范围边界**：受控合成 drift_lab 语料（机制验证，非真实站点泛化）；小规模；描述性收益信号，非奖励门槛。

## 2. 复用构件（零改写冻结件）

- P-C：`rule_cache.ClusterRuleCache`（派生/复用/双机制漂移/回退）、`dom_similarity.structural_features`。
- node5：`critic_feedback`、`CriticGuidedProvider`、`audit_repair_prompt`（结构泄漏审计）、`BudgetGuard`、`baseline_preview`。
- 修复执行器：`rule_agent.run_agent`（reference-only，禁 expected/test，XPath 输出，可信执行，max_attempts=2 即 ≤1 次修复干预）。
- critic/rejudge：`rubrics_judge_v141.run_judge`（**source_only**，gold=None）。
- 评分：`score_node5.classify_pair`（冻结分类）+ `bootstrap_stats.bootstrap_ci`。

## 3. 语料与簇

`samples/dom_similarity.controlled.json`（5 页合成夹具，drift_lab）。簇 = manual_group（受控设计族）：
- reference-layout：rep=reference；members=class-drift, role-drift。
- duplicate-main：单页（对照，回退已恢复）。
- content-moved：单页（诚实负面：unique match≠正文完整，容器选择不可修复）。

零调用探针（outputs/_pd_probe.py，执行前）确认：role-drift 共享规则 rule_no_match + 回退 no_candidate（recall 0），`//*[@role='article']` 修复后 recall 1.0（可修复）；content-moved recall 0.667 容器外正文（不可修复）；duplicate-main 回退 recall 1.0。

## 4. 闭环设计（每簇）

1. derive_and_cache(rep) → 共享规则。
2. 每 member：reuse_member → 漂移检测（fingerprint_drift / rule_failure）。
3. critic v1.4.1 source_only 评估 reuse/fallback 抽取（基线臂）。
4. 触发修复 iff 漂移 OR critic decision==fail OR 缺陷非空。
5. 修复：rule_agent（reference_pages=[member 源]，critic_feedback+baseline_preview 注入，泄漏审计）→ 修复规则 → 在 member 上可信执行 → 修复候选。
6. rejudge v1.4.1 source_only → classify_pair（基线 vs 修复）。
7. **回灌**：修复规则若改善且在 rep+全部 members 上通过校验（唯一匹配+ok+非空+程序质量不降）→ 回灌为簇共享规则；否则记为逐页修复 + feedback_blocked 原因（如实）。另存 member 级修复规则缓存（member 自身复用摊薄）。
8. 回灌后重复用 members → 度量复用恢复/节省。
9. 程序侧核（recall/precision vs expected，post-hoc 仅报告不回传）。

## 5. 触发语义（冻结）

repair iff (drift_reasons 非空) OR (critic decision==fail) OR (defects 非空：severity∈{minor,major,critical} 或已评分 score<4)。source_only decision 永不为 pass；零缺陷 uncertain 且无漂移 → no_repair_needed。

## 6. 分类（逐字节复用 node5 冻结分类）

improved / regressed / no_effect / other_change；regressed 优先（保守）；total_score=非空维度分和；paired n=修复且 rejudge accepted 的案例。

## 7. 回灌规则（冻结）

feedback_accepted iff 修复改善 AND 修复规则在 rep 与每个 member 上 apply_rule 唯一匹配+status ok+block_count>0 AND 程序 block_text_recall 不低于该 member 修复前。否则 feedback_blocked（记录原因：rule_no_match/ambiguous/quality_drop 等），保留逐页修复。

## 8. 预注册判据（描述性信号，非奖励门槛）

- improvement_rate_ge ≥ 1/3（paired n）
- regression_rate_le ≤ 0.10
- leakage_audit_all_passed = True
- unnecessary_repair_zero = 0
- candidate_integrity 无哈希不符
- drift_recovery：role-drift 程序 recall 0→1.0（机制验证）
- verdict_labels：REPAIR_BENEFIT_SIGNAL / NO_BENEFIT_SIGNAL（n 小，CI 宽，如实降级）

## 9. 预算（合理上限，预注册）

token_cap=300000；调用上限 25；reserve_judge=16000，reserve_rule=8000。估算：5 基线 critic + ≤6 修复生成（max_attempts=2×3 触发）+ ≤3 rejudge + ≤2 回灌重复用 critic + 1 冒烟 ≈ ≤17 调用。合成小页（~500-800 字节）单次 token 低。守卫在超顶前停止；可能跳过案例 → 如实部分报告。

## 10. 纪律与局限

- 协议冻结：v1.4.1 模块 sha 25c154b9… / 基座 v1.2 edd841ef… / rubrics v2.0.0 / rule_agent sha；运行前后校验。
- test/gold 不回传：critic source_only；修复 prompt 白名单+禁词递归审计；基线预览来自 reuse/fallback 抽取而非 expected。
- 修复 ≤1 干预；不追加调参刷分；负结果如实交付。
- 局限：合成小语料（5 页）非泛化；paired n 小 CI 宽；簇纯度≠准确率；judge 判改善≠真实改善；回灌受布局异质性限制（修复规则可能仅成员特异）；单标注者背景延续；judge 分数仍非训练奖励。

## 11. 复现命令

```
python -m tools.run_pd_repair_loop --freeze
python -m tools.run_pd_repair_loop --run --max-cases 1 --output outputs/pd.smoke.v1.json
python -m tools.run_pd_repair_loop --run --output outputs/pd.run.v1.json --token-cap <cap-smoke>
python -m tools.score_pd --run outputs/pd.run.v1.json --output outputs/pd.score.v1.json
.\run.cmd test
```

## 12. 工程细化声明（post-smoke，协议/判据未改）

冒烟（pd.freeze.v1，仅评估 members）验证 role-drift 修复端到端可行（recall 0→1.0，回灌因成员特异规则被阻）后，做一处工程细化：**把 representative 自身也纳入评估成员**（rep 复用自身派生规则），使单页族 content-moved（unique match≠完整的诚实负面）与 duplicate-main（回退恢复）也被闭环覆盖。簇成员由「除 rep 外」改为「含 rep 的全部页」；validate_feedback/pre_recall 对 rep+members 去重。

- 此细化**不改**协议（v1.4.1 sha 25c154b9）、触发语义、冻结分类、回灌规则、判据、预算上限。
- pd.freeze.v1 为冒烟冻结（member-only clusters，已被 v2 取代）；**pd.freeze.v2 为正式运行冻结**（rep-inclusive clusters，pin 本更新后计划 sha）。
- 冒烟与正式运行各自独立留痕；正式运行是预注册实验主体。
