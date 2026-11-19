# 网页批量评测

开发、验证和合成样本分组统计；这是小样本诊断，不是总体准确率估计。

| 分组 | 总数 | 已评分 | 错误 | 结构已标注 | 结构全匹配 |
| --- | ---: | ---: | ---: | ---: | --- |
| development/real | 2 | 2 | 0 | 2 | 1.0 |
| development/synthetic | 1 | 1 | 0 | 1 | 1.0 |
| validation/real | 1 | 1 | 0 | 1 | 0.0 |

## python-blurb (development/real)

状态：ok；标题：True；旧p段落：True；结构：True；块文本精确率/召回率：1.0/1.0。

## python-appetite-zh (development/real)

状态：ok；标题：True；旧p段落：True；结构：True；块文本精确率/召回率：1.0/1.0。

## list-lab (development/synthetic)

状态：ok；标题：True；旧p段落：True；结构：True；块文本精确率/召回率：1.0/1.0。

## iana-example-domains (validation/real)

状态：ok；标题：True；旧p段落：True；结构：False；块文本精确率/召回率：0.8333333333333334/0.8333333333333334。

多提（1次）：

    Instructions and Guides

漏提（1次）：

    Further Reading
