# P-D 交付报告：漂移 → 修复 → 回灌簇规则闭环

> 状态：**基本完成 · REPAIR_BENEFIT_SIGNAL（7/7 预注册判据通过）**。受控合成语料机制验证，非真实站点泛化。
> 日期：2026-11-23 · 批准：hqli631 目标授权「开始P-D…批准合理的计划+预算，直至P-D基本完成」。
> 前置：P-F gate PASS（20cddf1）→ v1.4.1 受控范围 reward 资格。本实验把合格 critic 接入簇修复闭环；**judge 分数仍非训练奖励**（reward 接线属后续独立工作）。

## 1. 摘要

把 P-C「漂移→回退」升级为「漂移→v1.4.1 critic 引导修复→回灌簇规则→复用」闭环，并在**退化候选**上检验修复能力（补 node5 NO_BENEFIT 缺口：node5 dev 基线质量已高、可修复空间极小）。

- 5 页受控 drift_lab：2 对照不修复；3 触发修复，paired n=3 → **improved 2 / regressed 0 / no_effect 1**，improvement_rate **0.667**（≥1/3）。
- **role-drift**：共享规则 rule_no_match + 回退 no_candidate（recall 0）→ critic fail → 修复 `//div[@role='article']` → **recall 0→1.0**，decision fail→uncertain（improved）。
- **content-moved**：unique match 但 recall 0.667（正文移出容器）→ v1.4.1 missing-body 锚点判 fail → 修复 `//body`（排除 nav/footer）→ **recall 0.667→1.0**（improved）。意外正面：宽容器+排除可修复「容器外正文」。
- **duplicate-main**：no_shared_rule 漂移触发，但回退已 recall 1.0、critic 0 缺陷 → 修复 no_effect（如实冗余）。
- **回灌**：3 次尝试，1 次 accepted（content-moved 单页簇）；reference-layout 多页簇 **blocked**（成员特异规则不泛化到 reference）；duplicate-main blocked（not_improved）。
- 预算：冒烟 6,625 + 正式 26,883 = **33,508 tokens**（硬顶 300k，远低于）；无跳过。

## 2. 预注册与批准

- 计划：docs/P_D_REPAIR_LOOP_PLAN.md（sha f3c52495…，含 §12 post-smoke 工程细化声明）。
- 冻结 v1（冒烟，member-only clusters）sha e1e85062… → **v2（正式，rep-inclusive clusters）sha ec311e82…**。细化仅把 rep 纳入评估成员，**协议/触发/分类/回灌/判据/预算未改**。
- 协议冻结：judge v1.4.1 模块 sha 25c154b9…（基座 v1.2 edd841ef…）；rubrics v2.0.0；rule_agent sha e60ec309…；rule_cache sha 1b1c3794…；模型 qwen3.8-27b；critic source_only。
- 触发：drift_reasons 非空 OR critic fail OR 缺陷非空。分类逐字节复用 node5 冻结 classify_pair。回灌：改善 AND 规则在 rep+全 members 唯一匹配+ok+非空+recall 不降。

## 3. 复现命令与产物哈希

环境：Windows PowerShell；QWEN_API_KEY 环境变量/env.local（不入库）；PYTHONIOENCODING=utf-8；python 经运行时路径；输出拒覆盖。

```
python -m tools.run_pd_repair_loop --freeze --freeze-path outputs/pd.freeze.v2.json
python -m tools.run_pd_repair_loop --run --only role-drift --output outputs/pd.smoke.v1.json
python -m tools.run_pd_repair_loop --run --freeze-path outputs/pd.freeze.v2.json --output outputs/pd.run.v1.json --token-cap 293375
python -m tools.score_pd --run outputs/pd.run.v1.json --freeze-path outputs/pd.freeze.v2.json --output outputs/pd.score.v1.json
.\run.cmd test   # Ran 715 tests OK (outputs/pd.suite.v1.log)
```

