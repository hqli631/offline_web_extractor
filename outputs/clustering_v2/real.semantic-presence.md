# DOM结构相似度原型

显式阈值：0.7；特征模式：semantic-presence。

固定特征设置：`{"mode": "semantic-presence", "path_scope": "body-relative full tag path", "multiplicity": "presence (one per distinct feature)", "ignored": "all text, class, id, URLs, sibling indexes and head", "semantic_roles": ["article", "banner", "complementary", "contentinfo", "main", "navigation", "region", "search"], "semantic_source": "main/nav/aside/article tags and bounded explicit ARIA roles", "feature": "semantic-presence", "skipped_tags": ["noscript", "script", "style", "template"], "metric": "multiset Jaccard", "threshold": 0.7, "clustering": "threshold-edge connected components"}`

| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |
| --- | ---: | --- | --- | --- | --- |
| python-appetite / python-interpreter | 0.4852 | True | False | False | real/real |
| python-appetite / iana | 0.0056 | False | False | False | real/real |
| python-appetite / gnu | 0.0532 | False | False | False | real/real |
| python-appetite / github | 0.0017 | False | False | False | real/real |
| python-appetite / nasa | 0.0150 | False | False | False | real/real |
| python-appetite / mdn | 0.0040 | False | False | False | real/real |
| python-appetite / python-introduction | 0.3966 | True | False | False | real/real |
| python-appetite / python-controlflow | 0.3372 | True | False | False | real/real |
| python-appetite / python-library-index | 0.7415 | True | True | True | real/real |
| python-appetite / python-search | 0.4143 | False | False | False | real/real |
| python-appetite / iana-abuse | 0.0057 | False | False | False | real/real |
| python-appetite / iana-whois | 0.0051 | False | False | False | real/real |
| python-interpreter / iana | 0.0035 | False | False | False | real/real |
| python-interpreter / gnu | 0.0464 | False | False | False | real/real |
| python-interpreter / github | 0.0014 | False | False | False | real/real |
| python-interpreter / nasa | 0.0118 | False | False | False | real/real |
| python-interpreter / mdn | 0.0033 | False | False | False | real/real |
| python-interpreter / python-introduction | 0.6444 | True | False | False | real/real |
| python-interpreter / python-controlflow | 0.5877 | True | False | False | real/real |
| python-interpreter / python-library-index | 0.4196 | True | False | False | real/real |
| python-interpreter / python-search | 0.2358 | False | False | False | real/real |
| python-interpreter / iana-abuse | 0.0036 | False | False | False | real/real |
| python-interpreter / iana-whois | 0.0033 | False | False | False | real/real |
| iana / gnu | 0.0047 | False | False | False | real/real |
| iana / github | 0.0018 | False | False | False | real/real |
| iana / nasa | 0.0332 | False | False | False | real/real |
| iana / mdn | 0.0068 | False | False | False | real/real |
| iana / python-introduction | 0.0029 | False | False | False | real/real |
| iana / python-controlflow | 0.0025 | False | False | False | real/real |
| iana / python-library-index | 0.0053 | False | False | False | real/real |
| iana / python-search | 0.0076 | False | False | False | real/real |
| iana / iana-abuse | 0.7742 | True | True | True | real/real |
| iana / iana-whois | 0.6750 | True | False | False | real/real |
| gnu / github | 0.0016 | False | False | False | real/real |
| gnu / nasa | 0.0186 | False | False | False | real/real |
| gnu / mdn | 0.0037 | False | False | False | real/real |
| gnu / python-introduction | 0.0399 | False | False | False | real/real |
| gnu / python-controlflow | 0.0356 | False | False | False | real/real |
| gnu / python-library-index | 0.0513 | False | False | False | real/real |
| gnu / python-search | 0.0457 | False | False | False | real/real |
| gnu / iana-abuse | 0.0049 | False | False | False | real/real |
| gnu / iana-whois | 0.0044 | False | False | False | real/real |
| github / nasa | 0.0039 | False | False | False | real/real |
| github / mdn | 0.0046 | False | False | False | real/real |
| github / python-introduction | 0.0013 | False | False | False | real/real |
| github / python-controlflow | 0.0012 | False | False | False | real/real |
| github / python-library-index | 0.0016 | False | False | False | real/real |
| github / python-search | 0.0018 | False | False | False | real/real |
| github / iana-abuse | 0.0019 | False | False | False | real/real |
| github / iana-whois | 0.0018 | False | False | False | real/real |
| nasa / mdn | 0.0060 | False | False | False | real/real |
| nasa / python-introduction | 0.0106 | False | False | False | real/real |
| nasa / python-controlflow | 0.0097 | False | False | False | real/real |
| nasa / python-library-index | 0.0146 | False | False | False | real/real |
| nasa / python-search | 0.0199 | False | False | False | real/real |
| nasa / iana-abuse | 0.0338 | False | False | False | real/real |
| nasa / iana-whois | 0.0315 | False | False | False | real/real |
| mdn / python-introduction | 0.0030 | False | False | False | real/real |
| mdn / python-controlflow | 0.0028 | False | False | False | real/real |
| mdn / python-library-index | 0.0039 | False | False | False | real/real |
| mdn / python-search | 0.0044 | False | False | False | real/real |
| mdn / iana-abuse | 0.0069 | False | False | False | real/real |
| mdn / iana-whois | 0.0066 | False | False | False | real/real |
| python-introduction / python-controlflow | 0.6364 | True | False | False | real/real |
| python-introduction / python-library-index | 0.3746 | True | False | False | real/real |
| python-introduction / python-search | 0.1895 | False | False | False | real/real |
| python-introduction / iana-abuse | 0.0029 | False | False | False | real/real |
| python-introduction / iana-whois | 0.0027 | False | False | False | real/real |
| python-controlflow / python-library-index | 0.3058 | True | False | False | real/real |
| python-controlflow / python-search | 0.1620 | False | False | False | real/real |
| python-controlflow / iana-abuse | 0.0026 | False | False | False | real/real |
| python-controlflow / iana-whois | 0.0024 | False | False | False | real/real |
| python-library-index / python-search | 0.3867 | False | False | False | real/real |
| python-library-index / iana-abuse | 0.0054 | False | False | False | real/real |
| python-library-index / iana-whois | 0.0048 | False | False | False | real/real |
| python-search / iana-abuse | 0.0079 | False | False | False | real/real |
| python-search / iana-whois | 0.0067 | False | False | False | real/real |
| iana-abuse / iana-whois | 0.6000 | True | False | False | real/real |

连通分量：[["github"], ["gnu"], ["iana", "iana-abuse"], ["iana-whois"], ["mdn"], ["nasa"], ["python-appetite", "python-library-index"], ["python-controlflow"], ["python-interpreter"], ["python-introduction"], ["python-search"]]

误聚页面对：0；漏聚页面对：11。

这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。
