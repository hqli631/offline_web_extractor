# 实操 03：修复自动识别与标题锚点

版本说明：本课描述修复候选和标题时的结果；列表格式后续已在 [实操04](04_list_blocks.md) 实现。下面的旧输出文件用于比较，不代表最新版本的列表表现。

你已核对中文网页的首尾段落与噪声边界；三条项目列表的文字都在，但被输出成普通段落。这说明文字完整性与格式正确性需要分别检查。

## 1. 列表为什么变成三个段落

在 VS Code 中打开 `samples/python_appetite_zh.html`，搜索 `高级数据类型允许`。周围是：

```html
<ul class="simple">
  <li><p>高级数据类型允许在单一语句中表述复杂操作；</p></li>
  <li><p>使用缩进，而不是括号实现代码块分组；</p></li>
  <li><p>无需预声明变量或参数。</p></li>
</ul>
```

ul 是无序列表，li 是列表项。页面的圆点由浏览器渲染，不属于 p 文本；itertext() 不会自动生成 Markdown 的 `- `。当前 `.//p` 保留这些文字，却没有保存它们属于列表的信息。此时改成 `/p` 会漏掉三个条目。下一步再添加结构化正文块，本轮保持 paragraphs/body 接口一致。

## 2. VS Code 中查看两处实际修复

打开 `src/webextractor/extractor.py`。在 `_candidate_nodes()` 中新增：

```python
"//article | //main | //*[@role='main'] | "
```

`<main>` 是标签，`role="main"` 是属性声明，之前的 `//main` 不会匹配 `<div role="main">`。现在先让它进入候选集合，再用已有评分流程。这里没有绑定这篇网页的 section id，但仍只是启发式规则，不能保证所有 role=main 区域纯净。

搜索 `normalize_title()`。它复制标题节点，删除 class token 为 headerlink 的 a 元素，再取文本。这样有针对性地去掉标题锚点，保留普通链接、强调文字和标题里合法出现的 ¶。不能全局用 replace('¶', '')，否则可能删除真实内容。

标题查找的各个分支都调用这个函数，包括标题位于候选外部的情况。源 HTML 快照不会被改写。

## 3. 不带手动 XPath 运行

```powershell
.\run.cmd extract samples/python_appetite_zh.html --show-candidates --output outputs/python_appetite_zh.fixed.json --text-output outputs/python_appetite_zh.fixed.txt
.\run.cmd test
.\run.cmd evaluate --output outputs/python_blurb.regression.json
```

在 VS Code 里对 `outputs/python_appetite_zh.baseline.json` 右键“选择以进行比较”，再对 fixed.json 右键“与已选项目进行比较”。旧文件如果仍是最初结果，status 从 no_candidate 变成 ok，标题变为“1. 课前甜点”，段落数为16。

旧 manual.txt 中可对照到 ¶；新 fixed.txt 中它应消失。三个列表条目仍是三个普通段落，这是已记录的格式缺陷，本轮不宣称解决。

默认 evaluate 的期望答案对应第一篇英文文章，用来检查旧样本是否退化。不要拿它评中文网页；中文页面目前只有你的边界检查与定向回归，还没有独立完整标准答案。

这一轮形成了可复用的修复流程：观察真实失败 → 找到缺失的结构信号 → 小范围改规则 → 用新样本验证 → 回归旧样本。
