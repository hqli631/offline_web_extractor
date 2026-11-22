# P2 人类 gold 接收摘要

- 标注者：hqli631（2026-11-21）
- 案例数：18（dev 6 / frozen_test v2 12）
- 决策分布：{"pass": 0, "uncertain": 18, "fail": 0}
- 完整性：freeze v5 全部文件哈希零漂移；案卷头部与重算元数据一致（max_source_chars=20000，与冻结批跑配置一致）。
- 本阶段不做 judge 对照：judge 批跑在 gold 封存之后执行，杜绝锚定。

## 局限

- 单一标注者（用户决定不设第二标注者），IAA 未测。
- 一致率不是准确率；人类 gold 也只是参考之一。
- source 截断案卷的 decision 按协议只能 uncertain/fail。
- Judge 分数仍不作为训练奖励。
