# P0 人工校准 · 盲评阶段索引

共 23 例（development 12 / frozen_test 11）。预计总耗时 1.5-2.5 小时，可分两次完成。

## 工作流
1. 按顺序阅读 `packets/<case_id>.md` 案卷（候选 + 参考答案 + 源证据 + 评分速查）。
2. 在 `human_labels.blind.json` 对应条目填写 decision 与五维 score/status/severity。
3. 先填 annotator（你的标识）与 annotation_date（YYYY-MM-DD）。
4. 全部填完后运行校验与一致性计算（见下），把输出发回给助手。

## 建议分会话
- 会话1（development，12 例）：cal-appetite-clean, cal-appetite-duplicate, cal-appetite-missing_paragraph, cal-appetite-noise, cal-appetite-reorder, cal-appetite-title_number, cal-blurb-clean, cal-blurb-missing_paragraph, cal-blurb-noise, cal-blurb-reorder, cal-iana-clean, cal-iana-noise
- 会话2（frozen_test，11 例）：cal-github-clean, cal-github-duplicate, cal-github-missing_paragraph, cal-github-noise, cal-mdn-clean, cal-mdn-code_indent, cal-mdn-instruction_interference, cal-mdn-missing_paragraph, cal-mdn-reorder, cal-w3clink-clean, cal-w3clink-instruction_interference

## 盲评纪律
- 填写前不要查看 outputs/ 下的 judge 批量结果、metrics、silver 标签或本报告以外的文档。
- 案卷已隐藏变异类型与所有机器分数；你的独立判断正是本阶段的价值。
- 拿不准就标 unscored/unknown 并写 note，不要猜。

## 填完后运行（项目根目录）
```
python -m tools.ingest_human_labels --stage blind --labels "D:\codex project\offline_web_extractor\outputs\human_review\blind.v1\human_labels.blind.json" --output outputs/human_review/round1.v1
```
校验失败会列出全部错误条目；修正后重跑（输出目录需换新名或先移走旧目录）。
