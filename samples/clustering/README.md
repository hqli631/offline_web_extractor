# 网页聚簇开发样本补充

这些完整 HTML 快照只用于 DOM 相似度与模板聚簇开发。它们不是正文标准答案，也不参与正文准确率统计。来源文件记录 URL、采集时间、HTTP 状态、完整响应字节数和 SHA256；采集脚本只解析标题等来源信息，没有调用项目正文提取器。

## 先看源结构，再确定分组

分组以正文容器及页面骨架能否复用为依据。内容长短、段落数量和代码数量是需要承受的簇内差异，不能因为相似度低而临时改分组。

| 页面 | 原始 DOM 证据 | 最终开发分组 |
| --- | --- | --- |
| 既有 Python 课前甜点、解释器；新增 Python 速览、更多控制流工具 | `div.body[role=main] > section`，其后是清理浮动用的 `div.clearer`；章节内含标题、段落、嵌套章节和代码 | `sphinx-documentation` |
| Python 标准库索引 | 同一个 `div.body[role=main] > section` 容器；含 5 个段落、32 个 `ul`、277 个 `li` | `sphinx-documentation`，列表密集压力样本 |
| Python 搜索页 | 外层仍为 `div.body[role=main]`，但直接子节点为 `h1`、`noscript`、说明段落、搜索 `form`、`div#search-results`、`div.clearer`，没有文档正文 `section` | `sphinx-search`，同站不同页面类型负例 |
| 既有 IANA Example Domains；新增 Network Abuse Information、Using our WHOIS Server | `article.hemmed.sidenav > main + nav#sidenav`；`main` 的直接子节点均为 `ol.breadcrumb`、`h1`、`div.help-article-flow` | `iana-help` |

Python 标准库索引最初采集时的来源记录中，`proposed_manual_group` 是 `sphinx-library-index`。源结构复核后发现它与教程共享正文模板，因此最终 manifest 纠正为同组。保留最初来源记录是为了让判断过程可追溯；不能用它充当同站不同模板负例。

新增 Python 速览含 66 个段落、42 个 `pre`；更多控制流工具含 128 个段落、57 个 `pre`；既有课前甜点只有 16 个段落且无 `pre`。这组对照用于观察相似度是否被正文长度和代码重复次数主导。计数来自原始 HTML 独立解析，不代表正文提取数量或准确率。

## 使用方式与限制

扩展清单位于上级目录 `dom_similarity.expanded_development.json`，其中使用最终分组；历史 `dom_similarity.real_development.json` 保持原样。开发结果应记录 manifest 文件及其哈希、特征方式、阈值与失败的具体页面对。开发集上的改善不能作为独立验证成绩。

`collect.py` 不覆盖已有 HTML 和来源记录。首次 5 页采集报告保存在 `collection_results.json`；随后补充的搜索页具有单独的 `.source.json` 来源记录。此批样本未读取或运行 web.dev 留出验证页。
