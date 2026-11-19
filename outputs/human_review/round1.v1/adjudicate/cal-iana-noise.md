# 裁决案卷 cal-iana-noise

- split：development
- 触发原因：dim_score_mismatch:cleanliness, dim_score_mismatch:structure, severity_sign_mismatch:structure

## 决策对照

- 你(blind)：fail
- judge：fail
- silver：fail
- 程序：uncertain

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 4/none | 4/none | None |
| cleanliness | 3/major | 2/major | 2/major | None |
| structure | 4/none | 3/minor | 4/none | None |
| title | 4/none | 4/none | 4/none | None |
| format | None/none | None/none | None/none | None |

## judge 理由与证据（现在可以看了）

### completeness — score=4 status=scored severity=none
reason: All meaningful article content including paragraphs and the 'Further Reading' list is captured.
- s:6 : A number of domains such as example.com
- s:7 : We provide a web service on the example domain hosts
- s:8 : Further Reading
- s:9 : IANA-managed Reserved Domains

### cleanliness — score=2 status=scored severity=major
reason: Candidate contains injected noise (p:1) that does not exist in the source HTML.
- p:1 : Share this article on Facebook and Twitter.
- s:html : <article class="hemmed sidenav">

### structure — score=3 status=scored severity=minor
reason: Article order is correct, but an extraneous paragraph block disrupts the flow between the two main text sections.
- s:6 : available for registration or transfer.
- s:7 : We provide a web service
- p:1 : Advertisement: buy now related content.

### title — score=4 status=scored severity=none
reason: Title matches the source H1 exactly.
- s:5 : Example Domains
- p:title : Example Domains

### format — score=None status=not_applicable severity=none
reason: 

## 变异信息（盲评时隐藏）

类型：noise；参数：{"index": 1, "injected_text": "Share this article on Facebook and Twitter. Subscribe to our newsletter! Advertisement: buy now related content."}

## 你的盲评标签

{
 "blind_code": "B12",
 "split": "development",
 "mode": "source_only",
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
 "overall_note": "将非正文的推荐内容提取出来，且无参考答案",
 "case_id": "cal-iana-noise"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
