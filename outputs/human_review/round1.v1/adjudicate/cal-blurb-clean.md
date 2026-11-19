# 裁决案卷 cal-blurb-clean

- split：development
- 触发原因：dim_score_mismatch:title, severity_sign_mismatch:title

## 决策对照

- 你(blind)：uncertain
- judge：uncertain
- silver：uncertain
- 程序：uncertain

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 4/none | 4/none | 4 |
| cleanliness | 4/none | 4/none | 4/none | 4 |
| structure | 4/none | 4/none | 4/none | 4 |
| title | 4/none | 3/minor | 4/none | 4 |
| format | None/none | None/none | None/none | None |

## judge 理由与证据（现在可以看了）

### completeness — score=4 status=partial severity=none
reason: All article paragraphs are captured accurately.
- s:77 : Python is an interpreted, object-oriented, high-level programming
- s:78 : Often, programmers fall in love with Python because of the
- s:79 : See also some comparisons between

### cleanliness — score=4 status=partial severity=none
reason: Navigation and footer elements are excluded from the extraction.
- s:16 : About
- s:21 : Downloads
- s:80 : The PSF

### structure — score=4 status=partial severity=none
reason: Paragraph order matches the source document structure.
- s:77 : Python is an interpreted, object-oriented, high-level programming
- s:78 : Often, programmers fall in love with Python because of the
- s:79 : See also some comparisons between

### title — score=3 status=partial severity=minor
reason: Title omits the double space present in the source heading.
- s:75 : What is Python?  Executive Summary

### format — score=None status=not_applicable severity=none
reason: 

## 变异信息（盲评时隐藏）

类型：clean；参数：{}

## 你的盲评标签

{
 "blind_code": "B07",
 "split": "development",
 "mode": "with_gold",
 "decision": "uncertain",
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
   "score": 4,
   "status": "partial",
   "severity": "none",
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
 "overall_note": "源截断：是",
 "case_id": "cal-blurb-clean"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
