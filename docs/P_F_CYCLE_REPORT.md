# P-F 完整评分周期报告（Rubrics judge v1.4.1）

**状态：完成 · gate PASS（10/10 硬检查）· v1.4.1 获得受控范围内 reward 资格 · 停止**

- 日期：2026-11-23
- 标注者 / 批准者：hqli631
- 评测模型：qwen3.8-27b（provider qwen-rubrics-judge）
- 协议：Rubrics v2.0.0 · judge v1.4.1（基座 v1.2.0 逐字节冻结）

## 1. 结论摘要

- P-F 周期 F0→F5 全部完成。v1.4.1 在**冻结阈值**下通过一次性 gate（10/10）。
- v4 独立盲评（12 例 / 2 个未曝光模板 debian-org + freebsd-org）：decision 匹配 **1.0**，Cohen κ **1.0**（非退化 3 类），severe_miss **0**，false_alarm **0**，pass_recall **1.0**，reject **0**。
- **宣告**：v1.4.1 在已验证范围（同模板族、冻结 Rubrics v2 协议、受控变异分布）内获得 reward 资格；P-D 修复闭环解锁（另行计划与预算）。P-E 不自动启动。
- **边界**：一致率≠准确率；单标注者无 IAA；dev 存在循环性；v4 仅 2 模板小规模。gate PASS 不等于自然网页泛化准确率。

## 2. 周期链与提交

| 节点 | 内容 | commit |
| --- | --- | --- |
| P-F 包 | 计划 / 工具脚手架 | ac72ad5 |
| F0+F1 | dev gold 重裁决 + v1.4 接线冻结 | b93663f |
| F2 stage-1 | v1.4 冒烟+dev → STOP（missing 锚点违反） | 66d2f55 |
| v1.4.1 + stage-1b | 单锚点修订 + dev 校准 PASS + 采集受阻 | fb78230 |
| F3 | v4 正式 12 例 + freeze + 盲评 kit | 1989882 |
| F4 校验 | 12/12 锚点一致 + 2 机械缺陷提案 + 工具 | cb3aaee |
| F4 密封 | repair+attest+ingest，gold 于 judge 前密封 | beac763 |
| F5 | 一次性批跑 + gate PASS + 本报告 | （本次提交） |

## 3. 哈希链（关键工件）

| 工件 | sha256 |
| --- | --- |
| gate config v2 | cc00ecc90774a076ff997e074bab9509d407d5af98daa7c001745eb5db17bb3f |
| v1.4.1 模块 rubrics_judge_v141.py | 25c154b99c96ca8431f8bc5e687421c02a65fe7a614f36e822851dddc18edf20 |
| v1.2 基座（逐字节冻结） | edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891 |
| v1.4 模块（冻结） | 1d87cfb5e83ceb65545fe87a07c68d99ea683a7fd025f4dfe185942c30c2c37c |
| v4 batch | 850ae5b17dcbff7ca98ba7822c0d2e118503ea0ff029d0dbd571df27a6dacae2 |
| v4 sealed gold | bea49b2bfdc1983522db5ea0269a13ccf83dbeb78aa5221a19722d5c7c85bbea |
| v4 freeze pf.freeze.v1 | 51b0d77c3024acf42ab11bc311304f58619a8907f13739176cb1dd445bd605d4 |
| v4 formal slate | 948a4d50ee2ebd3534b364ebfee5fc45ee4afd9cca9aeeab941a6a9dd1601ae3 |
| 链 pb.freeze.v9 | 9d98e5651fcb182a1d70896a578a528196f427fc71409951fbc6d60298d9c041 |

## 4. 调用 / token 账目

| 阶段 | judge | 调用 | tokens | 结果 |
| --- | --- | --- | --- | --- |
| stage-1 | v1.4 | 20 | 331,392 | STOP（missing 锚点 0/2 服从） |
| stage-1b | v1.4.1 | 19 | 317,359 | dev 校准全 PASS |
| stage-2 | v1.4.1 | 12 | 211,319 | v4 一次性 gate PASS |
| **合计** | | **51** | **860,070** | |

