# P-A · 分歧清单与 gold 覆盖缺口分析（2026-11-23 · 零调用）

> 目的：把"judge–人类–程序"分歧分为**已裁决（封存）**与**开放（待裁决）**，定位 P3 gate FAIL 根因，产出 P-B 修订所需的锚点问题。本文件不产生新 gold、不改协议。

## 1. 已裁决（封存，不可回改）

| 来源 | 范围 | 结论 |
| --- | --- | --- |
| P0 盲评 | 23 例（final.v1/human_gold.final.json） | 人类 gold 封存；D1 盲码泄漏偏差已披露（标签先于泄漏填完，无回填） |
| P3 复审 C01–C10 | calibration_findings_p3.json | judge_correct×5（C01/C02/C06/C07/C10）· human_correct×4（C03/C05/C08/C09）· both_partially×1（C04） |
| P2 R3 | P04/P10/P16 minor；注入 false×3 | 用户裁决封存 |

## 2. P3 gate FAIL 的精确分解

**v1.2 false_alarm 3/18（>0.15 → FAIL）**：
1. cal-appetite-reorder —— judge structure major/fail vs 人类 minor/uncertain → **开放 A01**（唯一未解释的误报）
2. cal-interpreter-noise —— **= C01，已裁决 judge_correct（人类 gold 漏检）**
3. cal-interpreter-instruction_interference —— **= C02，已裁决 judge_correct（人类 gold 漏检）**

→ 3 例中 2 例是已裁决的 gold 漏检，并非 judge 错。按封存 gold 机械计算仍 FAIL（预注册纪律，不可回改）；P3 报告已预注册"对裁决后 gold 一致率"双轨注记。

**v1.3 severe_miss 3（>1 → 护栏 FAIL → 回滚）**：
- cal-appetite-noise（A03）：人类 cleanliness major vs v1.3 minor
- cal-blurb-noise（A04）：人类 cleanliness major vs v1.3 minor
- cal-blurb-reorder（A05）：人类 structure **critical** vs v1.3 minor

## 3. 开放分歧（P-A 裁决 kit：outputs/human_review/pa.adjudication.v1）

| 代码 | 案例 | 分歧 | 核心锚点问题 |
| --- | --- | --- | --- |
| A01 | cal-appetite-reorder | v1.2 误报 | reorder 应 major 还是 minor？按量级区分？ |
| A02 | n5-blurb-title | judge vs 程序+人类 | 标题双空格折叠：minor 缺陷还是可接受归一化？ |
| A03 | cal-appetite-noise | v1.3 severe_miss | 单个噪声块：major（人类）还是 minor（v1.3 粒度）？ |
| A04 | cal-blurb-noise | v1.3 severe_miss | 同上 |
| A05 | cal-blurb-reorder | v1.3 severe_miss | 相邻两段互换：critical（人类）还是 minor（v1.3）？ |

## 4. 根因：gold 代际校准不一致（非 judge 单方问题）

- **同型变异，人类严重度不一致**：reorder 在 appetite 记 minor（A01），在 blurb 记 critical（A05）。差异源于缺陷量级/上下文（相邻两段互换 vs 更大范围乱序），但 P0 时代 gold 未用统一量级锚点。
- **v1.3 粒度原则与 P0 gold 冲突**：v1.3"单个小缺陷→minor"修复了误报（A01 类），却把人类记 major/critical 的噪声/乱序降为 minor（A03–A05 severe_miss）。v1.2 曾与人类 major 一致。
- **结论**：不可通过回改旧 gold 或放宽阈值解决（P3 报告已定）。需**按缺陷量级细化严重度锚点**的预注册修订（P-B），其设计应由 A01–A05 的 anchor_revision_suggestion 驱动。

## 5. gold 覆盖缺口图（judge 标记 vs gold 覆盖）

| 缺陷类型 | judge 行为 | gold 现状 | 缺口 |
| --- | --- | --- | --- |
| 注入/噪声污染（interpreter） | v1.2 标 major | C01/C02 人类给 4/none（漏检） | gold 低估污染缺陷；需补标或裁决确认 |
| 标题空白保真 | v1.2 标 minor（双空格） | 人类/程序给 4（归一化） | 标题锚点空白政策未定义（A02） |
| 乱序严重度 | v1.2 major / v1.3 minor | 人类 minor↔critical 不一致 | 量级锚点缺失（A01/A05） |
| 单噪声块严重度 | v1.2 major / v1.3 minor | 人类 major | 粒度锚点冲突（A03/A04） |

## 6. P-A 交付与交接

- **自主完成（零调用）**：裁决 kit 构建器 tools/build_pa_adjudication_kit.py + 5 案卷 + findings 模板 + 本清单 + 单标注者声明（docs/P_A_SINGLE_ANNOTATOR_DECLARATION.md）。
- **需用户裁决**：A01–A05 的 verdict + anchor_revision_suggestion + note（填 pa_findings.json）。这是 P-A 完成与 P-B 启动的前置。
- **下游**：P-B 据 anchor_revision_suggestion 起草预注册修订（量级化严重度锚点 + 标题空白政策 + 长页分块证据）→ dev 护栏 → 一次性 v3 检验。
