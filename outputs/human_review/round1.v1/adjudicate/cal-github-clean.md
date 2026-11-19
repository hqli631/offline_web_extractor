# 裁决案卷 cal-github-clean

- split：frozen_test
- 触发原因：dim_score_mismatch:completeness, severity_sign_mismatch:completeness, decision_mismatch, severe_miss

## 决策对照

- 你(blind)：fail
- judge：uncertain
- silver：uncertain
- 程序：uncertain

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 3/minor | 4/none | 4 |
| cleanliness | 3/major | 3/minor | 4/minor | 4 |
| structure | 3/major | 3/minor | 4/none | 4 |
| title | 4/none | 4/none | 4/none | 4 |
| format | None/none | None/none | None/none | None |

## judge 理由与证据（现在可以看了）

### completeness — score=3 status=partial severity=minor
reason: All main article content is present, but the candidate includes non-article metadata (Tags, Written by) and has a minor parsing artifact in the list section.
- g:0 : We’re making GitHub Copilot
- p:22 : Tags:
- p:24 : Written by

### cleanliness — score=3 status=partial severity=minor
reason: Navigation was successfully excluded, but the candidate contains footer/metadata elements like 'Tags' and 'Written by', as well as HTML parsing artifacts ('<', 'ul>').
- s:0 : Changelog
- p:22 : Tags:
- p:10 : <
- p:11 : ul>

### structure — score=3 status=partial severity=minor
reason: Headings and lists are generally correct, but there are two stray paragraph blocks containing HTML tags ('<', 'ul>') before the actual list items, disrupting the flow.
- g:6 : The wait is over
- p:10 : <
- p:11 : ul>
- p:12 : Get AI-based coding suggestions

### title — score=4 status=partial severity=none
reason: Title matches the source and gold exactly.
- g:title : GitHub Copilot is generally available to all developers
- p:title : GitHub Copilot is generally available to all developers

### format — score=None status=not_applicable severity=none
reason: 

## 变异信息（盲评时隐藏）

类型：clean；参数：{}

## 你的盲评标签

{
 "blind_code": "B13",
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
   "score": 3,
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
 "overall_note": "将非正文的编辑信息提取出来，结构上还将<、ul>这类结构符号提取了出来，且是源截断",
 "case_id": "cal-github-clean"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
