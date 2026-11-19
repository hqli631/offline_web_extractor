# 静态基线对比

同一HTML、同一Python环境；文本指标使用全部正文块。耗时为预热后串行中位数，不能推算工业吞吐。

| 页面 | 方法 | 状态 | 字符P | 字符R | 有序相似度 | 标题一致 | 中位耗时ms |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| mdn.candidate | rules | ok | 0.9999 | 1.0000 | 0.9933 | True | 49.814 |
| mdn.candidate | trafilatura | ok | 0.9946 | 0.9588 | 0.9695 | True | 65.972 |
| gnu.candidate | trafilatura | ok | 0.9908 | 1.0000 | 0.9955 | False | 29.320 |
| gnu.candidate | rules | ok | 1.0000 | 1.0000 | 1.0000 | True | 21.652 |
| nasa-voyager-news.candidate | rules | ok | 0.9413 | 1.0000 | 0.9624 | True | 87.963 |
| nasa-voyager-news.candidate | trafilatura | ok | 0.9528 | 0.9982 | 0.9493 | False | 69.921 |
| github-copilot-blog.candidate | trafilatura | ok | 0.9856 | 0.9443 | 0.8562 | True | 54.257 |
| github-copilot-blog.candidate | rules | ok | 0.9910 | 1.0000 | 0.9945 | True | 57.113 |
| w3c-link-text.candidate | rules | ok | 0.7089 | 1.0000 | 0.8434 | True | 5.606 |
| w3c-link-text.candidate | trafilatura | ok | 0.6951 | 1.0000 | 0.8293 | False | 7.411 |

## 比较边界

- 字符次数交集忽略顺序；有序相似度基于词/字元SequenceMatcher，属于诊断相似度，不是精确编辑距离或事实正确率。
- 代码空白、列表编号、表格分隔符和Markdown标记不参与文本比较；结构指标仅生产结果对自身协议计算，Trafilatura结构指标为空，不能冒充同构评测。
- 标题从正文投影剔除：仅移除与各方法自己预测标题相等的heading，不用标准答案修正预测。原始输出和移除计数保存在JSON。
- 统一协议选择和剩余标注差异见 manifest 与 docs/BASELINE_PROTOCOL.md。开发页结果不等于未见站点泛化。
