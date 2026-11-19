# 实操04：保留列表结构

## 1. 先看实际结果

在 VS Code 终端运行：

```powershell
.\run.cmd extract samples/python_appetite_zh.html --output outputs/python_appetite_zh.structured.json --text-output outputs/python_appetite_zh.structured.md
```

打开生成的 md 文件，按 Ctrl+Shift+V 预览；搜索“高级数据类型允许”。三条文字应有列表标记，没有重复，其前后的普通段落保持原顺序。标题不含锚点 ¶。

预览排版修复说明：普通段落之间、段落与列表之间现在插入空行；相邻列表项仍使用单换行。.md 输出的标题使用 `# `，防止“1. 课前甜点”被误认为有序列表。若已打开旧结果，请重新运行命令生成后再预览，不要手动修改生成文件来掩盖渲染问题。

JSON 新增 blocks，表示有序的正文块，例如：

```json
{
  "kind": "list_item",
  "text": "高级数据类型允许在单一语句中表述复杂操作；",
  "list_type": "ul",
  "depth": 0,
  "ordinal": null
}
```

kind 是块类型；text 是不带项目符号的文字；list_type 区分 ul/ol；depth 从0开始表示嵌套层级；ordinal 是有序列表编号。普通段落的 kind 为 paragraph，其列表元数据为空或0。

这一页当前有16个块，其中13个普通段落、3个列表项。注意只比较正文区域，导航中的列表不应该出现。

## 2. 读取核心分支

打开 `src/webextractor/content_blocks.py`，找到 extract_blocks 内的 visit：

```python
if node.tag == "p":
    # 读取本段及其内联文字，生成 paragraph 块
    ...
    return
if node.tag in {"ul", "ol"}:
    visit_list(node, depth=0)
    return
```

节点遍历保持 DOM 顺序；识别到完整结构后，由对应函数负责读取它。列表处理完后 return，避免再次进入其中的 li/p 造成重复。不要用 `//p | //li` 后对每个节点 itertext：li 本身已经包含其 p，嵌套 li 还可能被父项重复吞入。

visit_list 逐项处理直接子 li，visit_item 保留内联文字并在遇到嵌套列表时递归。嵌套列表后的父项文字输出为 list_item_continuation，避免冒出一个虚假的新列表项。render_blocks 根据元数据给文字添加 `- ` 或数字序号。

extractor.py 的调用顺序：选择容器 → 删除噪声 → extract_blocks → render_blocks。旧 paragraphs 仍记录全部 p 文本，用于旧评测；body 现在由 blocks 生成。blocks 是结构化输出的主要入口。

## 3. 自己修改一个小样本

运行新建的实验样本，它有一个不带 p 的 li：

```powershell
.\run.cmd extract samples/list_lab.html --output outputs/list_lab.json --text-output outputs/list_lab.md
.\run.cmd evaluate samples/list_lab.html --expected samples/list_lab.expected.json --output outputs/list_lab.evaluation.json
```

打开 list_lab.json：paragraphs 只有3段，blocks 有4块。第二项没有 p，旧字段不包含它，而 blocks/body 会保留。

body_exact 仍比较旧的 p 序列，不能代表列表正确。新增 blocks_exact 比较块类型、顺序和元数据，rendered_body_exact 比较渲染正文。没有对应标准答案时，这两个指标为 null，表示未评分。字符指标同样仍基于旧 paragraphs。这个人工样例是结构检查案例，不是新网站泛化证明。

接着复制 `samples/list_lab.html` 为 `samples/list_lab.practice.html`，只修改副本，把 ul 的开始/结束标签一起改为 ol，并在 ol 上加 start="3"。运行：

补充：工程现在已提供上述练习副本，可直接运行下面命令；如想自己练习，可另取文件名，避免覆盖。终端每次只粘贴一条完整命令，不粘贴 `PS D:...>` 提示符；执行前可用 `Test-Path samples/list_lab.practice.html` 确认文件存在（应为 True）。缺失文件现在会给出简短提示而不是 Python 堆栈。

```powershell
.\run.cmd extract samples/list_lab.practice.html --output outputs/list_lab.practice.json --text-output outputs/list_lab.practice.md
```

预期两项分别显示3、4；JSON 里 list_type 为 ol，ordinal 为3、4。此时不要用未修改的 ul 标准答案给改后的样本评分。

## 4. 回归与边界

```powershell
.\run.cmd test
.\run.cmd evaluate --output outputs/python_blurb.structure_regression.json
```

当前支持普通 p、ul/ol、直接文本 li、li内p、基础嵌套列表以及有序列表 start/value/reversed。多段列表项输出续行；这是轻量文本表示，没有保留完整 HTML/CSS，也不是任意复杂 Markdown 的无损转换。尚未覆盖子标题、表格、代码块或任意 div 正文；候选评分仍以长度、p等初始特征为主，对只有列表的页面还未做专门调优。

本轮只需回报你改过副本后的两项序号，及 blocks 中这两项的 kind/list_type/ordinal。之后进入多页面评测，避免长期只在两个开发网页上修补。
