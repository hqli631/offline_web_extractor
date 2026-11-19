# 裁决案卷 cal-mdn-missing_paragraph

- split：frozen_test
- 触发原因：judge_error

## judge 状态：拒绝（fail-closed）

错误：{"type": "ValueError", "stage": "validation", "detail": "Scoring needs source/reference evidence"}

judge 未给出可用评估。你的盲评标签将作为该例的人类期望；请确认你的 decision 与严重度判断，并写 adjudication_note。

## 变异信息（盲评时隐藏）

类型：missing_paragraph；参数：{"index": 0, "removed_excerpt": "在本文中，我们将介绍最基础的 HTML 知识。为了让你快速入门，本文将定义元素、属性以及你可能听过的所有其他重要术语，并解释它们在 HTML 中的作用。你将学习 HTML 元素的结构、一个典型 HTML 页面的结构，以及其他重要的基本语言特"}

## 你的盲评标签

{
 "blind_code": "B20",
 "split": "frozen_test",
 "mode": "with_gold",
 "decision": "fail",
 "dimensions": {
  "completeness": {
   "score": 3,
   "status": "partial",
   "severity": "major",
   "note": ""
  },
  "cleanliness": {
   "score": 4,
   "status": "partial",
   "severity": "none",
   "note": ""
  },
  "structure": {
   "score": 3,
   "status": "scored",
   "severity": "minor",
   "note": ""
  },
  "title": {
   "score": 4,
   "status": "partial",
   "severity": "none",
   "note": ""
  },
  "format": {
   "score": 4,
   "status": "partial",
   "severity": "none",
   "note": ""
  }
 },
 "overall_note": "原文的第一段正文未被提取出来，存在原文的一段被分成多段的情况，且是源截断",
 "case_id": "cal-mdn-missing_paragraph"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
