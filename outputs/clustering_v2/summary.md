# 固定阈值DOM特征对照

阈值0.7；误聚/漏聚按最终连通分量统计；真实与合成分开。

| 语料 | 模式 | 页数 | 同组/异组页面对 | 误聚 | 漏聚 | 簇数 | 链式分量 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| real | full-counts | 13 | 13/65 | 0 | 10 | 11 | 1 |
| real | full-presence | 13 | 13/65 | 0 | 9 | 10 | 1 |
| real | full-capped | 13 | 13/65 | 0 | 11 | 11 | 0 |
| real | semantic-presence | 13 | 13/65 | 0 | 11 | 11 | 0 |
| real | suffix-capped | 13 | 13/65 | 0 | 6 | 8 | 0 |
| controlled | full-counts | 5 | 3/7 | 3 | 0 | 2 | 0 |
| controlled | full-presence | 5 | 3/7 | 7 | 0 | 1 | 0 |
| controlled | full-capped | 5 | 3/7 | 7 | 0 | 1 | 1 |
| controlled | semantic-presence | 5 | 3/7 | 5 | 2 | 2 | 0 |
| controlled | suffix-capped | 5 | 3/7 | 7 | 0 | 1 | 1 |

固定来源、人工分组及特征设置均见逐模式JSON；当前集合没有独立聚簇验证成绩。
