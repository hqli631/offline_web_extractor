# 实操 02：在 VS Code 里分析一次自动提取失败

进度说明：完成本课后继续 [实操03](03_semantic_main_and_title.md)。当前代码已修复 role=main 候选，下面描述的 no_candidate 是修复前的现象；不要用新版本覆盖已保存的 baseline 文件。

## 本次只完成定位，不急着修改抽取规则

已保存新样本 `samples/python_appetite_zh.html`，来源为 https://docs.python.org/zh-cn/3/tutorial/appetite.html 。这是 Python 官方中文教程的“课前甜点”，属于文档页面，布局与上一篇官网介绍不同。

自动抽取原始结果保存在 `outputs/python_appetite_zh.baseline.json`，状态是 `no_candidate`。保留这个文件，之后用不同名称保存手动结果，方便比较。

## 1. 在 VS Code 打开工程

文件 → 打开文件夹 → `D:\codex project\offline_web_extractor`。选择“终端 → 新建终端”，在集成终端中运行下方命令；使用 `.cmd` 入口不需要先激活 Python 环境。

```powershell
Set-Location 'D:\codex project\offline_web_extractor'
.\run.cmd extract samples/python_appetite_zh.html --show-candidates --output outputs/python_appetite_zh.current.json
```

按 Ctrl+P，输入 `outputs/python_appetite_zh.baseline.json`，查看 `status`、`candidates` 和 `paragraphs`。`no_candidate` 对应进程退出码 2，表示当前规则未覆盖该布局；不等于下载失败，也不等于网页没有正文。

## 2. 从标题向上找边界

按 Ctrl+P 打开 `samples/python_appetite_zh.html`，按 Ctrl+F 搜索 `<h1`。这里只查看，不要修改快照。浏览标题周围的开始标签、正文段落，以及文章结束后的侧栏。

在终端运行只读检查工具：

```powershell
.\run.cmd inspect samples/python_appetite_zh.html --xpath '//h1' --ancestors
```

它显示标题以及从近到远的祖先。重点比较 `tag`、`id`、`class`、`role` 和 `paragraph_count`，判断哪一层最贴合正文边界。`preview` 只显示前160字符，不能用它判断全文是否完整。这里是去噪前的原始节点统计，与抽取器的去噪后诊断有所不同。

不要直接选择最外层 body：它会包含导航、侧栏和页脚。也不要只选 h1：它没有正文段落。

## 3. 对照代码解释为何没有候选

打开 `src/webextractor/extractor.py`，搜索 `def _candidate_nodes`。把代码允许的标签、class 与快照里正文容器的实际属性逐项比较。

当前阶段顺序是：候选生成 → 评分 → 选择 → 抽取。如果候选列表是空的，评分函数不会有机会起作用，先不要调整评分权重。

## 4. 用自己选择的容器做手动验证

先检查你的容器 XPath 是否只匹配目标区域。把下面的“你选择的容器XPath”替换为实际表达式：

```powershell
.\run.cmd inspect samples/python_appetite_zh.html --xpath "你选择的容器XPath"
.\run.cmd extract samples/python_appetite_zh.html --xpath "你选择的容器XPath" --output outputs/python_appetite_zh.manual.json --text-output outputs/python_appetite_zh.manual.txt
```

在 VS Code 中打开生成的 `.txt`，与源网页对照首段、末段、是否混进导航、是否漏掉列表。标题末尾可能包含网页的锚点符号 `¶`，先记录，不要用修改标准答案的方式掩盖。当前程序只处理 p，列表项等结构需要单独检查。

本次不要运行上一课默认的 evaluate：默认标准答案对应另一篇文章，新网页尚未建立标准答案。

## 本次交付

回复你选的容器 XPath、inspect 的 match_count、手动正文中发现的一个具体问题，以及你认为自动候选规则缺了什么。下一步我们根据这个案例修改候选生成器，先复测当前网页，再回归上一课的网页。
