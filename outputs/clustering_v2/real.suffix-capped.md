# DOM结构相似度原型

显式阈值：0.7；特征模式：suffix-capped。

固定特征设置：`{"mode": "suffix-capped", "path_scope": "suffix tag path", "multiplicity": "capped counts", "ignored": "all text, attributes, sibling indexes and head", "suffix_depth": 3, "count_cap": 3, "feature": "suffix-capped", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| python-appetite / python-interpreter | 0.4886 | True | False | False | real/real |
| python-appetite / iana | 0.0942 | False | False | False | real/real |
| python-appetite / gnu | 0.1420 | False | False | False | real/real |
| python-appetite / github | 0.0935 | False | False | False | real/real |
| python-appetite / nasa | 0.1231 | False | False | False | real/real |
| python-appetite / mdn | 0.0807 | False | False | False | real/real |
| python-appetite / python-introduction | 0.4481 | True | False | False | real/real |
| python-appetite / python-controlflow | 0.4266 | True | False | False | real/real |
| python-appetite / python-library-index | 0.7414 | True | True | True | real/real |
| python-appetite / python-search | 0.5556 | False | False | False | real/real |
| python-appetite / iana-abuse | 0.0949 | False | False | False | real/real |
| python-appetite / iana-whois | 0.1034 | False | False | False | real/real |
| python-interpreter / iana | 0.0676 | False | False | False | real/real |
| python-interpreter / gnu | 0.1435 | False | False | False | real/real |
| python-interpreter / github | 0.1149 | False | False | False | real/real |
| python-interpreter / nasa | 0.1313 | False | False | False | real/real |
| python-interpreter / mdn | 0.0964 | False | False | False | real/real |
| python-interpreter / python-introduction | 0.7617 | True | True | True | real/real |
| python-interpreter / python-controlflow | 0.7397 | True | True | True | real/real |
| python-interpreter / python-library-index | 0.5367 | True | False | False | real/real |
| python-interpreter / python-search | 0.3254 | False | False | False | real/real |
| python-interpreter / iana-abuse | 0.0680 | False | False | False | real/real |
| python-interpreter / iana-whois | 0.0748 | False | False | False | real/real |
| iana / gnu | 0.1348 | False | False | False | real/real |
| iana / github | 0.0681 | False | False | False | real/real |
| iana / nasa | 0.1205 | False | False | False | real/real |
| iana / mdn | 0.0780 | False | False | False | real/real |
| iana / python-introduction | 0.0556 | False | False | False | real/real |
| iana / python-controlflow | 0.0547 | False | False | False | real/real |
| iana / python-library-index | 0.0878 | False | False | False | real/real |
| iana / python-search | 0.1078 | False | False | False | real/real |
| iana / iana-abuse | 0.8475 | True | True | True | real/real |
| iana / iana-whois | 0.8030 | True | True | True | real/real |
| gnu / github | 0.1190 | False | False | False | real/real |
| gnu / nasa | 0.1712 | False | False | False | real/real |
| gnu / mdn | 0.0841 | False | False | False | real/real |
| gnu / python-introduction | 0.1704 | False | False | False | real/real |
| gnu / python-controlflow | 0.1228 | False | False | False | real/real |
| gnu / python-library-index | 0.1722 | False | False | False | real/real |
| gnu / python-search | 0.1164 | False | False | False | real/real |
| gnu / iana-abuse | 0.1277 | False | False | False | real/real |
| gnu / iana-whois | 0.1267 | False | False | False | real/real |
| github / nasa | 0.2591 | False | False | False | real/real |
| github / mdn | 0.1418 | False | False | False | real/real |
| github / python-introduction | 0.1233 | False | False | False | real/real |
| github / python-controlflow | 0.1173 | False | False | False | real/real |
| github / python-library-index | 0.1061 | False | False | False | real/real |
| github / python-search | 0.0675 | False | False | False | real/real |
| github / iana-abuse | 0.0585 | False | False | False | real/real |
| github / iana-whois | 0.0760 | False | False | False | real/real |
| nasa / mdn | 0.0905 | False | False | False | real/real |
| nasa / python-introduction | 0.1181 | False | False | False | real/real |
| nasa / python-controlflow | 0.1168 | False | False | False | real/real |
| nasa / python-library-index | 0.1353 | False | False | False | real/real |
| nasa / python-search | 0.1189 | False | False | False | real/real |
| nasa / iana-abuse | 0.1161 | False | False | False | real/real |
| nasa / iana-whois | 0.1354 | False | False | False | real/real |
| mdn / python-introduction | 0.1414 | False | False | False | real/real |
| mdn / python-controlflow | 0.1356 | False | False | False | real/real |
| mdn / python-library-index | 0.0762 | False | False | False | real/real |
| mdn / python-search | 0.0439 | False | False | False | real/real |
| mdn / iana-abuse | 0.0840 | False | False | False | real/real |
| mdn / iana-whois | 0.0733 | False | False | False | real/real |
| python-introduction / python-controlflow | 0.7247 | True | True | True | real/real |
| python-introduction / python-library-index | 0.4541 | True | False | False | real/real |
| python-introduction / python-search | 0.2570 | False | False | False | real/real |
| python-introduction / iana-abuse | 0.0558 | False | False | False | real/real |
| python-introduction / iana-whois | 0.0618 | False | False | False | real/real |
| python-controlflow / python-library-index | 0.4459 | True | False | False | real/real |
| python-controlflow / python-search | 0.2523 | False | False | False | real/real |
| python-controlflow / iana-abuse | 0.0549 | False | False | False | real/real |
| python-controlflow / iana-whois | 0.0608 | False | False | False | real/real |
| python-library-index / python-search | 0.5046 | False | False | False | real/real |
| python-library-index / iana-abuse | 0.0884 | False | False | False | real/real |
| python-library-index / iana-whois | 0.0968 | False | False | False | real/real |
| python-search / iana-abuse | 0.0980 | False | False | False | real/real |
| python-search / iana-whois | 0.1091 | False | False | False | real/real |
| iana-abuse / iana-whois | 0.7353 | True | True | True | real/real |

连通分量：[["github"], ["gnu"], ["iana", "iana-abuse", "iana-whois"], ["mdn"], ["nasa"], ["python-appetite", "python-library-index"], ["python-controlflow", "python-interpreter", "python-introduction"], ["python-search"]]

误聚页面对：0；漏聚页面对：6。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。