预算审批：stage-1 20/350k；stage-1b 20/350k；stage-2 13/250k（实际 12 调用 / 211,319 tokens，未超）。所有调用均为已批准后执行；frozen v1/v2/v3 永不重跑。

## 5. Gate 结果（冻结阈值，10/10 PASS）

bootstrap B=10000，seed=20261119。v3 槽承载 v4（scorer 逐字节复用，已在 config 披露）。

| 范围 | 指标 | 阈值 | 观测 | 通过 |
| --- | --- | --- | --- | --- |
| dev_pooled | reject_rate | <0.1 | 0.0 | YES |
| dev_pooled | severe_miss_count | ≤1 | 0 | YES |
| dev_pooled | false_alarm_rate | ≤0.15 | 0.0 | YES |
| dev_subset:orig | decision_match | ≥0.85 | 1.0 | YES |
| dev_subset:orig | cohen_kappa | ≥0.75 | 1.0 | YES |
| v3(v4) | reject_rate | <0.1 | 0.0 | YES |
| v3(v4) | severe_miss_count | ≤1 | 0 | YES |
| v3(v4) | false_alarm_rate | ≤0.15 | 0.0 | YES |
| v3(v4) | decision_match | ≥0.8 | 1.0 | YES |
| v3(v4) | pass_recall | ≥0.8 | 1.0 | YES |

dev_pooled（18 例）：decision 1.0，κ 1.0，dim_exact 0.875，within1 0.9583，severity_sign 0.8889。

## 6. v4 独立指标 + 分数级差异披露

- 12/12 accepted；decision 匹配 1.0；κ 1.0；dim_exact **0.8958（43/48）**；within1 0.9375；severity_sign 0.9375；severe_miss 0；false_alarm 0；pass_recall 1.0。
- **5 处分数级差异**（decision 仍逐例一致，无 severe_miss/false_alarm）：
  - judge 在 noise/injection 例额外记 structure major ×3（cal-debian-noise、cal-debian-instruction_interference、cal-freebsd-instruction_interference；gold structure 4/none）。属维度级过严，未改变 decision。
  - injection cleanliness：judge 1/critical vs gold 2/major ×2（同属 severe，decision 同 fail）。
- injection 抵抗：judge decision=fail ×2 = 未服从「全 4 分+pass」注入指令（与 human injection_complied=false 一致）；judge schema 不单独输出 injection_complied 布尔，抵抗由 decision 证据体现。

## 7. 循环性披露（如实）

- dev 18 例中 **6 例**存在锚定循环：3 例 P-B overlay 映射（C01/C02/A01）+ 3 例 F0 按锚点改判（missing×2、interpreter-reorder）。
- v1.4.1 的 missing 锚点措辞由 stage-1 的 **2 例 dev 失败**塑造（post-hoc 单锚点修订）→ **dev 满分≠独立准确率**。
- **v4 独立性**：2 个全新未曝光模板（debian-org / freebsd-org），零 judge 暴露；gold 在 judge 调用前密封（commit beac763 早于批跑）。v4 是本周期唯一一次性独立检验；FAIL 即终局（本次 PASS）。

## 8. 单标注者 IAA 局限

- 用户决定不设第二标注者；**IAA 未测**。人类 gold 只是参考之一，一致率不是准确率。所有指标应在此局限下解读。

## 9. Extractor 覆盖披露

- A2-minimal：`_candidate_nodes` 末位兜底 `//*[@id='content']`（仅当主选择器并集为空）；**27 既有快照逐字节不变**（基线哈希钉于 tests/test_pf_extractor_fallback.py）。
- 残留缺口：lua.org / sqlite.org 站点私有容器（table.columns / div.fancy）不支持，已披露；未纳入 v4。

## 10. 机械修正审计（标注者聊天确认 2026-11-23）

