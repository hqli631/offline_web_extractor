# 实操07：固定规则跨页复用

版本说明：本课描述最初的22块输出。代码块已在 [实操08](08_pre_code.md) 修复，最新新页为28块；三级标题和脚注仍待处理。最初输出保存在outputs/rule_reuse/interpreter-transfer.before_code.md。

本次参考页是已检查的“课前甜点”，迁移页是同一Python中文教程的“使用Python的解释器”：https://docs.python.org/zh-cn/3/tutorial/interpreter.html 。新快照已保存，来源与哈希保存在旁边的source.json。

## 1. 运行固定规则

```powershell
.\run.cmd reuse
```

打开outputs/rule_reuse/report.md，Ctrl+Shift+V预览。当前参考页和迁移页都匹配1个容器，标题分别对应第1章和第2章，输出16块和22块。这是模板迁移检查，不是正文准确率评测。

## 2. 看规则配置，而不只看输出

打开samples/sphinx_reuse.json。规则只有一份：

```json
{
  "id": "sphinx-main-v1",
  "container_xpath": "//div[@role='main']",
  "frozen_from": "appetite-reference"
}
```

pages中reference页用于确定规则，transfer页只执行规则。XPath不包含第一页的section id，也不包含正文文字。规则指纹帮助确认本轮所有页面使用相同配置；不是自动生成、聚类或完整版本管理。

两页都使用document → documentwrapper → bodywrapper → div.body[role=main]布局，侧栏位于该容器之外，因此适合人工分为同一模板组。当前只是人工观察，尚未实现结构相似度算法。

打开src/webextractor/rule_reuse.py：query执行后先检查match_count。0个为rule_no_match，多个为rule_ambiguous，只有1个才执行提取。此命令不会自动改规则或回退到评分器；这样能如实暴露复用失败。

## 3. 在VS Code对照新页的缺失

左侧打开samples/python_interpreter_zh.html，右侧打开outputs/rule_reuse/interpreter-transfer.md。源网页可在浏览器查看。

搜索三类结构：

- h3：当前源容器内3个，包含“传入参数”“交互模式”“源文件的字符编码”，尚未加入正文块。
- pre：当前6个代码区域，原始换行、空格和代码语句尚未提取。只阅读p会让“如下所示”后面空缺。
- aside：当前2个，是正文脚注相关结构；现有去噪规则把aside全部删掉，引用可能仍在，脚注正文却不在。

报告原始标签计数只是检查线索，不是正式漏提指标。新页没有完整人工金标准，不应报告泛化准确率。status=ok仅表示输出了支持的正文块。

## 4. 亲手试一次页面特定规则失败

不要改默认配置；复制samples/sphinx_reuse.json为samples/sphinx_reuse.practice.json，只把container_xpath改为第一页的section id：

```xpath
//section[@id='whetting-your-appetite']
```

执行时使用独立输出目录：

```powershell
.\run.cmd reuse samples/sphinx_reuse.practice.json --output-dir outputs/rule_reuse_practice
```

预期参考页匹配1个，新页匹配0个并返回rule_no_match，命令退出码2。练习配置与frozen_from的旧说明需注明这是对照实验，不能将其当作原冻结规则。若文件未复制，请先在VS Code文件树复制；可用Test-Path检查存在后再执行。

## 5. 这与岗位方案的关系

本次只实现“人工选同模板 → 一份XPath固定 → 多页CPU执行 → 暴露失败”。后续Agent可以帮助提出和修复这份规则，但仍要验证跨页泛化、检测模板漂移并设计回退。CPU解析和执行仍有成本，复用降低的是逐页模型推理需求。

本次先回报：新页某一段“如下所示”后实际漏了什么，以及两种XPath在迁移页的match_count。下一步按这个案例补充代码块/标题支持和脚注边界，避免只提高容器命中率。
