# DOM结构相似度原型

显式阈值：0.7；特征模式：full-capped。

固定特征设置：`{"mode": "full-capped", "path_scope": "body-relative full tag path", "multiplicity": "capped counts", "ignored": "all text, attributes, sibling indexes and head", "count_cap": 3, "feature": "full-capped", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| python-appetite / python-interpreter | 0.4274 | True | False | False | real/real |
| python-appetite / iana | 0.0055 | False | False | False | real/real |
| python-appetite / gnu | 0.0970 | False | False | False | real/real |
| python-appetite / github | 0.0048 | False | False | False | real/real |
| python-appetite / nasa | 0.0254 | False | False | False | real/real |
| python-appetite / mdn | 0.0073 | False | False | False | real/real |
| python-appetite / python-introduction | 0.3574 | True | False | False | real/real |
| python-appetite / python-controlflow | 0.2668 | True | False | False | real/real |
| python-appetite / python-library-index | 0.7075 | True | True | True | real/real |
| python-appetite / python-search | 0.4444 | False | False | False | real/real |
| python-appetite / iana-abuse | 0.0055 | False | False | False | real/real |
| python-appetite / iana-whois | 0.0050 | False | False | False | real/real |
| python-interpreter / iana | 0.0033 | False | False | False | real/real |
| python-interpreter / gnu | 0.0791 | False | False | False | real/real |
| python-interpreter / github | 0.0040 | False | False | False | real/real |
| python-interpreter / nasa | 0.0205 | False | False | False | real/real |
| python-interpreter / mdn | 0.0060 | False | False | False | real/real |
| python-interpreter / python-introduction | 0.6341 | True | False | False | real/real |
| python-interpreter / python-controlflow | 0.5517 | True | False | False | real/real |
| python-interpreter / python-library-index | 0.3713 | True | False | False | real/real |
| python-interpreter / python-search | 0.2258 | False | False | False | real/real |
| python-interpreter / iana-abuse | 0.0033 | False | False | False | real/real |
| python-interpreter / iana-whois | 0.0031 | False | False | False | real/real |
| iana / gnu | 0.0047 | False | False | False | real/real |
| iana / github | 0.0017 | False | False | False | real/real |
| iana / nasa | 0.0280 | False | False | False | real/real |
| iana / mdn | 0.0060 | False | False | False | real/real |
| iana / python-introduction | 0.0027 | False | False | False | real/real |
| iana / python-controlflow | 0.0022 | False | False | False | real/real |
| iana / python-library-index | 0.0050 | False | False | False | real/real |
| iana / python-search | 0.0075 | False | False | False | real/real |
| iana / iana-abuse | 0.8108 | True | True | True | real/real |
| iana / iana-whois | 0.6848 | True | False | False | real/real |
| gnu / github | 0.0015 | False | False | False | real/real |
| gnu / nasa | 0.0317 | False | False | False | real/real |
| gnu / mdn | 0.0035 | False | False | False | real/real |
| gnu / python-introduction | 0.0676 | False | False | False | real/real |
| gnu / python-controlflow | 0.0593 | False | False | False | real/real |
| gnu / python-library-index | 0.0898 | False | False | False | real/real |
| gnu / python-search | 0.0500 | False | False | False | real/real |
| gnu / iana-abuse | 0.0048 | False | False | False | real/real |
| gnu / iana-whois | 0.0043 | False | False | False | real/real |
| github / nasa | 0.0044 | False | False | False | real/real |
| github / mdn | 0.0075 | False | False | False | real/real |
| github / python-introduction | 0.0037 | False | False | False | real/real |
| github / python-controlflow | 0.0034 | False | False | False | real/real |
| github / python-library-index | 0.0047 | False | False | False | real/real |
| github / python-search | 0.0053 | False | False | False | real/real |
| github / iana-abuse | 0.0018 | False | False | False | real/real |
| github / iana-whois | 0.0017 | False | False | False | real/real |
| nasa / mdn | 0.0072 | False | False | False | real/real |
| nasa / python-introduction | 0.0187 | False | False | False | real/real |
| nasa / python-controlflow | 0.0165 | False | False | False | real/real |
| nasa / python-library-index | 0.0245 | False | False | False | real/real |
| nasa / python-search | 0.0281 | False | False | False | real/real |
| nasa / iana-abuse | 0.0281 | False | False | False | real/real |
| nasa / iana-whois | 0.0269 | False | False | False | real/real |
| mdn / python-introduction | 0.0055 | False | False | False | real/real |
| mdn / python-controlflow | 0.0049 | False | False | False | real/real |
| mdn / python-library-index | 0.0071 | False | False | False | real/real |
| mdn / python-search | 0.0080 | False | False | False | real/real |
| mdn / iana-abuse | 0.0060 | False | False | False | real/real |
| mdn / iana-whois | 0.0058 | False | False | False | real/real |
| python-introduction / python-controlflow | 0.5682 | True | False | False | real/real |
| python-introduction / python-library-index | 0.3364 | True | False | False | real/real |
| python-introduction / python-search | 0.1818 | False | False | False | real/real |
| python-introduction / iana-abuse | 0.0028 | False | False | False | real/real |
| python-introduction / iana-whois | 0.0026 | False | False | False | real/real |
| python-controlflow / python-library-index | 0.2429 | True | False | False | real/real |
| python-controlflow / python-search | 0.1393 | False | False | False | real/real |
| python-controlflow / iana-abuse | 0.0022 | False | False | False | real/real |
| python-controlflow / iana-whois | 0.0021 | False | False | False | real/real |
| python-library-index / python-search | 0.3862 | False | False | False | real/real |
| python-library-index / iana-abuse | 0.0050 | False | False | False | real/real |
| python-library-index / iana-whois | 0.0045 | False | False | False | real/real |
| python-search / iana-abuse | 0.0076 | False | False | False | real/real |
| python-search / iana-whois | 0.0066 | False | False | False | real/real |
| iana-abuse / iana-whois | 0.6630 | True | False | False | real/real |

连通分量：[["github"], ["gnu"], ["iana", "iana-abuse"], ["iana-whois"], ["mdn"], ["nasa"], ["python-appetite", "python-library-index"], ["python-controlflow"], ["python-interpreter"], ["python-introduction"], ["python-search"]]

误聚页面对：0；漏聚页面对：11。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。
