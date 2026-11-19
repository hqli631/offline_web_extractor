# 裁决案卷 cal-appetite-duplicate

- split：development
- 触发原因：judge_error

## judge 状态：拒绝（fail-closed）

错误：{"type": "ValueError", "stage": "validation", "detail": "Scoring needs source/reference evidence"}

judge 未给出可用评估。你的盲评标签将作为该例的人类期望；请确认你的 decision 与严重度判断，并写 adjudication_note。

## 变异信息（盲评时隐藏）

类型：duplicate；参数：{"index": 0, "duplicated_excerpt": "如果您的工作主要是用电脑完成的，总有一天您会想能不能自动执行一些任务。比如，对大量文本文件执行查找、替换操作；利用复杂的规则重命名、重排序一堆照片文件；也可能您想编写一个小型数据库、或开发专用的图形界面应用，甚至是开发一个简单的游戏。"}

## 你的盲评标签

{
 "blind_code": "B02",
 "split": "development",
 "mode": "with_gold",
 "decision": "uncertain",
 "dimensions": {
  "completeness": {
   "score": 4,
   "status": "scored",
   "severity": "none",
   "note": ""
  },
  "cleanliness": {
   "score": 3,
   "status": "scored",
   "severity": "minor",
   "note": ""
  },
  "structure": {
   "score": 4,
   "status": "scored",
   "severity": "none",
   "note": ""
  },
  "title": {
   "score": 4,
   "status": "scored",
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
 "overall_note": "存在段落重复",
 "case_id": "cal-appetite-duplicate"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
