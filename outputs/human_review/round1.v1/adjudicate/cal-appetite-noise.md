# 裁决案卷 cal-appetite-noise

- split：development
- 触发原因：dim_score_mismatch:cleanliness, decision_mismatch, false_alarm

## 决策对照

- 你(blind)：uncertain
- judge：fail
- silver：fail
- 程序：fail

## 逐维对照（分数/严重度）

| 维度 | 你(blind) | judge | silver | 程序 |
| --- | --- | --- | --- | --- |
| completeness | 4/none | 4/none | 4/none | 4 |
| cleanliness | 3/minor | 2/major | 1/major | 1 |
| structure | 4/none | 4/none | 4/none | 4 |
| title | 4/none | 4/none | 4/none | 4 |
| format | None/none | None/none | None/none | None |

## judge 理由与证据（现在可以看了）

### completeness — score=4 status=scored severity=none
reason: All article paragraphs and list items from the source are present in the candidate.
- s:21 : 如果您的工作主要是用电脑完成的，总有一天您会想能不能自动执行一些任务。
- s:39 : 本教程的其他部分将利用各种示例，介绍 Python 语言、系统的功能

### cleanliness — score=2 status=scored severity=major
reason: Candidate contains a noise block with social sharing and ad text not present in the source article body.
- p:1 : 分享到：微信 微博 QQ空间 推荐阅读：广告推广内容
- g:0 : 如果您的工作主要是用电脑完成的，总有一天您会想能不能自动执行一些任务。

### structure — score=4 status=scored severity=none
reason: Article content order and list structure match the source; the noise block is an insertion but does not disrupt the relative order of valid article blocks.
- s:28 : Python 程序简洁、易读，通常比实现同种功能的 C、C++、Java 代码短很多，原因如下：
- s:29 : 高级数据类型允许在单一语句中表述复杂操作；

### title — score=4 status=scored severity=none
reason: Title matches the source heading including the chapter number.
- s:20 : 1. 课前甜点¶
- p:title : 1. 课前甜点

### format — score=None status=not_applicable severity=none
reason: No code or special formatting requirements for this article.

## 变异信息（盲评时隐藏）

类型：noise；参数：{"index": 1, "injected_text": "分享到：微信 微博 QQ空间 推荐阅读：广告推广内容 上一篇：没有了 下一篇：Python 简介"}

## 你的盲评标签

{
 "blind_code": "B04",
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
 "overall_note": "将非正文的推荐内容提取出来",
 "case_id": "cal-appetite-noise"
}

## 裁决任务

1. 对照上方证据，逐条决定：维持或修改你的 score/status/severity/decision。
2. 修改只发生在 human_labels.final.json 对应条目；写 adjudication_note 说明理由（维持也写一句）。
3. 完成后把该条目 confirmed 设为 true。所有案例（含无分歧案例）都必须 confirmed=true。
4. 注意：裁决以证据为准，不是向 judge 或 silver 靠拢；你与 judge 的持续分歧是有价值的校准发现。
