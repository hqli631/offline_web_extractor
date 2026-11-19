# DOM结构相似度原型

显式阈值：0.7；特征模式：full-presence。

固定特征设置：`{"mode": "full-presence", "path_scope": "body-relative full tag path", "multiplicity": "presence (one per distinct path)", "ignored": "all text, attributes, sibling indexes and head", "feature": "full-presence", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| python-appetite / python-interpreter | 0.4874 | True | False | False | real/real |
| python-appetite / iana | 0.0098 | False | False | False | real/real |
| python-appetite / gnu | 0.0894 | False | False | False | real/real |
| python-appetite / github | 0.0031 | False | False | False | real/real |
| python-appetite / nasa | 0.0231 | False | False | False | real/real |
| python-appetite / mdn | 0.0073 | False | False | False | real/real |
| python-appetite / python-introduction | 0.3986 | True | False | False | real/real |
| python-appetite / python-controlflow | 0.3391 | True | False | False | real/real |
| python-appetite / python-library-index | 0.7432 | True | True | True | real/real |
| python-appetite / python-search | 0.4429 | False | False | False | real/real |
| python-appetite / iana-abuse | 0.0101 | False | False | False | real/real |
| python-appetite / iana-whois | 0.0090 | False | False | False | real/real |
| python-appetite / python-datastructures | 0.4214 | True | False | False | real/real |
| python-interpreter / iana | 0.0065 | False | False | False | real/real |
| python-interpreter / gnu | 0.0809 | False | False | False | real/real |
| python-interpreter / github | 0.0027 | False | False | False | real/real |
| python-interpreter / nasa | 0.0192 | False | False | False | real/real |
| python-interpreter / mdn | 0.0061 | False | False | False | real/real |
| python-interpreter / python-introduction | 0.6456 | True | False | False | real/real |
| python-interpreter / python-controlflow | 0.5889 | True | False | False | real/real |
| python-interpreter / python-library-index | 0.4219 | True | False | False | real/real |
| python-interpreter / python-search | 0.2520 | False | False | False | real/real |
| python-interpreter / iana-abuse | 0.0066 | False | False | False | real/real |
| python-interpreter / iana-whois | 0.0061 | False | False | False | real/real |
| python-interpreter / python-datastructures | 0.7143 | True | True | True | real/real |
| iana / gnu | 0.0089 | False | False | False | real/real |
| iana / github | 0.0033 | False | False | False | real/real |
| iana / nasa | 0.0470 | False | False | False | real/real |
| iana / mdn | 0.0120 | False | False | False | real/real |
| iana / python-introduction | 0.0054 | False | False | False | real/real |
| iana / python-controlflow | 0.0047 | False | False | False | real/real |
| iana / python-library-index | 0.0093 | False | False | False | real/real |
| iana / python-search | 0.0127 | False | False | False | real/real |
| iana / iana-abuse | 0.8372 | True | True | True | real/real |
| iana / iana-whois | 0.7500 | True | True | True | real/real |
| iana / python-datastructures | 0.0056 | False | False | False | real/real |
| gnu / github | 0.0030 | False | False | False | real/real |
| gnu / nasa | 0.0299 | False | False | False | real/real |
| gnu / mdn | 0.0071 | False | False | False | real/real |
| gnu / python-introduction | 0.0690 | False | False | False | real/real |
| gnu / python-controlflow | 0.0611 | False | False | False | real/real |
| gnu / python-library-index | 0.0859 | False | False | False | real/real |
| gnu / python-search | 0.0571 | False | False | False | real/real |
| gnu / iana-abuse | 0.0092 | False | False | False | real/real |
| gnu / iana-whois | 0.0083 | False | False | False | real/real |
| gnu / python-datastructures | 0.0718 | False | False | False | real/real |
| github / nasa | 0.0043 | False | False | False | real/real |
| github / mdn | 0.0085 | False | False | False | real/real |
| github / python-introduction | 0.0025 | False | False | False | real/real |
| github / python-controlflow | 0.0023 | False | False | False | real/real |
| github / python-library-index | 0.0030 | False | False | False | real/real |
| github / python-search | 0.0033 | False | False | False | real/real |
| github / iana-abuse | 0.0033 | False | False | False | real/real |
| github / iana-whois | 0.0032 | False | False | False | real/real |
| github / python-datastructures | 0.0025 | False | False | False | real/real |
| nasa / mdn | 0.0097 | False | False | False | real/real |
| nasa / python-introduction | 0.0175 | False | False | False | real/real |
| nasa / python-controlflow | 0.0163 | False | False | False | real/real |
| nasa / python-library-index | 0.0226 | False | False | False | real/real |
| nasa / python-search | 0.0297 | False | False | False | real/real |
| nasa / iana-abuse | 0.0476 | False | False | False | real/real |
| nasa / iana-whois | 0.0453 | False | False | False | real/real |
| nasa / python-datastructures | 0.0179 | False | False | False | real/real |
| mdn / python-introduction | 0.0056 | False | False | False | real/real |
| mdn / python-controlflow | 0.0052 | False | False | False | real/real |
| mdn / python-library-index | 0.0072 | False | False | False | real/real |
| mdn / python-search | 0.0080 | False | False | False | real/real |
| mdn / iana-abuse | 0.0121 | False | False | False | real/real |
| mdn / iana-whois | 0.0115 | False | False | False | real/real |
| mdn / python-datastructures | 0.0057 | False | False | False | real/real |
| python-introduction / python-controlflow | 0.6373 | True | False | False | real/real |
| python-introduction / python-library-index | 0.3766 | True | False | False | real/real |
| python-introduction / python-search | 0.2026 | False | False | False | real/real |
| python-introduction / iana-abuse | 0.0055 | False | False | False | real/real |
| python-introduction / iana-whois | 0.0052 | False | False | False | real/real |
| python-introduction / python-datastructures | 0.6395 | True | False | False | real/real |
| python-controlflow / python-library-index | 0.3077 | True | False | False | real/real |
| python-controlflow / python-search | 0.1732 | False | False | False | real/real |
| python-controlflow / iana-abuse | 0.0048 | False | False | False | real/real |
| python-controlflow / iana-whois | 0.0045 | False | False | False | real/real |
| python-controlflow / python-datastructures | 0.6211 | True | False | False | real/real |
| python-library-index / python-search | 0.4133 | False | False | False | real/real |
| python-library-index / iana-abuse | 0.0096 | False | False | False | real/real |
| python-library-index / iana-whois | 0.0086 | False | False | False | real/real |
| python-library-index / python-datastructures | 0.3691 | True | False | False | real/real |
| python-search / iana-abuse | 0.0132 | False | False | False | real/real |
| python-search / iana-whois | 0.0114 | False | False | False | real/real |
| python-search / python-datastructures | 0.2138 | False | False | False | real/real |
| iana-abuse / iana-whois | 0.6923 | True | False | True | real/real |
| iana-abuse / python-datastructures | 0.0057 | False | False | False | real/real |
| iana-whois / python-datastructures | 0.0054 | False | False | False | real/real |

连通分量：[["github"], ["gnu"], ["iana", "iana-abuse", "iana-whois"], ["mdn"], ["nasa"], ["python-appetite", "python-library-index"], ["python-controlflow"], ["python-datastructures", "python-interpreter"], ["python-introduction"], ["python-search"]]

误聚页面对：0；漏聚页面对：13。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。

链式聚簇警告：{"component": ["iana", "iana-abuse", "iana-whois"], "below_threshold_pairs": [{"left": "iana-abuse", "right": "iana-whois", "score": 0.6923076923076923}]}
