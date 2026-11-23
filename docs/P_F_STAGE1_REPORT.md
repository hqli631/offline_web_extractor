# P-F 阶段1交付报告：v1.4 dev 校准（触发预注册停止条件）

日期：2026-11-23 ｜ 批准：hqli631（阶段1预算 20 调用/350k tokens；按锚点改判；路线 A）
状态：**F0/F1/F2 完成；F3–F5 未启动——按预注册停止条件停下，等待用户决策。**

## 1. 执行摘要

- **F0 重裁决**：3 例 dev gold 按已批锚点改判（missing×2 → completeness 2/major/fail；reorder → structure 2/major/fail），审计视图 `outputs/pf.dev.gold.v2/`，其余 15 例逐字节不变，上游密封文件零改写（输入哈希复核通过）。
- **F1 接线冻结**：`run_rubrics_judge.py --judge-version {1.2,1.4}` opt-in（默认 v1.2 行为不变，缓存键跨版本隔离已测）；`outputs/pf.gate.config.v1.json` 冻结（dev/v3 阈值逐字节沿用 P-B v2，judge pin 1.4.0）；`outputs/pf.protocol.v1.json` 协议 pin（链 pb.freeze.v9）。
- **F2 校准**：20 次真实调用全部在批准预算内；**missing-body 锚点系统性未被遵循（2/2 可评案例均 3/minor）**，触发计划 F2 预注册停止条件："dev 出现系统性锚点违反 → 停下报告，不自动调参"。

## 2. 预算账目（qwen3.8-27b）

| 批次 | 调用 | tokens | 输出 |
| --- | ---: | ---: | --- |
| 冒烟（cal-appetite-clean） | 1 | 15,504 | outputs/pf.smoke.v1.json |
| dev orig 12 | 12 | 175,022 | outputs/pf.dev.orig.v14.v1.json |
| dev p2 6 | 6 | 123,954 | outputs/pf.dev.p2.v14.v1.json |
| blurb-missing 重试 | 1 | 16,912 | outputs/pf.dev.orig.v14.v2.json |
| **合计** | **20/20** | **331,392/350,000** | 未超支 |

重试说明：cal-blurb-missing_paragraph 两次独立全新调用模型均返回空对象 `{}`（finish_reason=stop，模型侧确定性失败，非瞬时网络错误）。第一次失败后删除该案例缓存条目再 resume（其余 11 例缓存复验零成本）；第二次仍 `{}`。预算用满，未追加调用。该案例计为 rejected。

## 3. 校准指标（gate 依据轨：pf.dev.gold.v2）

| 指标 | 观测 | dev 阈值 | 判定 |
| --- | --- | --- | --- |
| reject_rate（pooled 18） | 0.0556（1/18） | <0.10 | 通过 |
| severe_miss_count（pooled） | **2** | ≤1 | **不通过** |
| false_alarm_rate（pooled） | 0.0 | ≤0.15 | 通过 |
| decision_match（orig 子集） | 0.9091 | ≥0.85 | 通过 |
| Cohen κ（orig 子集） | 0.8429 | ≥0.75 | 通过 |

若此即 gate dev 检查 → **FAIL（severe_miss 2>1）**。这是校准而非 gate；v4 独立测试未运行。

## 4. 锚点遵循逐项审计

| 锚点 | 结果 | 证据 |
| --- | --- | --- |
| R1 乱序→major/fail | **3/3 遵循** | appetite/blurb/interpreter-reorder 均 fail |
| R2 噪声→major/fail | **3/3 遵循** | appetite/blurb/interpreter-noise 均 fail |
| 注入→污染/fail | **1/1 遵循** | interpreter-injection fail，未服从 |
| 重复按量级 | 符合 | appetite/interpreter-duplicate uncertain（小局部重复 minor 轨） |
| R3 标题空白/编号 | 符合 | appetite-title_number uncertain（minor 轨） |
| **缺失关键正文→≤2/major** | **0/2 遵循（系统性违反）** | appetite-missing：completeness 3/minor/scored，reason 明确承认 "Missing the first paragraph of the article body" 仍定 minor；interpreter-missing：3/minor/partial（源截断），同样承认缺失仍 minor |

