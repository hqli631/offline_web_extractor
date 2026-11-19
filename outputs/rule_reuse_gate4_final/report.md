# 固定规则跨页复用

固定 XPath：`//div[@role='main']`

规则指纹：`2befe90e5d3f3fe904ca8135d0e7dba26f511230eb6e53c864a7ceee11f52446`

| 页面 | 用途 | 匹配数 | 状态 | 标题 | 块数 |
| --- | --- | ---: | --- | --- | ---: |
| appetite-reference | reference | 1 | ok | 1. 课前甜点 | 16 |
| interpreter-transfer | transfer | 1 | ok | 2. 使用 Python 的解释器 | 32 |

容器唯一匹配只证明规则适用，不证明正文完整。quality为空表示没有完整参考；合成漂移与真实迁移必须分开报告。本工具不自动聚类、不回退、不逐页修规则。

interpreter-transfer 原始容器有 6 个 pre，本次输出 6 个代码块；数量对应不代表文字/缩进已自动评分。

interpreter-transfer 原始容器有 2 个 aside（可能含包装层），本次保留 1 个脚注块；部分正文旁注可保留，仍需核对边界。

interpreter-transfer 原始容器有 5 个h2–h6，本次输出 5 个带层级的子标题块。
