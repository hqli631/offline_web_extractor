# P2 规模扩展与统计强化 · 预注册方案（调用/采集前冻结）

日期：2026-11-19（Asia/Shanghai）。状态：**预注册 drafted；新数据采集与模型调用尚未发生，等待用户批准预算与配合项**。
上游：P1.5 交付（docs/P1_5_DELIVERY_REPORT.md，judge v1.2.0 dev ACCEPT：拒绝 0%、severe_miss 0、分歧 1、一致率 0.9167/κ0.8554）。P2 目标：把 dev 上的可信度结论推进到**独立泛化检验 + 统计区间 + 标注者间一致性**。

## 0. 诚实边界（继承，不可动摇）

一致率 ≠ 准确率；**dev ≠ 泛化**（P1.5 在 dev 迭代，有过拟合风险，P2 须独立测试集确认）；单一标注者无 IAA → P2 引入第二标注者；frozen_test **v1（11 例）永久封存**，P2 不再用于任何调参或验收，新建 **frozen_test v2** 预注册后封存；silver ≠ human gold；judge 分数在 P3 门槛达标前不作训练奖励。所有新数字区分 dev / 泛化 / 裁决后，不得混用。

## 1. 现状与扩样可行性（零调用勘察）

现有 23 例：dev 12（appetite/blurb/iana）+ frozen_test v1 11（mdn/github/w3clink）；8 变异类型；6 模板。
samples/ 未用候选源页预算检验（max_source_chars=20000，均 <110k）：
- **充实可用**：python_interpreter_zh（zh，32 块）、nasa-voyager-news.candidate（en，23 块）、w3c_accessibility_intro_zh（zh，61 块）。
- 偏薄（3–4 块，变异受限）：code_lab、list_lab、news（仅 clean/noise 类有限变异，可选）。
- **禁用**：webdev-learn-html.candidate（封存验证页，不得参与校准/调参）；rfc/gnu/whatwg（超预算，node3 已排除）。

## 2. 假设（预注册）

- **H1（泛化）**：judge v1.2.0 协议在**新模板**构成的 frozen_test v2 上，决策一致率/κ 与 dev 同量级（不显著崩塌），severe_miss ≤1、拒绝率 <10%。若泛化显著低于 dev → 揭示 dev 过拟合，如实报告。
- **H2（IAA）**：第二标注者与第一标注者（hqli631）在独立复核子集上 κ ≥0.6（实质一致）；若低 → 人类 gold 本身噪声大，judge 一致率上限受限，须如实声明。
- **H3（统计）**：bootstrap 95% CI 量化现有 dev 一致率/κ 的不确定性（小样本 CI 宽）。
- **H4（跨家族）**：跨家族第二 judge（gpt-5.6-sol via ccswitch）与 qwen3.8-27b 的 judge 间一致率，识别家族特异性偏差（描述性）。

## 3. 工作包与顺序

### WP1 统计强化（零调用，先行）
- 工具 tools/bootstrap_stats.py：对 judge–human 决策一致率、Cohen κ、逐维 exact、严重度符号、severe_miss/false_alarm 率做 **bootstrap 95% CI**（案例级重采样，B=10000，固定种子）；配对显著性（v1.0 vs v1.1 vs v1.2 dev 决策一致率差异，bootstrap 配对 CI / McNemar）。
- 先对现有 P0/P1/P1.5 dev 结果计算 CI（立即产出，无需新数据）。

### WP2 扩样工程（零调用构建 + 需用户确认源页）
- 扩展 tools/build_calibration_set.py：新增 BASES（python_interpreter_zh、nasa-voyager-news、w3c_accessibility_intro_zh；可选 code_lab/list_lab/news），各 × 变异 {clean, missing_paragraph, noise, duplicate, reorder}（充实页）；source_only 或 with_gold（with_gold 需创建 expected.json 参考提取并经用户核验）。
- 新案例 silver 标签由 derive_expected 自动生成（assistant_silver，非 human gold）。
- **分层**：按 模板 × 变异类型 × split 分层；新模板整页隔离 split（check_manifest_isolation，同源不跨 split）。
- 目标规模：**总计 ~45–55 例**（现有 23 + 新增 ~22–32）。最小可行 ≥40。
- 产出 P2 manifest（新文件，不改 v1 冻结 manifest）+ freeze v5（新校准集冻结）。

