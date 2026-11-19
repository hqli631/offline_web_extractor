# 首轮错误诊断

只读取已保存报告；块文本比较不检查顺序或类型，差异数量不等于丢失的文字数量。

| 页面 | 标题一致 | 预测/标准块 | 文本精确率 | 文本召回率 | 结构全匹配 |
| --- | --- | --- | --- | --- | --- |
| mdn.candidate.first_evaluation | True | 156/141 | 0.8782 | 0.9716 | False |
| gnu.candidate.first_evaluation | False | 100/133 | 0.7900 | 0.5940 | False |
| nasa-voyager-news.candidate.first_evaluation | True | 35/20 | 0.5714 | 1.0000 | False |
| github-copilot-blog.candidate.first_evaluation | True | 32/20 | 0.5000 | 0.8000 | False |
| w3c-link-text.candidate.first_evaluation | False | 0/22 | 0.0000 | 0.0000 | False |

## mdn.candidate.first_evaluation

原始报告：outputs/mdn.candidate.first_evaluation.json

预测类型：{"paragraph": 64, "list_item": 45, "heading": 18, "code": 26, "list_item_continuation": 3}

标准类型：{"paragraph": 61, "table": 2, "heading": 17, "code": 25, "list_item": 36}

### 多提/拆分不一致（19块）

> 1次：此页面由社区从英文翻译而来。了解更多并加入 MDN Web Docs 社区。

> 1次：View in English Always switch to English

> 2次：概述：使用 HTML 构建 Web

> 2次：下一页

> 1次：HTML 元素的剖析：元素、开始标签、内容、结束标签、属性。

> 1次：HTML body 及其作为页面内容容器的用途。

> 1次：辨识空元素，以及其与其他元素的区别。

> 1次：明白为何需要在 HTML 文档顶部声明 doctype。了解其历史缘由，但现在它在某种程度上已成为历史遗留。

> 1次：掌握 HTML 标签正确嵌套的规则。

> 1次：<!doctype html>：文档类型声明（doctype）。在 HTML 早期（1991-1992 年），doctype 旨在作为一套规则的链接，HTML 页面必须遵循这些规则才能被认为是好的 HTML。过去的 doctype 看起来像这样：

> 1次：html

> 1次：<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> 

> 1次：最近，doctype 成为了一个历史遗留物，为了让其他一切正常工作而必须包含它。<!doctype html> 是算作有效 doctype 的最短字符序列。你只需要知道这些！

> 1次：在本地计算机上操作：

> 1次：备注：你也可以在我们的 GitHub 仓库中找到这个基础 HTML 模板。你可以复制这个文件，而不是自己创建。

> 1次：帮助改进 MDN

> 1次：此页面最后更新于 2025年11月10日，由 MDN 贡献者更新。


### 漏匹配/拆分不一致（4块）

> 1次：前提： | 安装基础软件，并掌握处理文件的基本知识。 学习成果： | HTML 元素的剖析：元素、开始标签、内容、结束标签、属性。 HTML body 及其作为页面内容容器的用途。 辨识空元素，以及其与其他元素的区别。 明白为何需要在 HTML 文档顶部声明 doctype。了解其历史缘由，但现在它在某种程度上已成为历史遗留。 掌握 HTML 标签正确嵌套的规则。

> 1次：<!doctype html>：文档类型声明（doctype）。在 HTML 早期（1991-1992 年），doctype 旨在作为一套规则的链接，HTML 页面必须遵循这些规则才能被认为是好的 HTML。过去的 doctype 看起来像这样： html<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> 最近，doctype 成为了一个历史遗留物，为了让其他一切正常工作而必须包含它。<!doctype html> 是算作有效 doctype 的最短字符序列。你只需要知道这些！

> 1次：在本地计算机上操作： 备注：你也可以在我们的 GitHub 仓库中找到这个基础 HTML 模板。你可以复制这个文件，而不是自己创建。

> 1次：字面字符 | 字符引用等效项 < | &lt; > | &gt; " | &quot; ' | &apos; & | &amp;


类型+文本交集：137块；仍不检查顺序、层级和列表编号。

## gnu.candidate.first_evaluation

原始报告：outputs/gnu.candidate.first_evaluation.json

预测类型：{"heading": 21, "paragraph": 52, "list_item": 27}

标准类型：{"paragraph": 51, "heading": 19, "list_item": 8, "definition_term": 27, "definition_description": 27, "footnote": 1}

### 多提/拆分不一致（21块）

> 1次：What is Free Software?

> 1次：Table of contents

> 1次：The Free Software Definition

> 1次：The four essential freedoms

> 1次：Free software can be commercial

> 1次：Clarifying the Boundary Between Free and Nonfree

