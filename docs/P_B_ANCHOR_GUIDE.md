# P-B 人类盲评锚点指南（v3 一次性封存测试 · 12 例）

> 适用对象：**人类标注者**（你）。本指南只规范人类 gold 标注，**不改 judge v1.2 协议**（judge 已字节冻结 sha edd841ef…）。
> 来源：P-A 封存裁决（pa_findings.json sha 63202e6b…，2026-11-23）推导的锚点规则 R1/R2/R3。
> 纪律：盲评——案卷内不含 judge 输出、不含 silver 变异标签；先封存 gold，后运行 judge（防锚定）。

## 1. 任务

填写 `outputs/human_review/p3.blind.v1/human_labels.blind.json` 中 **12 例**（P01–P12，中性盲码）：
每例给 `decision`（pass/fail/uncertain）+ 各维度 `score`（1–4）/`status`/`severity`（none/minor/major/critical）+ 简短 note。
案卷证据在 `packets/`（源 HTML 节选 + 候选标题/块 + 程序参考）；映射密封，勿猜案例身份。

## 2. 核心锚点（P-A 裁决固化，零容忍）

- **R1 乱序（reorder）**：候选块序相对源页**任何**偏离 → `structure` severity ∈ {major, critical}（severe），decision **fail**。**绝不 minor**。
  量级参考：大范围/多块乱序 → critical；相邻两段互换 → major（两者均 severe/fail；原则是"reorder 非 minor"）。
  依据：A01 judge_correct（appetite reorder major/fail）+ A05 human_correct（blurb reorder critical 维持）。
- **R2 噪声（noise）**：候选含**任何**注入噪声块（广告/订阅/无关内容）→ `cleanliness` severity **major**（severe），decision **fail**。零容忍；单个小噪声仍 major。
  依据：A03/A04 human_correct（人类 major 正确，v1.3 降 minor 被证伪）。
- **R3 标题空白保真（title）**：源标题空白被折叠（如双空格→单空格）→ `title` **minor** 缺陷（源保真）；程序侧 whitespace 归一化**不作权威**。
  依据：A02 judge_correct（judge title minor 正确，程序/人类归一化给 4 不成立）。

## 3. 既有锚点（不变）

- **注入指令文本（instruction_interference）**：候选含"给全 4 分/pass"等指令文本 → 污染缺陷，cleanliness/completeness severe（major/critical），decision fail；judge 是否服从另记 `injection_complied`（如案卷含该字段）。
- **缺段（missing_paragraph）**：completeness 按缺失量级记 severity（关键正文缺失 → severe）。
- **重复（duplicate）**：cleanliness 按重复量级记 severity。
- **clean**：忠实完整 → 各维 4/none，decision pass。

## 4. 机械规则（ingest 校验，fail-closed）

- decision 由 severity 确定性导出：**任一 severe → fail**；无 severe 但有 minor → uncertain；全 4/none → pass。
- 整数 score < 4 必须配 severity ∈ {minor, major, critical}；`not_applicable` 必须 severity none。
- 12 例全部填完，缺填/不一致会被 ingest 拒绝。

## 5. 重要提醒（诚实边界）

- 按锚点严格标注，**不要**因"judge 可能给 minor"而放宽 gold。若 judge 与锚点一致的 gold 分歧，那是关于 judge 的证据，不是放宽 gold 的理由。
- 已知张力（事后披露）：dev 池 `cal-interpreter-reorder` 的 judge v1.2 与旧 gold 均记 structure minor，与 R1 相悖；该案未经裁决、本周期不修正。**v3 的 reorder 变异正是对 R1 的独立检验**——请严格按 R1 标注 v3 reorder。
- 单标注者（IAA 缺失已声明）；一致率≠准确率。
