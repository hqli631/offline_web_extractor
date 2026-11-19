# 裁决案卷 cal-github-noise

- split：frozen_test
- 触发原因：judge_error

## judge 状态：拒绝（fail-closed）

错误：{"type": "ValueError", "stage": "validation", "detail": "Scoring needs source/reference evidence"}

judge 未给出可用评估。你的盲评标签将作为该例的人类期望；请确认你的 decision 与严重度判断，并写 adjudication_note。

## 变异信息（盲评时隐藏）

类型：noise；参数：{"index": 1, "injected_text": "Share this article on Facebook and Twitter. Subscribe to our newsletter! Advertisement: buy now related content."}

## 你的盲评标签

{
 "blind_code": "B16",
 "split": "frozen_test",
 "mode": "with_gold",
 "decision": "fail",
 "dimensions": {
  "completeness": {
   "score": 4,
   "status": "partial",
   "severity": "none",
   "note": ""
  },
  "cleanliness": {
   "score": 2,
   "status": "partial",
   "severity": "major",
   "note": ""
  },
  "structure": {
   "score": 3,
   "status": "partial",
   "severity": "major",
   "note": ""
  },
  "title": {
   "score": 4,
   "status": "partial",
   "severity": "none",
   "note": ""
  },
  "format": {
   "score": null,
   "status": "not_applicable",
   "severity": "none",
   "note": ""
  }
 },
 "overall_note": "将非正文的推荐广告和编辑信息提取出来，结构上还将<、ul>这类结构符号提取了出来，且是源截断",
 "case_id": "cal-github-noise"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
