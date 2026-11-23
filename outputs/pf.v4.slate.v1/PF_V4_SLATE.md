# P-F v4 候选 slate 草案（选项 B · 零采集 · 未密封）

> **DRAFT / 未批准**：仅为提案。未写 samples/、未冻结、未密封、零 judge 调用。
> 正式构建/盲评 kit/标注须在用户批准 slate 与预算后进行（docs/P_F_V14_PLAN.md）。

**独立性披露**：两页从未被 judge 评分，但同属 iana 模板族（经 example_domains 已曝光）
→ 同族同站转移测试，独立性显著弱于 v3 的新模板设计。
选项 A（新采集 2 个新模板短页）仍是推荐路线。

| 案例 | 模板 | 变异 | 源字节 | 截断 | prompt_chars |
| --- | --- | --- | ---: | --- | ---: |
| cal-ianaabuse-clean | iana-abuse | clean | 8550 | False | 30278 |
| cal-ianaabuse-missing_paragraph | iana-abuse | missing_paragraph | 8550 | False | 29993 |
| cal-ianaabuse-noise | iana-abuse | noise | 8550 | False | 30488 |
| cal-ianaabuse-duplicate | iana-abuse | duplicate | 8550 | False | 30563 |
| cal-ianaabuse-reorder | iana-abuse | reorder | 8550 | False | 30278 |
| cal-ianaabuse-instruction_interference | iana-abuse | instruction_interference | 8550 | False | 30459 |
| cal-ianawhois-clean | iana-whois | clean | 8717 | False | 30145 |
| cal-ianawhois-missing_paragraph | iana-whois | missing_paragraph | 8717 | False | 29908 |
| cal-ianawhois-noise | iana-whois | noise | 8717 | False | 30355 |
| cal-ianawhois-duplicate | iana-whois | duplicate | 8717 | False | 30382 |
| cal-ianawhois-reorder | iana-whois | reorder | 8717 | False | 30145 |
| cal-ianawhois-instruction_interference | iana-whois | instruction_interference | 8717 | False | 30326 |

变异覆盖：{"clean": 2, "missing_paragraph": 2, "noise": 2, "duplicate": 2, "reorder": 2, "instruction_interference": 2}

全部源 ≤20000 字符（BATCH_MAX_SOURCE_CHARS），无截断 → pass 可达。
silver 参考为 extract_html 程序输出（gold=None，provisional）；人类盲评 gold 才是权威。

