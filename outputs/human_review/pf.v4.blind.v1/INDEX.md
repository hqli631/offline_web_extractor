# P-F v4 正式 · 盲评索引（路线 A · 已批准 · 可标注）

**FORMAL**：2 个新采集未曝光模板 ×6 变异（采集溯源见 samples/pf_v4_*.html.source.json）。
独立性与 v3 同构（新模板新站）；选项 B iana 草案已作废保留。

共 12 例，中性编号 F01–F12，密封映射见 sealed_mapping.json（标注完成前勿查阅）。

## 工作流
1. 按顺序读 packets/F##.md（候选+程序参考+源证据，不含 judge/变异分数）。
2. 在 human_labels.blind.json 对应 blind_code 条目填 decision 与五维（按 INDEX 锚点）。
3. 先填 annotator 与 annotation_date。
4. 填完发回助手校验接收；gold 先密封，后运行 v1.4 judge（防锚定）。

单标注者（IAA 缺失沿用声明）；一致率≠准确率。
