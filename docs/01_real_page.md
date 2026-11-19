# 实操 01：从真实网页到正文文件

本次网页：https://www.python.org/doc/essays/blurb/ 。选择它是因为文章短、公开、原始 HTML 中有正文，适合先跑通静态提取。以后再处理脚本加载的页面。

本教程使用 `.\run.cmd`，由它调用 Python 入口。即使 PowerShell 禁止执行 `.ps1`，也无需修改系统执行策略。请使用下面的 `--output`、`--xpath` 等参数，不要混用旧版 `.ps1` 的参数。

## 1. 先看网页和快照

在自己的浏览器打开上述地址，确认正文标题是 `What is Python? Executive Summary`。按 F12 → Elements，使用选取元素工具点击正文，向上查找容器。浏览器里可在 Console 输入 XPath 验证：

```javascript
$x("//article[@class='text']")
$x("//article[@class='text']/p")
```

两个表达式分别检查正文容器和段落。浏览器 DOM 会随网页更新，与本地快照未必完全相同；离线结果以快照为准。

项目中已下载 `samples/python_blurb.html`。也可自己下载另一份快照：

```powershell
Set-Location 'D:\codex project\offline_web_extractor'
Invoke-WebRequest -Uri 'https://www.python.org/doc/essays/blurb/' -OutFile 'samples/python_blurb.new.html' -TimeoutSec 30
```

保存成功后检查文件是不是目标文章，而非登录页或错误页。下载成功不代表抓到了正文。这个命令保存 HTTP 响应，不执行 JavaScript，也不会自动生成 `.source.json`。自己采集新样本时，请另外记录网址、下载时间和正文范围；项目已提供的快照附有来源记录。

打开本轮快照，搜索 `article class="text"`。结构是：

```text
section.main-content
└── article.text
    ├── header.article-header / h1
    ├── H1（页面源码重复放置了标题）
    ├── P（语言介绍）
    ├── P（开发与调试介绍）
    └── P（See also ...）
```

源码的 P 标签是大写，而且省略了结束标签。lxml 的 HTML 解析器会整理成树；XPath 使用小写 `p`。因此要区分源码字符串和解析后的节点。

本轮正文范围为上述三个段落，包含文章内最后一句 See also；排除两个标题副本、导航、左侧栏、PSF 捐赠与页脚。若改变任务对“相关阅读”的定义，先改标注口径，再改提取器。

## 2. 先强制使用自己确认的 XPath

```powershell
.\run.cmd extract samples/python_blurb.html --xpath "//article[@class='text']" --output outputs/python_blurb.manual.json --show-candidates
```

`--xpath` 接收容器节点，不接收 `/text()`。程序随后提取容器中的 `p`，每段用 `itertext()` 保留内部链接、强调标签中的文字。期望输出是标题和三个段落。

这就是 XPath 在实际项目里的用法：浏览器确认边界 → 对原始快照运行规则 → 检查正文是否完整、有没有噪声。无需把浏览器复制出的长路径原样当作规则。

## 3. 再运行自动候选选择

```powershell
.\run.cmd extract samples/python_blurb.html --show-candidates --output outputs/python_blurb.auto.json
```

打开 JSON，先看 `selected_candidate.xpath`、`paragraphs`，再看评分。这份快照当前只有一个被候选生成器找到的节点：`article.text`。它能说明链路跑通，尚不能证明评分函数能在多个易混淆候选之间正确选择。

可读结果保存为 `outputs/python_blurb.body.txt`。对照浏览器逐段读一遍，不只看 `status=ok`。

## 4. 跑一次评测

```powershell
.\run.cmd evaluate samples/python_blurb.html --expected samples/python_blurb.expected.json --output outputs/python_blurb.evaluation.json
```

标准答案根据已检查的文章原文和边界整理，并压缩空白。`title_exact` 比较标题，`body_exact` 同时比较段落内容、顺序和边界。字符精确率/召回率按字符次数交集计算，只作辅助诊断，无法判断句子被打乱等情况。

本轮样本已被查看和用于开发，属于开发样本，不能计入未见网页泛化评测。

## 5. 只读这几段代码

沿 `cli.main → extract_html → _candidate_nodes → _diagnostic → remove_noise → normalize_text` 阅读。先理解：手动 XPath 如何替换自动候选、为什么复制 DOM 后再删除噪声、为什么标题查找与正文容器选择分开。

`drop_tree()` 删除噪声但保留节点后面的 tail 文本，避免把正文一起删掉。候选标识按分隔后的词匹配，避免 `reading` 被 `ad` 子串误罚。清理规则仍然有限，不能保证任意广告都会被识别。

## 下一次动手任务

找一篇短中文新闻或博客，用上面的 `Invoke-WebRequest` 命令存为新文件；先运行自动提取，保留原始结果。再用浏览器找到正文容器，传入 `--xpath`。记录网址、下载时间、XPath、两个结果之间的差异；若返回 `no_candidate` 或 `empty_body`，记录失败即可。接下来围绕那个实际问题修改代码并做回归。