| 产物 | sha256 |
| --- | --- |
| docs/P_D_REPAIR_LOOP_PLAN.md | f3c524956ee87cf7f0ec3fd7fdae8e740bb43fde8fa702f15b2fc412a068f60d |
| outputs/pd.freeze.v2.json | ec311e8238a93e69ec453050984530efab3db177eda1189b3cfb646122f6a658 |
| outputs/pd.smoke.v1.json | 502995137860b30bfa28dd88c01665af6c7f08cbfc6363e0bb391dbfd79fddbc |
| outputs/pd.run.v1.json | fd2db20417acb57f01958c24a4660cb1e257ad25938f9755c3dafc3e546f5884 |
| outputs/pd.score.v1.json | 65b7ca0f88f1a6ab3648692b414fbe22869d5fa05c5b687aaafa7d9e492c7a3c |
| tools/run_pd_repair_loop.py | 375ba52f77f8f02e6f8d2fba99d474b24f8298f0060af685af4e55d09b2d1512 |
| tools/score_pd.py | fbcbc0a42a381deeebb2572134746186f35e1080851bd3256bb686321758019e |

## 4. 闭环设计（每簇）

derive_and_cache(rep) → 每 member（含 rep）reuse_member（双机制漂移：fingerprint + rule_failure）→ v1.4.1 source_only critic 基线 → 触发修复 → rule_agent（reference_pages=[member 源]，critic_feedback+baseline_preview 注入，结构泄漏审计，max_attempts=2 即 ≤1 干预）→ 修复规则可信执行 → rejudge → classify_pair → 回灌校验（改善+泛化）→ accepted 则回灌簇共享规则并重复用 / blocked 则保留 member 级规则缓存 → 程序侧核（post-hoc）。

## 5. 逐例结果（正式运行）

| 案例 | 状态 | 漂移 | 基线 critic | 修复规则 | recall Δ | 分类 |
| --- | --- | --- | --- | --- | --- | --- |
| reference | no_repair_needed | 无 | uncertain/0 缺陷 | — | — | 对照 |
| class-drift | no_repair_needed | 无（属性不入指纹） | uncertain/0 缺陷 | — | — | 对照 |
| role-drift | repaired | rule_failure | fail/3 缺陷 | `//div[@role='article']` | 0→1.0 | **improved** |
| content-moved | repaired | 无（unique match） | fail/1 缺陷（missing） | `//body` − nav/footer | 0.667→1.0 | **improved** |
| duplicate-main | repaired | no_shared_rule | uncertain/0 缺陷 | `//div[@role='main' and @class='desktop-layout']` | 0 | no_effect |

paired n=3：improved 2、regressed 0、no_effect 1；mean_total_score_delta_ci95 point 4.67，ci95 [0.0, 12.0]（n=3，B=10000，seed=20261119，**宽区间，无强推断力**）。

## 6. 回灌结果（诚实边界）

| 簇 | 尝试 | accepted | 原因 |
| --- | --- | --- | --- |
| reference-layout（多页） | 是 | **否** | role-drift 修复规则 `//div[@role='article']` 在 reference（role=main）rule_no_match → **rule_does_not_generalize** |
| duplicate-main（单页） | 是 | 否 | not_improved（no_effect） |
| content-moved（单页） | 是 | **是** | `//body`−nav/footer 改善且（单页簇）泛化平凡成立 |

**关键诚实结论**：闭环机制完整且正确（accepted/blocked 两路径均验证）；但**跨异质多页簇的共享规则回灌未成功**——成员特异修复规则不泛化到布局不同的同簇成员。feedback_accepted=1 来自单页簇（平凡泛化），不构成「异质簇共享规则修复复用」的证据。member 级规则缓存仍摊薄成员自身重复抽取。content-moved 的 `//body` 宽容器在小夹具可行，复杂真实页噪声风险未证。

## 7. 预注册判据核对（7/7）

| 检查 | 阈值 | 实际 | 通过 |
| --- | --- | --- | --- |
| improvement_rate_ge | ≥1/3 | 0.667（2/3） | ✓ |
| regression_rate_le | ≤0.10 | 0.0 | ✓ |
| leakage_audit_all_passed | 全通过 | 5/5 | ✓ |
| unnecessary_repair_zero | =0 | 0 | ✓ |
| candidate_integrity | 无不符 | 无 | ✓ |
| freeze_integrity | 无漂移 | 无 | ✓ |
| drift_recovery（role-drift） | recall 0→1.0 | 0→1.0 | ✓ |

