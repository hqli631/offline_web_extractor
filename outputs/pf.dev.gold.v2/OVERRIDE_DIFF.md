# P-F dev gold 重裁决差异（审计视图，密封历史未改写）

批准：hqli631（2026-11-23）

| 案例 | 文件 | 维度 | 改前 | 改后 | decision |
| --- | --- | --- | --- | --- | --- |
| cal-appetite-missing_paragraph | dev.orig.gold.json | completeness | 3/minor | 2/major | uncertain -> fail |
| cal-interpreter-missing_paragraph | dev.p2.gold.json | completeness | 3/minor | 2/major | uncertain -> fail |
| cal-interpreter-reorder | dev.p2.gold.json | structure | 3/minor | 2/major | uncertain -> fail |

其余 15 例 dev gold 逐字段不变；上游 sealed/overlay 文件零改写（输入哈希复核通过）。
锚定循环披露：dev 轨道最多 6/18（overlay 3 + 本次改判 3）；v4 为独立泛化测试。
