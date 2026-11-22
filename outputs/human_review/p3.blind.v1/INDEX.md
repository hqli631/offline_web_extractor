# P2 扩样 · 盲评索引

共 12 例（dev 扩展 0 / frozen_test v2 12）。中性编号 P01–P12，密封映射见 sealed_mapping.json（标注完成前勿查阅）。

## 工作流
1. 按顺序读 packets/P##.md（候选+参考答案+源证据+评分速查，不含 judge/silver 分数）。
2. 在 human_labels.blind.json 对应 blind_code 条目填 decision 与五维。
3. 先填 annotator 与 annotation_date。
4. 填完发回助手做校验与接收。

## IAA（第二标注者）
第二标注者独立复核至少 12 例（dev/test 混合），用相同案卷、独立填写另一份标签文件；助手用 compute_iaa.py 计算标注者间 kappa。

dev: 
frozen_test v2: P01, P02, P03, P04, P05, P06, P07, P08, P09, P10, P11, P12