> 1次：The freedom to run the program as you wish

> 1次：The freedom to study the source code and make changes

> 1次：The freedom to redistribute if you wish: basic requirements

> 1次：Copyleft

> 1次：Rules about packaging and distribution details

> 1次：Export regulations

> 1次：Legal considerations

> 1次：Contract-based licenses

> 1次：The Free Software Definition in Practice

> 1次：How we interpret these criteria

> 1次：Get help with free licenses

> 1次：Use the right words when talking about free software

> 1次：Beyond Software

> 1次：History

> 1次：Have a question about free software licensing not answered here? See our other licensing resources, and if necessary contact the FSF Compliance Lab at licensing@fsf.org.


### 漏匹配/拆分不一致（54块）

> 1次：Version 1.169

> 1次：Explain more clearly why the four freedoms must apply to commercial activity. Explain why the four freedoms imply the freedom not to run the program and the freedom to delete it, so there is no need to state those as separate requirements.

> 1次：Version 1.165

> 1次：Clarify that arbitrary annoyances in the code do not negate freedom 0, and that freedoms 1 and 3 enable users to remove them.

> 1次：Version 1.153

> 1次：Clarify that freedom to run the program means nothing stops you from making it run.

> 1次：Version 1.141

> 1次：Clarify which code needs to be free.

> 1次：Version 1.135

> 1次：Say each time that freedom 0 is the freedom to run the program as you wish.

> 1次：Version 1.134

> 1次：Freedom 0 is not a matter of the program's functionality.

> 1次：Version 1.131

> 1次：A free license may not require compliance with a nonfree license of another program.

> 1次：Version 1.129

> 1次：State explicitly that choice of law and choice of forum specifications are allowed. (This was always our policy.)

> 1次：Version 1.122

> 1次：An export control requirement is a real problem if the requirement is nontrivial; otherwise it is only a potential problem.

> 1次：Version 1.118

> 1次：Clarification: the issue is limits on your right to modify, not on what modifications you have made. And modifications are not limited to “improvements”

> 1次：Version 1.111

> 1次：Clarify 1.77 by saying that only retroactive restrictions are unacceptable. The copyright holders can always grant additional permission for use of the work by releasing the work in another way in parallel.

> 1次：Version 1.105

> 1次：Reflect, in the brief statement of freedom 1, the point (already stated in version 1.80) that it includes really using your modified version for your computing.

> 1次：Version 1.92

> 1次：Clarify that obfuscated code does not qualify as source code.

> 1次：Version 1.90

> 1次：Clarify that freedom 3 means the right to distribute copies of your own modified or improved version, not a right to participate in someone else's development project.

> 1次：Version 1.89

> 1次：Freedom 3 includes the right to release modified versions as free software.

> 1次：Version 1.80

> 1次：Freedom 1 must be practical, not just theoretical; i.e., no tivoization.

> 1次：Version 1.77

> 1次：Clarify that all retroactive changes to the license are unacceptable, even if it's not described as a complete replacement.

> 1次：Version 1.74

> 1次：Four clarifications of points not explicit enough, or stated in some places but not reflected everywhere:

> 1次：Version 1.57

> 1次：Add “Beyond Software” section.

> 1次：Version 1.46

> 1次：Clarify whose purpose is significant in the freedom to run the program for any purpose.

> 1次：Version 1.41

> 1次：Clarify wording about contract-based licenses.

> 1次：Version 1.40

> 1次：Explain that a free license must allow to you use other available free software to create your modifications.

> 1次：Version 1.39

> 1次：Note that it is acceptable for a license to require you to provide source for versions of the software you put into public use.

> 1次：Version 1.31

> 1次：Note that it is acceptable for a license to require you to identify yourself as the author of modifications. Other minor clarifications throughout the text.

> 1次：Version 1.23

> 1次：Address potential problems related to contract-based licenses.

> 1次：Version 1.16

> 1次：Explain why distribution of binaries is important.

> 1次：Version 1.11

> 1次：Note that a free license may require you to send a copy of versions you distribute to previous developers on request.


类型+文本交集：78块；仍不检查顺序、层级和列表编号。

## nasa-voyager-news.candidate.first_evaluation

原始报告：outputs/nasa-voyager-news.candidate.first_evaluation.json

预测类型：{"paragraph": 20, "heading": 4, "list_item": 11}

标准类型：{"paragraph": 15, "list_item": 5}

### 多提/拆分不一致（15块）

> 1次：3 min read

> 1次：Gerelle Q. Dodson

> 2次：NASA Headquarters

> 1次：-end-

> 1次：Abbey Interrante / Karen FoxHeadquarters, Washington202-358-1600abbey.a.interrante@nasa.gov / karen.c.fox@nasa.gov

