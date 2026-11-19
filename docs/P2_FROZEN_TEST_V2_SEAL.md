# P2 frozen_test v2 · 预注册封存记录

封存时间：2026-11-19（Asia/Shanghai）。**本测试集在 judge 评估前预注册封存；一次性评估，不得据此调 judge/协议/阈值。**
上游预注册：docs/P2_META_EVAL_PLAN.md（WP3）。原 frozen_test v1（11 例，mdn/github/w3clink）**永久封存**，P2 不再评估或调参。

## 封存内容

- 来源：P2 扩样新模板 **nasa-voyager-news.candidate**（en）+ **w3c_accessibility_intro_zh**（zh），整页隔离 split（同源不跨 split）。
- 案例数：**12**（每模板 6 变异：clean / missing_paragraph / noise / duplicate / reorder / instruction_interference）。
- 模式：with_gold（参考为清洁提取 assistant_silver，待 WP4 人类核验）；人类 gold 由 WP4 独立标注产生。
- judge 协议：v1.2.0（rubrics_judge.py sha256 edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891），rubrics v2.0.0。
- P2 manifest：samples/p2_manifest.json（canonical sha256 8cf928f14379454c99de902fe1ca12cbd53a1f4db07e04b1904a3875217c0d02）。
- 冻结：outputs/p2.freeze.v5.json（freeze_version 5，files 48，rebuild 零漂移）。

## 封存案例清单（12）

| case_id | template | candidate_sha256 | source_sha256 |
| --- | --- | --- | --- |
| cal-nasa-clean | nasa-voyager-news.candidate | afa0e768a77c2a94… | e7f443d226454244… |
| cal-nasa-missing_paragraph | nasa-voyager-news.candidate | 17aa8f9fd4461d51… | e7f443d226454244… |
| cal-nasa-noise | nasa-voyager-news.candidate | 9a7e4b6e3604f54f… | e7f443d226454244… |
| cal-nasa-duplicate | nasa-voyager-news.candidate | 9861452157d5762b… | e7f443d226454244… |
| cal-nasa-reorder | nasa-voyager-news.candidate | 02c2206f88e8d799… | e7f443d226454244… |
| cal-nasa-instruction_interference | nasa-voyager-news.candidate | 374bd01ab9cc500f… | e7f443d226454244… |
| cal-w3ca11y-clean | w3c_accessibility_intro_zh | 8caa1907361e7897… | 0de81af8fa582694… |
| cal-w3ca11y-missing_paragraph | w3c_accessibility_intro_zh | 245153f1c2d3aa40… | 0de81af8fa582694… |
| cal-w3ca11y-noise | w3c_accessibility_intro_zh | d70a5fbb7f88eb0b… | 0de81af8fa582694… |
| cal-w3ca11y-duplicate | w3c_accessibility_intro_zh | ea8853a708d3c4c4… | 0de81af8fa582694… |
| cal-w3ca11y-reorder | w3c_accessibility_intro_zh | 6419d9a3d45b0ca1… | 0de81af8fa582694… |
| cal-w3ca11y-instruction_interference | w3c_accessibility_intro_zh | 0a9fbfbb483b7433… | 0de81af8fa582694… |

## 纪律

1. 本 12 例仅用于 P2 泛化验收（WP6），judge v1.2 一次性评估，对照 WP4 人类 gold。
2. 不得据本测试集结果调 judge prompt/协议/阈值后重报为干净验收；如需迭代，另建预注册测试集。
3. dev 扩展（python_interpreter_zh，6 例）可调参；与本测试集整页隔离。
4. 泛化结论须与 dev 分开报告，附 bootstrap CI；一致率≠准确率。
