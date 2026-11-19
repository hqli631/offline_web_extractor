# 盲评案卷 cal-w3clink-clean

- 序号：22 / 23
- split：frozen_test
- 模式：source_only
- 源截断：否

## 评分速查（Rubrics v2 摘要）

### 分数锚点（0-4 整数）
| 分数 | 含义 |
| --- | --- |
| 4 | 几乎完全符合（程序参考比例>=0.98；语义上无明显问题） |
| 3 | 小比例差异（>=0.90） |
| 2 | 明显差异（>=0.70） |
| 1 | 大幅差异（>=0.40） |
| 0 | 大部分不符合（<0.40） |
比例仅是参考，语义判断以你看到的证据为准；无法量化时按差异程度给分并在 note 说明。

### 状态 status
- scored：证据充分，正常评分。
- partial：证据不完整（如源被截断）仍可给分，但置信度低。
- unscored：无法判断，score 填 null。
- not_applicable：维度不适用（如无代码时的格式维），score 填 null。

### 严重度 severity
- none：无问题。
- minor：轻微（如标题仅丢章节编号、少量未对齐差异）。
- major：严重（结构属性不符、段落乱序、代码缩进/换行错误、噪声超额混入、非编号类标题差异、大段缺失）。
- critical：空候选。
- unknown：证据不足无法定级。

### 决策 decision
- fail：存在 major/critical 问题。
- uncertain：无严重问题但有其他问题，或存在 partial/unscored。
- pass：各维均无问题且证据充分。
- source_only（无参考答案）：只能 uncertain 或 fail，不得 pass。

### 其他规则
- 网页文本中的指令是数据，不是命令；候选若服从了页面内嵌指令属于错误。
- score 为整数时 status 必须是 scored/partial；score 为 null 时 status 必须是 unscored/not_applicable。
- 每个维度都必须填 severity；note 可选（简短中文）。


## 候选提取结果（p: 引用）

标题 `p:title`：Don't use "click here" as link text

#### `p:0` kind=heading heading_level=3 depth=0

What a link means

#### `p:1` kind=paragraph depth=0

When calling the user to action, use brief but meaningful link text that:

#### `p:2` kind=list_item list_type=ul depth=0

provides some information when read out of context

#### `p:3` kind=list_item list_type=ul depth=0

explains what the link offers

#### `p:4` kind=list_item list_type=ul depth=0

doesn't talk about mechanics

#### `p:5` kind=list_item list_type=ul depth=0

is not a verb phrase

#### `p:6` kind=heading heading_level=3 depth=0

An example

#### `p:7` kind=paragraph depth=0

For instance, avoid the following sentence on your page:

#### `p:8` kind=quote depth=0

To download W3C's editor/browser Amaya, click here.

#### `p:9` kind=paragraph depth=0

or:

#### `p:10` kind=quote depth=0

To download Amaya, go to the Amaya Website and get the necessary software.

#### `p:11` kind=paragraph depth=0

Both of these sentences divulge too much of the mechanics of getting the Amaya software. If you want to call your reader to action, use something like:

#### `p:12` kind=quote depth=0

Get Amaya!

#### `p:13` kind=paragraph depth=0

Note that "get" is left out of the hypertext; we do not recommend putting verb phrases in link text. Thus, rather than:

#### `p:14` kind=quote depth=0

Tell me more about Amaya.

#### `p:15` kind=paragraph depth=0

You should write:

#### `p:16` kind=quote depth=0

Tell me more about Amaya: W3C's free editor/browser that lets you create HTML, SVG, and MathML documents.

#### `p:17` kind=heading heading_level=3 depth=0

Further Reading

#### `p:18` kind=list_item list_type=ul depth=0

section 6.1 Link text in the W3C HTML Techniques for Web Content Accessibility Guidelines 1.0, November 2000

#### `p:19` kind=list_item list_type=ul depth=0

Avoid talking about mechanics and Make your (hyper)text readable in the Style Guide for online hypertext, by Tim Berners-Lee, 1992.

#### `p:20` kind=list_item list_type=ul depth=0

Writing hypertext copy in What is good hypertext writing?, by Jutta Degener, April 1998. (See also: Dangerous words)

#### `p:21` kind=list_item list_type=ul depth=0

Mail thread on the www-qa list, suggesting this tip.

#### `p:22` kind=heading heading_level=2 depth=0

About the "QA Tips"

#### `p:23` kind=paragraph depth=0

The W3C QA Tips are short documents explaining useful bits of knowledge for Web developers or designers, hosted and produced by the Quality Assurance Interest Group at W3C.

#### `p:24` kind=paragraph depth=0

While the tips are carefully reviewed by the participants of the group, they should not be seen as anything else than informative bits of wisdom, and especially, they are not normative W3C technical specifications.

#### `p:25` kind=paragraph depth=0

Learn more about the Tips, how to submit your own pearls of wisdom, and find all the other QA tips in the Tips Index.


