# DOM结构相似度原型

显式阈值：0.7；只用标签路径与次数，不用正文、class、id或URL。

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| reference / class-drift | 1.0000 | True | True | True | synthetic/synthetic |
| reference / role-drift | 1.0000 | True | True | True | synthetic/synthetic |
| reference / duplicate-main | 0.6429 | False | False | False | synthetic/synthetic |
| reference / content-moved | 0.7273 | False | True | True | synthetic/synthetic |
| class-drift / role-drift | 1.0000 | True | True | True | synthetic/synthetic |
| class-drift / duplicate-main | 0.6429 | False | False | False | synthetic/synthetic |
| class-drift / content-moved | 0.7273 | False | True | True | synthetic/synthetic |
| role-drift / duplicate-main | 0.6429 | False | False | False | synthetic/synthetic |
| role-drift / content-moved | 0.7273 | False | True | True | synthetic/synthetic |
| duplicate-main / content-moved | 0.5000 | False | False | False | synthetic/synthetic |

连通分量：[["class-drift", "content-moved", "reference", "role-drift"], ["duplicate-main"]]

误聚页面对：3；漏聚页面对：0。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。
