# DOM结构相似度原型

显式阈值：0.7；特征模式：full-counts。

固定特征设置：`{"mode": "full-counts", "path_scope": "body-relative full tag path", "multiplicity": "counts", "ignored": "all text, attributes, sibling indexes and head", "feature": "body-relative full tag-path multiset", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| python-appetite / python-interpreter | 0.3741 | True | False | False | real/real |
| python-appetite / iana | 0.0035 | False | False | False | real/real |
| python-appetite / gnu | 0.0413 | False | False | False | real/real |
| python-appetite / github | 0.0025 | False | False | False | real/real |
| python-appetite / nasa | 0.0067 | False | False | False | real/real |
| python-appetite / mdn | 0.0021 | False | False | False | real/real |
| python-appetite / python-introduction | 0.1036 | True | False | False | real/real |
| python-appetite / python-controlflow | 0.0489 | True | False | False | real/real |
| python-appetite / python-library-index | 0.1265 | True | False | False | real/real |
| python-appetite / python-search | 0.4718 | False | False | False | real/real |
| python-appetite / iana-abuse | 0.0033 | False | False | False | real/real |
| python-appetite / iana-whois | 0.0032 | False | False | False | real/real |
| python-interpreter / iana | 0.0019 | False | False | False | real/real |
| python-interpreter / gnu | 0.0397 | False | False | False | real/real |
| python-interpreter / github | 0.0021 | False | False | False | real/real |
| python-interpreter / nasa | 0.0065 | False | False | False | real/real |
| python-interpreter / mdn | 0.0019 | False | False | False | real/real |
| python-interpreter / python-introduction | 0.2076 | True | False | False | real/real |
| python-interpreter / python-controlflow | 0.1174 | True | False | False | real/real |
| python-interpreter / python-library-index | 0.1030 | True | False | False | real/real |
| python-interpreter / python-search | 0.2135 | False | False | False | real/real |
| python-interpreter / iana-abuse | 0.0019 | False | False | False | real/real |
| python-interpreter / iana-whois | 0.0018 | False | False | False | real/real |
| iana / gnu | 0.0017 | False | False | False | real/real |
| iana / github | 0.0009 | False | False | False | real/real |
| iana / nasa | 0.0061 | False | False | False | real/real |
| iana / mdn | 0.0017 | False | False | False | real/real |
| iana / python-introduction | 0.0006 | False | False | False | real/real |
| iana / python-controlflow | 0.0003 | False | False | False | real/real |
| iana / python-library-index | 0.0007 | False | False | False | real/real |
| iana / python-search | 0.0050 | False | False | False | real/real |
| iana / iana-abuse | 0.7244 | True | True | True | real/real |
| iana / iana-whois | 0.7037 | True | True | True | real/real |
| gnu / github | 0.0007 | False | False | False | real/real |
| gnu / nasa | 0.0111 | False | False | False | real/real |
| gnu / mdn | 0.0009 | False | False | False | real/real |
| gnu / python-introduction | 0.0169 | False | False | False | real/real |
| gnu / python-controlflow | 0.0133 | False | False | False | real/real |
| gnu / python-library-index | 0.0157 | False | False | False | real/real |
| gnu / python-search | 0.0187 | False | False | False | real/real |
| gnu / iana-abuse | 0.0016 | False | False | False | real/real |
| gnu / iana-whois | 0.0016 | False | False | False | real/real |
| github / nasa | 0.0013 | False | False | False | real/real |
| github / mdn | 0.0026 | False | False | False | real/real |
| github / python-introduction | 0.0011 | False | False | False | real/real |
| github / python-controlflow | 0.0007 | False | False | False | real/real |
| github / python-library-index | 0.0013 | False | False | False | real/real |
| github / python-search | 0.0027 | False | False | False | real/real |
| github / iana-abuse | 0.0009 | False | False | False | real/real |
| github / iana-whois | 0.0009 | False | False | False | real/real |
| nasa / mdn | 0.0016 | False | False | False | real/real |
| nasa / python-introduction | 0.0044 | False | False | False | real/real |
| nasa / python-controlflow | 0.0030 | False | False | False | real/real |
| nasa / python-library-index | 0.0046 | False | False | False | real/real |
| nasa / python-search | 0.0065 | False | False | False | real/real |
| nasa / iana-abuse | 0.0060 | False | False | False | real/real |
| nasa / iana-whois | 0.0060 | False | False | False | real/real |
| mdn / python-introduction | 0.0012 | False | False | False | real/real |
| mdn / python-controlflow | 0.0008 | False | False | False | real/real |
| mdn / python-library-index | 0.0014 | False | False | False | real/real |
| mdn / python-search | 0.0022 | False | False | False | real/real |
| mdn / iana-abuse | 0.0016 | False | False | False | real/real |
| mdn / iana-whois | 0.0016 | False | False | False | real/real |
| python-introduction / python-controlflow | 0.3526 | True | False | False | real/real |
| python-introduction / python-library-index | 0.0611 | True | False | False | real/real |
| python-introduction / python-search | 0.0566 | False | False | False | real/real |
| python-introduction / iana-abuse | 0.0006 | False | False | False | real/real |
| python-introduction / iana-whois | 0.0006 | False | False | False | real/real |
| python-controlflow / python-library-index | 0.0354 | True | False | False | real/real |
| python-controlflow / python-search | 0.0272 | False | False | False | real/real |
| python-controlflow / iana-abuse | 0.0003 | False | False | False | real/real |
| python-controlflow / iana-whois | 0.0003 | False | False | False | real/real |
| python-library-index / python-search | 0.0731 | False | False | False | real/real |
| python-library-index / iana-abuse | 0.0007 | False | False | False | real/real |
| python-library-index / iana-whois | 0.0007 | False | False | False | real/real |
| python-search / iana-abuse | 0.0045 | False | False | False | real/real |
| python-search / iana-whois | 0.0043 | False | False | False | real/real |
| iana-abuse / iana-whois | 0.6382 | True | False | True | real/real |

连通分量：[["github"], ["gnu"], ["iana", "iana-abuse", "iana-whois"], ["mdn"], ["nasa"], ["python-appetite"], ["python-controlflow"], ["python-interpreter"], ["python-introduction"], ["python-library-index"], ["python-search"]]

误聚页面对：0；漏聚页面对：10。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。

链式聚簇警告：{"component": ["iana", "iana-abuse", "iana-whois"], "below_threshold_pairs": [{"left": "iana-abuse", "right": "iana-whois", "score": 0.6381578947368421}]}
