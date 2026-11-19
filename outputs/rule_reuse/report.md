# 固定规则跨页复用

固定 XPath：`//div[@role='main']`

规则指纹：`2befe90e5d3f3fe904ca8135d0e7dba26f511230eb6e53c864a7ceee11f52446`

| 页面 | 用途 | 匹配数 | 状态 | 标题 | 块数 |
| --- | --- | ---: | --- | --- | ---: |
| appetite-reference | reference | 1 | ok | 1. 课前甜点 | 16 |
| interpreter-transfer | transfer | 1 | ok | 2. 使用 Python 的解释器 | 32 |

容器匹配成功不代表全文正确。这是同一Sphinx文档模板的人工分组实验，没有实现自动聚类；transfer页面没有完整金标准，不报告泛化准确率。

interpreter-transfer 原始容器有 6 个 pre，本次输出 6 个代码块；数量对应不代表文字/缩进已自动评分。

interpreter-transfer 原始容器有 2 个 aside（可能含包装层），本次保留 1 个语义脚注块；普通aside仍清理。

interpreter-transfer 原始容器有 5 个h2–h6，本次输出 5 个带层级的子标题块。
