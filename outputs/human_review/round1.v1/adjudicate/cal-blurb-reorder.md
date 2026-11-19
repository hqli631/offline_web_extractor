# 裁决案卷 cal-blurb-reorder

- split：development
- 触发原因：dim_score_mismatch:structure, dim_score_mismatch:title, severity_sign_mismatch:title

## 决策对照

- 你(blind)：fail
- judge：fail
- silver：fail
- 程序：fail

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 4/none | 4/none | 4 |
| cleanliness | 4/none | 4/none | 4/none | 4 |
| structure | 1/critical | 2/major | 1/major | 1 |
| title | 4/none | 3/minor | 4/none | 4 |
| format | None/none | None/none | None/none | None |

## judge 理由与证据（现在可以看了）

### completeness — score=4 status=partial severity=none
reason: All three article paragraphs are present in the candidate.
- s:77 : Python is an interpreted, object-oriented, high-level programming
- s:78 : Often, programmers fall in love with Python because of the
- s:79 : See also some comparisons between

### cleanliness — score=4 status=partial severity=none
reason: Navigation and footer content from source nodes s:1 through s:151 are excluded from the candidate blocks.
- s:16 : About
- s:82 : About
- s:151 : Copyright ©2001-2026.

### structure — score=2 status=partial severity=major
reason: The first two paragraphs are swapped relative to the source order found in s:77 and s:78.
- s:77 : Python is an interpreted, object-oriented, high-level programming
- s:78 : Often, programmers fall in love with Python because of the

### title — score=3 status=partial severity=minor
reason: The double space in the source title 'What is Python?  Executive Summary' was normalized to a single space.
- s:75 : What is Python?  Executive Summary

### format — score=None status=not_applicable severity=none
reason: No code or special block formatting requirements apply to this text-only article.

## 变异信息（盲评时隐藏）

类型：reorder；参数：{"indices": [0, 1]}

## 你的盲评标签

{
 "blind_code": "B10",
 "split": "development",
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
   "score": 4,
   "status": "partial",
   "severity": "none",
   "note": ""
  },
  "structure": {
   "score": 1,
   "status": "scored",
   "severity": "critical",
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
 "overall_note": "关键段落颠倒了，且是源截断",
 "case_id": "cal-blurb-reorder"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