**根因判断**：v1.4 修复了 P-B 的 reorder/noise 低估，但 missing 锚点措辞被模型的"量级直觉"覆盖——模型识别出缺失却把"首段/引言段缺失"归为小缺陷。这与 P-B 独立测试暴露的缺陷同类，仅在 missing 维度残留。

## 5. 双轨披露

- **机械轨（密封原始 gold，仅披露非 gate 依据）**：decision_match 0.7647，false_alarm 0.2353（4/17），severe_miss 0。false_alarm 升高是预期冲突：v1.4 按裁决锚点把 reorder 判 major/fail，而旧密封 gold 为 minor/uncertain——裁决史已改判，机械轨保留原值不改写。
- **锚定循环**：dev 轨道 6/18（overlay 3 + 本次重裁决 3）；独立泛化结论只能来自 v4。
- 单标注者，IAA 未测；一致率≠准确率。

## 6. 停止决策与后续选项

按预注册计划停止，**不自动调参、不消耗 v4 一次性机会**（已知 missing 缺陷下跑 v4 大概率浪费密封测试）。v1.4 仍 **reward-INELIGIBLE**；P-D/P-E 继续 gated。

供用户决策：
- **A（推荐）v1.4.1 修订周期**：强化 missing 锚点措辞（任何 gold 中存在而候选缺失的正文段落一律 major，与位置/大小无关；首段/引言段属关键正文），新预注册 + 新 dev 校准预算（约 19 调用/350k），v4 仍未触碰；reorder/noise 已验证的锚点不动。
- **B 按现状跑 v4**：不推荐——已知系统性缺陷下消耗一次性密封测试。
- **C 暂停**：保留全部产物，择期再议。

## 7. 工程验证

- 新增测试：override 9 + runner 6 + dev scorer 4 + collector 8 + v4 formal build/kit 7 = 34；全量套件见 outputs/pf.suite.v4.log。
- F3 工程已就绪但未执行采集：`tools/collect_pf_v4_sources.py`（预注册 sqlite/debian+apache 备选，≤10 抓取）、`tools/build_pf_v4_calibration.py`（正式 12 例+freeze+slate）、kit builder 支持正式路线 A。选项 B iana 草案保留并标记 superseded。
- Secret scan：NONE（每次提交前）。

## 8. 复现命令

```
python -m tools.apply_pf_dev_overrides --output outputs/pf.dev.gold.v2
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/pf.smoke.v1.json --judge-version 1.4 --max-source-chars 20000 --max-calls 1 --split development --ignore-cache
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/pf.dev.orig.v14.v1.json --judge-version 1.4 --max-source-chars 20000 --max-calls 12 --split development --ignore-cache
python -m tools.run_rubrics_judge samples/p2_manifest.json --output outputs/pf.dev.p2.v14.v1.json --judge-version 1.4 --max-source-chars 20000 --max-calls 6 --split development --ignore-cache
python -m tools.score_pf_dev --gate-config outputs/pf.gate.config.v1.json --dev-batch orig=outputs/pf.dev.orig.v14.v2.json --dev-gold orig=outputs/pf.dev.gold.v2/dev.orig.gold.json --dev-freeze orig=outputs/rubrics_judge.node3.freeze.v4.json --dev-manifest orig=samples/calibration_manifest.json --dev-batch p2=outputs/pf.dev.p2.v14.v1.json --dev-gold p2=outputs/pf.dev.gold.v2/dev.p2.gold.json --dev-freeze p2=outputs/p2.freeze.v5.json --dev-manifest p2=samples/p2_manifest.json --mechanical-gold orig=outputs/human_review/final.v1/human_gold.final.json --mechanical-gold p2=outputs/human_review/p2.gold.v1/human_gold.p2.blind.json --output outputs/pf.dev.calibration.v1
```

输入/输出哈希见 `outputs/pf.dev.calibration.v1/pf.dev.json` 与 `outputs/pf.protocol.v1.json`。
