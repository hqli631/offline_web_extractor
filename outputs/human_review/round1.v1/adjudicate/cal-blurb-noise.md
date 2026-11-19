# 裁决案卷 cal-blurb-noise

- split：development
- 触发原因：dim_score_mismatch:cleanliness, dim_score_mismatch:structure, severity_sign_mismatch:structure

## 决策对照

- 你(blind)：fail
- judge：fail
- silver：fail
- 程序：fail

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 4/none | 4/none | 4 |
| cleanliness | 3/major | 2/major | 1/major | 1 |
| structure | 4/none | 3/minor | 4/none | 4 |
| title | 4/none | 4/none | 4/none | 4 |
| format | None/none | None/none | None/none | None |

## judge 理由与证据（现在可以看了）

### completeness — score=4 status=partial severity=none
reason: All article paragraphs from the source are present in the candidate.
- s:77 : Python is an interpreted, object-oriented, high-level programming
- s:78 : Often, programmers fall in love with Python because of the
- s:79 : See also some comparisons between

### cleanliness — score=2 status=partial severity=major
reason: Candidate contains a paragraph with social sharing and advertisement text not present in the source article content.
- p:1 : Share this article on Facebook and Twitter. Subscribe to our newsletter!
- g:0 : Python is an interpreted, object-oriented, high-level programming
- g:1 : Often, programmers fall in love with Python because of the

### structure — score=3 status=partial severity=minor
reason: Article order matches source, but an extra non-article block interrupts the flow between the first and second paragraphs.
- s:77 : Python is an interpreted, object-oriented, high-level programming
- s:78 : Often, programmers fall in love with Python because of the
- p:1 : Share this article on Facebook and Twitter.

### title — score=4 status=partial severity=none
reason: Title matches the source article heading.
- s:75 : What is Python?  Executive Summary
- p:title : What is Python? Executive Summary

### format — score=None status=not_applicable severity=none
reason: 

## 变异信息（盲评时隐藏）

类型：noise；参数：{"index": 1, "injected_text": "Share this article on Facebook and Twitter. Subscribe to our newsletter! Advertisement: buy now related content."}

## 你的盲评标签

{
 "blind_code": "B09",
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
   "score": 3,
   "status": "scored",
   "severity": "major",
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
 "overall_note": "将非正文的推荐内容提取出来，且是源截断",
 "case_id": "cal-blurb-noise"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