→ **REPAIR_BENEFIT_SIGNAL**（描述性信号，非奖励门槛；n 小如实降级）。

## 8. 预算 accounting（硬顶 300k / ≤25 调用）

| 阶段 | 调用 | tokens |
| --- | --- | --- |
| 冒烟（role-drift：critic+生成+rejudge） | 3 | 6,625 |
| 正式（5 页：5 critic + 3 生成 + 3 rejudge） | 11 | 26,883 |
| **合计** | **14** | **33,508** |

无跳过；守卫未触发。合成小页（~500-800 字节）单次 token 低。

## 9. 纪律与审计核验

- **封存集未碰**：仅受控 drift_lab 5 页（freeze 源哈希校验）；frozen_test v1/v2/v3/v4 均未进入。
- **协议未改**：v1.4.1/rule_agent/rule_cache sha 运行前后一致（check_freeze）；锚点/阈值/分类未动。
- **test/gold 不回传**：critic 强制 source_only（gold=None）；修复 prompt 白名单+禁词递归审计 5/5 通过；基线预览来自 reuse/fallback 抽取而非 expected；程序侧核 post-hoc 仅报告。
- **修复 ≤1 干预**：rule_agent max_attempts=2；3 案各 1 次生成即 runtime_accepted。
- **不追加调参刷分**：冻结后单次正式运行；负结果（duplicate-main no_effect、多页簇回灌 blocked）如实交付。
- **全轨迹落盘**：prompts/哈希/usage/attempts/审计/回灌校验均在 run json；拒覆盖。
- **测试**：新增 13 项 P-D 测试（纯函数+mock 编排+评分器+CLI），全量 **715 tests OK**（outputs/pd.suite.v1.log）。

## 10. 如实局限

1. 合成小语料（5 页 drift_lab），paired n=3，CI [0,12] 宽：**描述性信号，非统计证明，非泛化**。
2. **跨异质多页簇共享规则回灌未成功**（成员特异规则不泛化）；feedback_accepted=1 为单页簇平凡泛化。「同簇规则复用摊薄成本」在异质簇上的收益**未实证**。
3. duplicate-main 修复为 no_effect（回退已恢复，drift=no_shared_rule 仍触发）→ 触发语义在「回退已成功」时可能冗余；unnecessary_repair_zero 按冻结定义（drift 计为有效触发）通过，但如实标注该修复无增值。
4. content-moved 经 `//body` 宽容器修复，小夹具可行；复杂真实页的噪声/精度风险未证。
5. judge 判改善≠真实改善（程序侧核 recall 佐证一致，但程序诊断亦未校准）；一致率≠准确率。
6. 单标注者背景局限延续；judge 分数仍**非训练奖励**。
7. 回退触发≠恢复成功的 P-C 诚实负面在 role-drift 上由**修复**解决（recall 0→1.0），但修复规则泛化受限。

## 11. 与最终目标的差距 / 下一步（不自动启动）

P-D 闭环已实现并验证（漂移→修复→回灌→复用，含 accepted/blocked 两路径），修复能力在退化候选上得到信号（补 node5 缺口）。距「基于 Rubrics 的大模型输出自动化评估 + 聚簇摊薄 GPU 成本」的最终目标，剩余：

1. **异质簇共享规则泛化**：修复需产出跨布局通用规则（如 union XPath）才能回灌多页簇；当前成员特异修复不泛化。候选方向：修复 prompt 注入簇内多布局参考、泛化校验驱动的规则搜索（需独立预注册）。
2. **真实站点 + 规模**：drift_lab 为合成机制夹具；真实模板族漂移修复、LSH 海量页面成本摊薄收益未实证。
3. **P-E（gated）**：Agentic RL / GRPO 真实训练（GPU + 预算审批），以聚簇分摊推理成本为前提；目前仅 toy_rl/dom_rl 脚手架，无真实训练。
4. **reward 接线**：v1.4.1 受控范围 reward 资格已成立，但 judge 分数接入训练奖励为后续独立工程（非本实验）。

---

*本报告交付后 P-D 基本完成。P-E 不自动启动。冻结工件零改写；秘密扫描 NONE；全量 715 tests OK。GitHub：github.com/hqli631/offline_web_extractor main。*
