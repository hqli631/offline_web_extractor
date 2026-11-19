# 实操08：从真实漏提到代码块提取

进度更新：标题与脚注已在 [实操09](09_heading_footnotes.md) 恢复，最新解释器页为32块。下文28块指仅修复代码块时的版本，历史结果保存在report.before_notes.json与interpreter-transfer.before_notes.md。

你已观察到pre代码消失，普通段落之间仍有空行。本轮只修复代码块，不扩展三级标题或脚注策略。

## 1. 看修复后的真实网页

```powershell
.\run.cmd reuse
```

打开outputs/rule_reuse/interpreter-transfer.md，Ctrl+Shift+V预览。搜索shebang或cp1252，你选择的代码现在位于说明句后：

```text
#!/usr/bin/env python3
# -*- coding: cp1252 -*-
```

新页输出由22块变为28块，新增6个code块。数量只能证明覆盖情况；测试还逐个比较源pre与输出的文字，包括缩进和末尾换行。完整文章仍缺三级标题、脚注，所以不能宣称全文无遗漏。

## 2. 对照代码

打开src/webextractor/content_blocks.py，搜索code_text。普通段落为了压缩空白使用split/join；代码使用直接拼接：

```python
return "".join(node.itertext())
```

源码中的高亮span只是文字包装，itertext按顺序读取；HTML实体如&amp;gt;由解析器解码。不要用strip、split或自动dedent改变代码。空白pre不生成代码块，但非空代码块内的首尾换行、缩进和制表符会保留在blocks.text。读取网页代码不会执行它。

在visit中新增pre分支后return，防止继续遍历高亮标签并重复输出。新块kind为code，其text包含真实换行；JSON文件里会显示成\n，这是序列化表示，不表示代码只剩一行。

render_blocks在code前后留空行，用反引号围栏包裹文字。围栏长度大于代码中最长连续反引号，避免正文里的三个反引号提前关闭代码块。关闭围栏前若缺换行，仅在渲染时补一个，blocks.text保持原样。不猜测编程语言，因此代码块预览不保证有语法高亮。

## 3. 亲手检查缩进

```powershell
.\run.cmd extract samples/code_lab.html --output outputs/code_lab.json --text-output outputs/code_lab.md
```

VS Code并排打开samples/code_lab.html与outputs/code_lab.md，检查：def行顶格，if行前4个空格，print行前8个空格，return前有一个空行。用“视图 → 呈现空白字符”帮助检查；只在源码编辑器查看空格，不靠预览视觉估计。

可以修改这个实验样本中的print内容并重新运行，确认只改变代码块对应文字。不要修改已冻结快照，否则reuse会检查出哈希漂移。无需执行greet函数。

## 4. 回归与剩余问题

```powershell
.\run.cmd test
.\run.cmd batch
```

修复前快照输出保存在outputs/rule_reuse/interpreter-transfer.before_code.md，报告为report.before_code.json。新输出覆盖常用路径；这些旧文件只用于比较。参考页仍16块，新页28块，固定容器XPath及规则指纹不变，但正文提取器已更新。

transfer页已用于发现和修复代码块问题，属于开发迁移案例，不能再作为未见泛化评测。下轮继续处理h3和脚注，再换新网页验证。
