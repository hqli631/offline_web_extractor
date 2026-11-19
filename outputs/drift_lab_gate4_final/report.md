# 固定规则跨页复用

固定 XPath：`//div[@role='main']`

规则指纹：`d0c753d9f1fd4852ef6240925cd508739211c43710d30bb59cb09100bbc95cdd`

| 页面 | 用途 | 匹配数 | 状态 | 标题 | 块数 |
| --- | --- | ---: | --- | --- | ---: |
| reference | reference | 1 | ok | Template drift laboratory | 3 |
| class-drift | transfer | 1 | ok | Template drift laboratory | 3 |
| role-drift | transfer | 0 | rule_no_match | — | 0 |
| duplicate-main | transfer | 2 | rule_ambiguous | — | 0 |
| content-moved | transfer | 1 | ok | Template drift laboratory | 2 |

容器唯一匹配只证明规则适用，不证明正文完整。quality为空表示没有完整参考；合成漂移与真实迁移必须分开报告。本工具不自动聚类、不回退、不逐页修规则。

reference 结构全匹配：True；块文本P/R：1.0/1.0。

class-drift 结构全匹配：True；块文本P/R：1.0/1.0。

content-moved 结构全匹配：False；块文本P/R：1.0/0.6666666666666666。
