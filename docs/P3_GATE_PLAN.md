# P3 奖励化门槛预注册提案（DRAFT · 待用户批准后冻结）

> 状态：**提案**。阈值与数据设计经用户批准后方为预注册约束；批准前零调用、零新采集。
> 依据：P2 交付报告 §8 校准发现（false_alarm 0.33–0.42、注入 3 例人类 gold 漏检、judge 漏标 minor×3、κ 退化、pass 类未检验）。

## 1. 目的与纪律

- 目的：判定 judge 分数何时可作为提取器改进（SFT/RL）的奖励信号。**门槛达标前禁止奖励化**（沿用既有约束）。
- 纪律：frozen_test v1 永久封存；frozen_test v2 已一次性消耗，**不得重评/调参**；P2 封存 gold 不回改；一致率≠准确率；单一标注者局限持续存在（IAA 已被用户取消）。
- 校准复审（outputs/human_review/p3.calibration.v1，10 例）结论仅用于：(a) 如实 findings；(b) **预注册**锚点/协议修订提案（judge v1.3 候选）。禁止看结果后事后改协议再重报。

## 2. 校准复审 → 修订提案路径

1. 用户复审 C01–C10，填 p3_findings.json（verdict ∈ judge_correct / human_correct / anchor_ambiguous / both_partially_correct）。
2. 助手汇总 findings → 若证据支持锚点歧义/漏检模式，起草 **freeze 修订提案**（judge v1.3 候选）：仅限锚点措辞澄清与证据约束强化（例如：注入指令文本=critical 污染；噪声量级锚点示例；乱序严重度按既有锚点执行），**不得针对具体案例刷分**。
3. 修订提案经用户批准 → amend freeze（v6）→ judge v1.3 在 **dev 池**评估（可调参轮）；v3 封存测试判前冻结。
4. 若 findings 不支持修订（judge v1.2 已正确、人类 gold 错）：不修订协议；门槛评估直接用 v1.2 + 修正后的人类 gold 流程（新案例盲评，不回改旧 gold）。

## 3. Gate 数据设计

- **dev 池（18 例）**：原 dev12（P0 裁决后 gold，混合决策，κ 非退化）+ P2 dev6（纯盲评 gold，全 uncertain）。分开报告再合并；裁决后 gold 的锚定局限如实注明。
- **新 sealed test v3（pass 类泛化，12 例）**：2 个未用于校准的模板 × 6 变异（clean/missing/noise/duplicate/reorder/injection），with_gold（expected.json 程序参考 + 用户盲评 human gold），**预注册封存后一次性评估**。源页须 raw HTML ≤ 20,000 字符（冻结 20k 上限下不截断 → pass 可达）。
  **尺寸核验（2026-11-22，零调用）**：现有本地页中 ≤20k 的中等页面（appetite 16,087 / iana 6,730 / w3c-link 7,271）**均已用于校准**（模板隔离禁止复用）；其余真实页 >40k；code_lab/list_lab/news/drift_lab 仅 296–778 字符（微夹具）。因此两个选项：
  - **(a) 微夹具路线**：code_lab + list_lab（或 news）×6 变异。零采集、零额外批准；但内容极小、变异近乎平凡，pass 类证据强度弱（如实降级声明）。
  - **(b) 新采集路线（推荐）**：采集 2 个真实短文章页（目标 raw 5k–18k 字符，如短新闻/博客），需用户批准**新数据采集**（2 次 HTTP 抓取，零模型调用）；证据强度显著更高。采集来源与尺寸构建时核验并记录哈希。
  选项由用户在批准门槛时一并选定；选定前不构建 v3。
- 用户配合项：v3 盲评 12 例（沿用中性编号+密封映射工具链）；门槛阈值批准；v3 数据路线 (a)/(b) 选定（(b) 含采集批准）；模型预算批准。

## 4. 门槛阈值（提案 · 待批准）

| 指标 | dev 池（18） | v3 一次性（12） |
| --- | --- | --- |
| 拒绝率 | < 10% | < 10% |
| severe_miss | ≤ 1 | ≤ 1 |
| false_alarm 率 | ≤ 0.15 | ≤ 0.15 |
| 决策一致率 | ≥ 0.85（混合决策子集） | ≥ 0.80 |
| Cohen κ | ≥ 0.75（原 dev12 子集，非退化） | 报告 + CI（不硬卡） |
| pass 类一致率 | — | human=pass 案例中 judge=pass ≥ 0.80 |

- 全部指标附 bootstrap 95% CI（B=10000，seed=20261119）；dev 与 v3 分开报告。
- false_alarm ≤0.15 的理由：奖励用途下误报会惩罚好输出，P2 实测 0.33–0.42 必须经校准下降；该阈值为新预注册，非事后修改 P2 阈值。
- **达标判定**：dev 池与 v3 全部硬阈值满足 → gate PASS；任一不满足 → gate FAIL（如实报告，不重测刷分）。
- gate PASS 后：judge 分数可在**已验证范围**（同模板族、冻结协议、受控变异分布）内作奖励；超出范围需新证据。奖励化本身（SFT/RL 接线）是后续独立工作，不在本目标内自动启动。

## 5. 预算估算（待批准，精确清单以 v3 构建后为准）

| 项 | 调用 | 估算 tokens |
| --- | --- | --- |
| judge v1.3（或 v1.2）× dev 池 18 | 18 | ~280k |
| judge × v3 一次性 12（短页不截断） | 12 | ~120k |
| 冒烟/resume（计入上行） | (2) | (计入) |
| **上限（+15% 裕量）** | **~30** | **~460k** |

批准前零调用。v3 构建（短页选择/变异/silver/expected/盲评包）零调用。

## 6. 交付物

tools/build_p3_review_kit.py（已建，10 测试）；p3_findings 汇总工具；freeze 修订提案（如需要）；v3 构建器 + 封存记录；gate 评分工具 **已建**（tools/score_p3_gate.py，29 测试；配置驱动 fail-closed：拒绝 draft 配置、校验冻结 batch_config 含 judge_version、数据冻结哈希、κ 退化子集强制 FAIL、v3 无 human=pass 案例时 pass_recall 记 FAIL、输出拒绝覆盖；阈值只从批准后的 frozen gate-config 读取）；docs/P3_GATE_REPORT.md（命令+哈希+测试日志+统计方法+如实局限）；GitHub 同步后停止。

## 7. 批准记录

- 校准复审完成：**2026-11-22 hqli631，10 案 verdict 已接收封存（outputs/p3.findings.v1）；amendment_signal=true → 修订提案 docs/P3_AMENDMENT_PROPOSAL.md（待批准）**
- 阈值批准：________（待填；批准前本文件仅为提案）
- 预算批准：________（待填）
- 预注册冻结时间：________（批准后记录）