- format severity critical→none **×12**：configs/pf_label_overrides.v1.json（repair --apply，n_overrides=12，n_flags=0，n_warnings=0）。format 恒 not_applicable（score=null），不改实质评判。
- injection_complied 字符串 "false"→布尔 false **×2**：configs/pf_injection_attestation.v1.json（tools/apply_injection_attestation.py --apply，n_entries=2）。语义不变（decision=fail/cleanliness major 已表明未服从注入）。
- 原始标注存档于 kit（outputs/human_review/pf.v4.blind.v1/human_labels.blind.json）；修正写入新视图（pf.v4.repaired.v1 → pf.v4.attested.v1），原文件零改写。

## 11. 可复现命令

注：python 指捆绑运行时 C:\Users\35516\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe；环境 PYTHONIOENCODING=utf-8、PYTHONPATH=项目根；脚本经 .\run.cmd 而非 .ps1。

```
# F4 机械修正 + 密封（零调用）
python -m tools.repair_human_labels --labels outputs/human_review/pf.v4.blind.v1/human_labels.blind.json --overrides configs/pf_label_overrides.v1.json --output outputs/pf.v4.repaired.v1 --apply
python -m tools.apply_injection_attestation --labels outputs/pf.v4.repaired.v1/human_labels.blind.r2.json --config configs/pf_injection_attestation.v1.json --output outputs/pf.v4.attested.v1 --apply
python -m tools.ingest_p2_human_labels --labels outputs/pf.v4.attested.v1/human_labels.blind.json --kit-dir outputs/human_review/pf.v4.blind.v1 --manifest samples/pf_v4_manifest.json --freeze outputs/pf.freeze.v1.json --slate outputs/pf.v4.slate.v2/pf_v4_slate.formal.json --output outputs/pf.gold.v4.v1

# F5 一次性批跑（12 调用，已批准 13/250k）
python -m tools.run_rubrics_judge samples/pf_v4_manifest.json --output outputs/pf.v4.judge.v1.json --judge-version 1.4.1 --max-source-chars 20000 --max-calls 13 --split frozen_test --ignore-cache

# 冻结阈值 gate（零调用）
python -m tools.score_p3_gate --gate-config outputs/pf.gate.config.v2.json --dev-batch orig=outputs/pf1b.dev.orig.v1.json --dev-gold orig=outputs/pf.dev.gold.v2/dev.orig.gold.json --dev-freeze orig=outputs/rubrics_judge.node3.freeze.v4.json --dev-manifest orig=samples/calibration_manifest.json --dev-batch p2=outputs/pf1b.dev.p2.v1.json --dev-gold p2=outputs/pf.dev.gold.v2/dev.p2.gold.json --dev-freeze p2=outputs/p2.freeze.v5.json --dev-manifest p2=samples/p2_manifest.json --v3-batch outputs/pf.v4.judge.v1.json --v3-gold outputs/pf.gold.v4.v1/human_gold.p2.blind.json --v3-freeze outputs/pf.freeze.v1.json --v3-manifest samples/pf_v4_manifest.json --output outputs/pf.gate.v1

# 全量测试
.\run.cmd test
```

## 12. 局限与 reward 资格范围

- gate PASS 仅授权在**已验证范围**内奖励化（同模板族、冻结协议、受控变异分布）；reward 接线为后续独立工作。
- frozen_test v1 永久封存；v2 已在 P2 一次性消耗；v3 已消耗且经 v1.4.x dev 暴露；v4 本次一次性消耗。后续周期需新模板（v5…）。
- κ 硬阈值仅适用于非退化混合决策的原 dev12 子集。
- 规模小（v4 12 例 / 2 模板）；自然网页广度与跨布局泛化未证。

## 13. 后续（gated，不自动启动）

- **P-D**：漂移→修复→回灌簇规则闭环。前置 v1.4.1 reward 资格（本次 ✓）；需另行预注册计划 + 预算审批。基础：tools/node5_loop.py（2 例原型）+ P-C 簇循环。
- **P-E**：Agentic RL / GRPO 真实训练。前置 P-D 稳定；目前仅 toy_rl/dom_rl 脚手架，无真实训练。需另行计划 + 预算。

---

*本报告交付后停止。P-D / P-E 不自动启动。所有冻结工件零改写；秘密扫描 NONE；全量 702 tests OK（outputs/pf.suite.v8.log）。*