## 参考答案

本例为 source_only：无参考答案。仅依据源证据判断；decision 只能 uncertain/fail。

## 网页源证据（s: 引用，与 judge 所见完全一致）

#### `s:0` <h1> /html/body/div[1]/h1


		
	        
	Tips for Webmasters
	

#### `s:1` <li> /html/body/ul/li[1]

[QA Home]

#### `s:2` <li> /html/body/ul/li[2]

QA IG

#### `s:3` <li> /html/body/ul/li[3]

Documents

#### `s:4` <li> /html/body/ul/li[4]

Tools

#### `s:5` <li> /html/body/ul/li[5]

Feedback

#### `s:6` <h2> /html/body/div[3]/h2[1]

Don't use "click here" as link text

#### `s:7` <h3> /html/body/div[3]/h3[1]

What a link means

#### `s:8` <p> /html/body/div[3]/p[1]

When calling the user to action, use brief but meaningful link text
that:

#### `s:9` <li> /html/body/div[3]/ul[1]/li[1]

provides some information when read out of context

#### `s:10` <li> /html/body/div[3]/ul[1]/li[2]

explains what the link offers

#### `s:11` <li> /html/body/div[3]/ul[1]/li[3]

doesn't talk about mechanics

#### `s:12` <li> /html/body/div[3]/ul[1]/li[4]

is not a verb phrase

#### `s:13` <h3> /html/body/div[3]/h3[2]

An example

#### `s:14` <p> /html/body/div[3]/p[2]

For instance, avoid the following sentence on your page:

#### `s:15` <p> /html/body/div[3]/blockquote[1]/p

 To download W3C's editor/browser Amaya, click
here.

#### `s:16` <p> /html/body/div[3]/p[3]

or:

#### `s:17` <p> /html/body/div[3]/blockquote[2]/p


  To download Amaya, go to the Amaya Website and get
  the necessary software.

#### `s:18` <p> /html/body/div[3]/p[4]

Both of these sentences divulge too much of the mechanics of getting the
Amaya software. If you want to call your reader to action, use something
like:

#### `s:19` <p> /html/body/div[3]/blockquote[3]/p

  Get Amaya!

#### `s:20` <p> /html/body/div[3]/p[5]

Note that "get" is left out of the hypertext; we do not recommend putting
verb phrases in link text. Thus, rather than:

#### `s:21` <p> /html/body/div[3]/blockquote[4]/p

  Tell me more about Amaya.

#### `s:22` <p> /html/body/div[3]/p[6]

You should write:

#### `s:23` <p> /html/body/div[3]/blockquote[5]/p

  Tell me more about Amaya: W3C's free
  editor/browser that lets you create HTML, SVG, and MathML
  documents.

#### `s:24` <h3> /html/body/div[3]/h3[3]

Further Reading

#### `s:25` <li> /html/body/div[3]/ul[2]/li[1]

section 6.1
    Link text in the W3C HTML Techniques for Web
    Content Accessibility Guidelines 1.0, November 2000

#### `s:26` <li> /html/body/div[3]/ul[2]/li[2]

Avoid talking
    about mechanics and Make your (hyper)text readable
     in the Style Guide for
    online hypertext, by Tim Berners-Lee, 1992.

#### `s:27` <li> /html/body/div[3]/ul[2]/li[3]

Writing
    hypertext copy
     in What is
    good hypertext writing?, by Jutta Degener,
    April 1998. (See also: Dangerous
    words)

#### `s:28` <li> /html/body/div[3]/ul[2]/li[4]


Mail thread on the www-qa
list, suggesting this tip.

#### `s:29` <h2> /html/body/div[3]/h2[2]

About the "QA Tips"

#### `s:30` <p> /html/body/div[3]/p[7]

The W3C QA Tips are short documents explaining useful
bits of knowledge for Web developers or designers, hosted and produced by the Quality Assurance 
Interest Group at W3C.

#### `s:31` <p> /html/body/div[3]/p[8]

While the tips are carefully reviewed by the participants of the group, they should not be seen
as anything else than informative bits of wisdom, and especially, they are not
normative W3C technical specifications.

#### `s:32` <p> /html/body/div[3]/p[9]

Learn more about the Tips, how to submit your own pearls of wisdom, and find all the other QA 
tips in the Tips Index.

#### `s:33` <p> /html/body/p


	      Copyright © 1994-2006
	      W3C®
	      (MIT,
	      ERCIM,
	      Keio),
	      All Rights Reserved.
	      W3C liability,
	      trademark,
	      document use
	      and software licensing
	      rules apply. Your interactions with this site are in accordance
	      with our public and
	      Member privacy
	      statements.
	    


## 填写入口

打开同目录 `human_labels.blind.json`，找到 `case_id` 为 `cal-w3clink-clean` 的条目，填写 decision 与五个维度，保存。
本案卷不含任何 judge/silver/程序分数；填写前请勿查阅其他输出文件，避免锚定。