### WP3 新 frozen_test v2 预注册封存（零调用，判前冻结）
- 从新模板中划 **frozen_test v2**（建议 nasa-voyager-news + w3c_accessibility_intro_zh 两整页，~10 例，含 with_gold/source_only 混合），**预注册 split 与案例清单后冻结**，judge 评估前不得改动。
- 其余新模板（python_interpreter_zh 等）入 **dev 扩展**（可调参）。
- frozen_test v1 永久封存（不再评估/调参）。

### WP4 人类 gold 与 IAA（需用户 + 第二标注者）
- 新案例人类 gold：用户（hqli631）按盲评工具包独立标注新案例（中性编号、密封映射，沿用 P0 防泄漏机制）。
- **IAA**：第二标注者独立复核 ≥12 例（dev/test 混合，盲评，不知第一标注者结果），计算标注者间 Cohen κ（决策）+ 逐维一致率。第二标注者由用户安排。
- 工具：扩展 build_human_review_kit / ingest_human_labels 支持 P2 manifest 与双标注者；新增 tools/compute_iaa.py。

### WP5 跨家族 cross-judge（需预算 + provider 接线）
- 第二 judge：gpt-5.6-sol（ccswitch OpenAI 兼容中转，env.local CCSWITCH_API_KEY）。需把 judge provider 适配 OpenAI 兼容接口（judge 层改动，走 freeze 修订；或独立 cross-judge 脚本不改生产 judge）。
- 在 dev 子集（~12 例）同协议评估，量化 judge 间一致率（描述性）。

### WP6 泛化验收与报告（需预算）
- judge v1.2.0 在 **frozen_test v2** 上评估（一次性，不调参），对照人类 gold：决策一致率/κ、severe_miss、拒绝率 + bootstrap CI。
- 验收阈值（预注册，泛化）：frozen_test v2 拒绝率 <10%、severe_miss ≤1、决策 κ 与 dev 差异在 bootstrap CI 内不显著崩塌（具体阈值见 §4）。
- 交付 docs/P2_DELIVERY_REPORT.md（命令+哈希+测试日志+统计方法+IAA+泛化 vs dev+如实局限）。

## 4. 验收阈值（预注册）

- **泛化（frozen_test v2，一次性）**：拒绝率 <10%；severe_miss ≤1；决策一致率 bootstrap 95% CI 下限报告（不硬卡 κ 点估计，因小样本）；若 dev→test 决策一致率下降的配对 bootstrap 95% CI 不含 0 且幅度 >0.15 → 判「显著泛化落差」，如实标记过拟合风险。
- **IAA**：第二标注者 κ 报告 + 95% CI；κ ≥0.6 为实质一致（描述性，不硬卡）。
- **统计**：所有一致率/κ 附 bootstrap 95% CI；dev 与泛化分开报告。
- 阈值一经批准不得事后修改；变更须修订记录。

## 5. 预算与用户配合项（待批准/安排）

模型调用（judge v1.2 评估新案例 + 跨家族 cross-judge）：
| 项 | 估算调用 | 估算 tokens |
| --- | --- | --- |
| 新案例 judge v1.2 评估（~22–32 新例，dev+test） | ~32 | ~480k |
| 跨家族 cross-judge（dev 子集 12） | 12 | ~180k（gpt-5.6-sol 计价单列） |
| 冒烟/稳定性 | ~4 | ~60k |
| **上限** | **~48** | **~720k** |
（新案例若 with_gold 需 gold 创建；source_only 无需。实际以构建后案例数为准，批准前报精确清单。）

**需用户配合（明确操作指导，见交付时细化）**：
1. 确认新源页可用（python_interpreter_zh / nasa-voyager / w3c_accessibility；是否需新采集页）。
2. 安排**第二标注者**（独立复核 ≥12 例）。
3. 对新案例做**人类 gold 盲评标注**（沿用 P0 工具包）。
4. 批准模型调用预算 + 跨家族中转可用确认。

## 6. 可复现交付物

bootstrap_stats.py / compute_iaa.py / 扩展构建器与 kit；P2 manifest + freeze v5；frozen_test v2 预注册封存记录；命令链 + 哈希 + 测试日志；docs/P2_DELIVERY_REPORT.md（统计方法 B=10000 种子、IAA、泛化 vs dev、CI、局限）。

## 7. 批准记录

- 用户批准预算 / 配合项：________（待填；批准前零调用、零新采集）。
- 预注册固定时间：2026-11-19；变更须修订记录。
