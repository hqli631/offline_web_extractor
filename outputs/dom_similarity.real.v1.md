# DOM结构相似度原型

显式阈值：0.7；只用标签路径与次数，不用正文、class、id或URL。

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| python-appetite / python-interpreter | 0.3741 | True | False | False | real/real |
| python-appetite / iana | 0.0035 | False | False | False | real/real |
| python-appetite / gnu | 0.0413 | False | False | False | real/real |
| python-appetite / github | 0.0025 | False | False | False | real/real |
| python-appetite / nasa | 0.0067 | False | False | False | real/real |
| python-appetite / mdn | 0.0021 | False | False | False | real/real |
| python-interpreter / iana | 0.0019 | False | False | False | real/real |
| python-interpreter / gnu | 0.0397 | False | False | False | real/real |
| python-interpreter / github | 0.0021 | False | False | False | real/real |
| python-interpreter / nasa | 0.0065 | False | False | False | real/real |
| python-interpreter / mdn | 0.0019 | False | False | False | real/real |
| iana / gnu | 0.0017 | False | False | False | real/real |
| iana / github | 0.0009 | False | False | False | real/real |
| iana / nasa | 0.0061 | False | False | False | real/real |
| iana / mdn | 0.0017 | False | False | False | real/real |
| gnu / github | 0.0007 | False | False | False | real/real |
| gnu / nasa | 0.0111 | False | False | False | real/real |
| gnu / mdn | 0.0009 | False | False | False | real/real |
| github / nasa | 0.0013 | False | False | False | real/real |
| github / mdn | 0.0026 | False | False | False | real/real |
| nasa / mdn | 0.0016 | False | False | False | real/real |

连通分量：[["github"], ["gnu"], ["iana"], ["mdn"], ["nasa"], ["python-appetite"], ["python-interpreter"]]

误聚页面对：0；漏聚页面对：1。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。
