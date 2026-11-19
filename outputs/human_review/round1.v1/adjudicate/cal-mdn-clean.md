# 裁决案卷 cal-mdn-clean

- split：frozen_test
- 触发原因：dim_score_mismatch:structure, severity_sign_mismatch:structure

## 决策对照

- 你(blind)：uncertain
- judge：uncertain
- silver：uncertain
- 程序：uncertain

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 4/none | 4/minor | 4 |
| cleanliness | 4/none | 4/none | 4/minor | 4 |
| structure | 3/minor | 4/none | 4/none | 4 |
| title | 4/none | 4/none | 4/none | 4 |
| format | 3/none | None/none | 4/none | 4 |

## judge 理由与证据（现在可以看了）

### completeness — score=4 status=partial severity=none
reason: The candidate covers the entire article content from introduction to conclusion and references, matching the gold standard blocks.
- g:0 : 在本文中，我们将介绍最基础的 HTML 知识。
- g:139 : 参见
- s:html : <title>HTML 基础语法 - 学习 Web 开发 | MDN</title>

### cleanliness — score=4 status=partial severity=none
reason: Navigation menus, accessibility links, and other non-article elements present in the source are correctly excluded from the candidate output.
- s:0 : 跳转到主要内容
- s:2 : HTML: Markup language
- s:121 : 学习 Web 开发

### structure — score=4 status=partial severity=none
reason: Headings, lists, and code blocks follow the correct order and hierarchy as defined in the source and gold standard.
- g:2 : 什么是 HTML？
- g:10 : 剖析一个 HTML 元素
- g:86 : 剖析 HTML 文档

### title — score=4 status=partial severity=none
reason: The extracted title matches the article's main heading exactly.
- g:title : HTML 基础语法
- p:title : HTML 基础语法

### format — score=None status=not_applicable severity=none
reason: 

## 变异信息（盲评时隐藏）

类型：clean；参数：{}

## 你的盲评标签

{
 "blind_code": "B17",
 "split": "frozen_test",
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
   "score": 3,
   "status": "partial",
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
   "score": 3,
   "status": "partial",
   "severity": "none",
   "note": ""
  }
 },
 "overall_note": "存在原文的一段被分成多段的情况，且是源截断",
 "case_id": "cal-mdn-clean"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