> 1次：Josh SmoohaJet Propulsion Laboratory, Pasadena, Calif.626-298-4414josh.smooha@jpl.nasa.gov

> 1次：Share

> 1次：Details

> 1次：Related Terms

> 1次：Voyager 1

> 1次：Heliophysics

> 1次：Heliophysics Division

> 1次：Jet Propulsion Laboratory

> 1次：Voyager 2


### 漏匹配/拆分不一致（0块）


类型+文本交集：20块；仍不检查顺序、层级和列表编号。

## github-copilot-blog.candidate.first_evaluation

原始报告：outputs/github-copilot-blog.candidate.first_evaluation.json

预测类型：{"paragraph": 19, "list_item": 2, "heading": 11}

标准类型：{"paragraph": 13, "quote": 1, "heading": 3, "list_item": 3}

### 多提/拆分不一致（16块）

> 1次：Share:

> 1次：Tags:

> 1次：GitHub Copilot

> 1次：Written by

> 1次：Thomas Dohmke

> 1次：@ashtom

> 1次：Fascinated by software development since his childhood in Germany, Thomas Dohmke has built a career building tools to accelerate developer happiness. Previously, Thomas was the Chief Executive Officer of GitHub (2021-2025) where he oversaw the rise of the world’s most widely adopted AI developer tools—including the launches of GitHub Copilot, Copilot Workspace, and GitHub Models. Thomas has also been a celebrated TED speaker and holds a PhD in mechanical engineering from University of Glasgow, UK.

> 1次：Related posts

> 1次：GitHub availability report: October 2026

> 1次：In October, we experienced eight incidents that resulted in degraded performance across GitHub services.

> 1次：GitHub Universe 2026: Evolving every layer of the stack

> 1次：Today, we laid out our vision for GitHub as the most comprehensive, end-to-end software delivery system in the world.

> 1次：Octoverse: Commits, pushes, reach new highs in 2026 as developers build with agents

> 1次：See how a record year of growth reached every industry, every field, and every kind of builder in the 2026 Octoverse report.

> 1次：We do newsletters, too

> 1次：Discover tips, technical guides, and best practices in our biweekly newsletter just for devs.


### 漏匹配/拆分不一致（4块）

> 1次：GitHub Copilot enables developers to

> 1次：Get AI-based coding suggestions: Get code suggestions that match a project’s context and style conventions, and cycle through different options to decide what to accept, reject, or edit.

> 1次：Use your preferred environment: Integrate GitHub Copilot with popular editors, including Neovim, JetBrains IDEs, Visual Studio, and Visual Studio Code as an unobtrusive extension.

> 1次：Code confidently in unfamiliar territory: Code in new languages or try something new, and let GitHub Copilot suggest syntax and code in dozens of languages—so you can spend more time learning by doing.


类型+文本交集：15块；仍不检查顺序、层级和列表编号。

## w3c-link-text.candidate.first_evaluation

原始报告：outputs/w3c-link-text.candidate.first_evaluation.json

预测类型：{}

标准类型：{"heading": 3, "paragraph": 11, "list_item": 8}

### 多提/拆分不一致（0块）


### 漏匹配/拆分不一致（22块）

> 1次：What a link means

> 1次：When calling the user to action, use brief but meaningful link text that:

> 1次：provides some information when read out of context

> 1次：explains what the link offers

> 1次：doesn't talk about mechanics

> 1次：is not a verb phrase

> 1次：An example

> 1次：For instance, avoid the following sentence on your page:

> 1次：To download W3C's editor/browser Amaya, click here.

> 1次：or:

> 1次：To download Amaya, go to the Amaya Website and get the necessary software.

> 1次：Both of these sentences divulge too much of the mechanics of getting the Amaya software. If you want to call your reader to action, use something like:

> 1次：Get Amaya!

> 1次：Note that "get" is left out of the hypertext; we do not recommend putting verb phrases in link text. Thus, rather than:

> 1次：Tell me more about Amaya.

> 1次：You should write:

> 1次：Tell me more about Amaya: W3C's free editor/browser that lets you create HTML, SVG, and MathML documents.

> 1次：Further Reading

> 1次：section 6.1 Link text in the W3C HTML Techniques for Web Content Accessibility Guidelines 1.0, November 2000

> 1次：Avoid talking about mechanics and Make your (hyper)text readable in the Style Guide for online hypertext, by Tim Berners-Lee, 1992.

> 1次：Writing hypertext copy in What is good hypertext writing?, by Jutta Degener, April 1998. (See also: Dangerous words)

> 1次：Mail thread on the www-qa list, suggesting this tip.


类型+文本交集：0块；仍不检查顺序、层级和列表编号。
