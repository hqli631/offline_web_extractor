# P0 人工校准 · 盲评阶段索引

共 23 例（development 12 / frozen_test 11）。预计总耗时 1.5-2.5 小时，可分两次完成。

## 工作流
1. 按顺序阅读 `packets/<blind_code>.md` 案卷（候选 + 参考答案 + 源证据 + 评分速查）。
2. 在 `human_labels.blind.json` 对应条目填写 decision 与五维 score/status/severity。
3. 先填 annotator（你的标识）与 annotation_date（YYYY-MM-DD）。
4. 全部填完后运行校验与一致性计算（见下），把输出发回给助手。

## 建议分会话
- 会话1（development，12 例）：B01, B02, B03, B04, B05, B06, B07, B08, B09, B10, B11, B12
- 会话2（frozen_test，11 例）：B13, B14, B15, B16, B17, B18, B19, B20, B21, B22, B23

## 盲评纪律
- 填写前不要查看 outputs/ 下的 judge 批量结果、metrics、silver 标签或本报告以外的文档。
- 案卷以中性编号 B01-B23 标识，已隐藏真实案例名、变异类型与所有机器分数。
- `sealed_mapping.json` 是编号到案例名的密封映射：盲评阶段禁止打开（裁决阶段才需要）。
- 拿不准就标 unscored/unknown 并写 note，不要猜。

## 填完后运行（项目根目录）
```
python -m tools.ingest_human_labels --stage blind --labels "D:\codex project\offline_web_extractor\outputs\human_review\blind.v2\human_labels.blind.json" --output outputs/human_review/round1.v1
```
校验失败会列出全部错误条目；修正后重跑（输出目录需换新名或先移走旧目录）。
