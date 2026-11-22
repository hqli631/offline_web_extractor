# P2 交付报告（DRAFT · 结果待填）

> 状态：**草稿**。人类 gold 待标注者补全 5 项（P04/P10/P16 severity、P03/P09/P15 injection_complied）并确认 18 处机械修正；模型调用预算（30 次 / ~563,700 tokens / 上限 650,000）待批准。批准前零调用。结果节以 PENDING 标记，禁止预填。

## 1. 目标与预注册

- 目标：judge v1.2.0（冻结 Rubrics v2 协议）在**新模板** frozen_test v2（12 例）上的一次性泛化检验 + dev 扩展（6 例）+ 同家族跨模型对照（qwen4-max × 原 dev12）+ bootstrap 统计强化。
- 预注册：docs/P2_META_EVAL_PLAN.md（2026-11-19 冻结；§8 修订记录 R1–R4，2026-11-22，阈值与 split 未变）。
- 封存纪律：frozen_test v1（11 例）**永久封存**，本阶段零接触；frozen_test v2 **一次性**评估，不调参；gold 先封存、judge 后运行（杜绝锚定）；judge 分数在 P3 门槛达标前**不作训练奖励**。

## 2. 证据对称性核验（零调用，已完成）

- 冻结批跑配置（freeze v4/v5 batch_config）：max_source_chars=**20000**、max_output_tokens=2200、timeout=90、model=qwen3.8-27b。案卷构建器使用同一上限 → **人类与 judge 证据对称**。
- 18 例源节点集合在 20k/40k 上限下逐项一致；案卷不渲染 s:html。dev6 源 25,771 字符、test12 源 283,702/51,194 字符，均 >20,000 → 双方均截断（test12 达 200 节点上限）。
- 协议确定性规则：截断 → scored 强制 partial → decision=uncertain（除非 severe→fail）。标注者 18 例全 uncertain **符合协议**。
- 完整性：freeze v5 全部文件哈希零漂移；案卷头部与重算元数据一致；kit 文件哈希校验通过（human_labels.blind.json 除外，标注者已填写）。
- 预检（--max-calls 0，零 API 调用）：outputs/p2.preflight.v1.json（18 例）、outputs/p2.cross.preflight.v1.json（原 dev12，qwen4-max）均通过源哈希/prompt 预算/provider 构造校验。

## 3. 可复现命令链（项目根目录；python =  bundled runtime）

```
# 0) 测试（零调用）
.\run.cmd test

# 1) 接收人类 gold（离线；校验+解封+封存；fail-closed）
python -m tools.ingest_p2_human_labels --labels outputs/human_review/p2.blind.v1/human_labels.blind.r2.json --output outputs/human_review/p2.gold.v1

# 2) judge v1.2 批跑 P2 18 例（冒烟 1 次 → resume 17 次；共 18 次调用）
python -m tools.run_rubrics_judge samples/p2_manifest.json --output outputs/p2.judge.v1.json --model qwen3.8-27b --max-source-chars 20000 --max-output-tokens 2200 --timeout 90 --max-calls 1
python -m tools.run_rubrics_judge samples/p2_manifest.json --output outputs/p2.judge.v2.json --model qwen3.8-27b --max-source-chars 20000 --max-output-tokens 2200 --timeout 90 --max-calls 17

# 3) 跨模型对照 qwen4-max × 原 dev12（冒烟 1 → resume 11；共 12 次调用）
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/p2.cross.v1.json --model qwen4-max --max-source-chars 20000 --max-output-tokens 2200 --timeout 90 --split development --max-calls 1
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/p2.cross.v2.json --model qwen4-max --max-source-chars 20000 --max-output-tokens 2200 --timeout 90 --split development --max-calls 11

# 4) 评分 + 泛化验收 + bootstrap CI（零调用）
python -m tools.score_p2_results --p2-batch outputs/p2.judge.v2.json --gold outputs/human_review/p2.gold.v1/human_gold.p2.blind.json --cross-batch outputs/p2.cross.v2.json --output outputs/p2.scored.v1
```

缓存键绑定 model+prompt hash：qwen4-max 与 qwen3.8-27b 缓存隔离；缓存文件不在 freeze 清单内。输出文件/目录拒绝覆盖（exit 3），重跑须换新名。

## 4. 关键哈希（SHA-256）

| 文件 | sha256 |
| --- | --- |
| samples/p2_manifest.json | f6a99ed5808a393cab9696d6fa9309fab248233a967a80df61b0be9a55c1e440 |
| outputs/p2.freeze.v5.json | 87cb35879e1eef872f0e71e7bb8468d815dd372c0c0e739555426ba076f2fe07 |
| outputs/rubrics_judge.node3.freeze.v4.json | aad20e177e8e0a16ca838b4accfbe83e7bc2a7c92159486433dd80fb906cddf8 |
| tools/ingest_p2_human_labels.py | 883b3c42462f6ad046b1c3148312ebfc243c3afacc065c661551fd73c76676cc |
| tools/score_p2_results.py | 387b2386eaf255e09d10d2b9144be6c028fb212cb462e5f79771fa4bde289fc4 |
| src/webextractor/rubrics_judge.py | edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891 |
| outputs/human_review/p2.blind.v1/kit_manifest.json | e553a3d577652b105c1d007ed9329e4a90815bea88555764a01dd1f80f5d473d |

## 5. 统计方法

- bootstrap：案例级重采样，B=10000，seed=20261119（tools/bootstrap_stats.py，P2 复用同一指标函数）。
- dev6 与 frozen_test v2 为**不相交案例集** → dev→test 决策一致率差异用**非配对**案例级 bootstrap 95% CI（预注册"paired"的操作化说明见 score_p2_results.py 文档字符串；阈值未变）。
- 泛化验收（预注册 §4）：test12 拒绝率 <10%；severe_miss ≤1；match/κ CI 如实报告；dev→test match 落差 CI 不含 0 且 >0.15 → 标记过拟合风险（诚实标记，非阈值改写）。
- κ 退化说明：人类 gold 决策若单类（全 uncertain），pe=1，Cohen κ 退化；**决策一致率为首要指标**，κ 仅参考。
- 机械伪差单列：截断案卷中 human status=scored vs judge 强制 partial 的维度计数（status_artifact），不计为语义分歧。

## 6. 结果（PENDING · 禁止预填）

- 人类 gold：PENDING（接收摘要、决策分布、injection 自证）
- judge v1.2 × P2 dev6：PENDING（match/κ/severe_miss/false_alarm/reject + CI）
- judge v1.2 × frozen_test v2（一次性）：PENDING（同上 + 泛化验收判定 + overfit_flag）
- qwen4-max × 原 dev12：PENDING（judge–judge 一致率、judge2–P0 human 一致率，描述性）
- 实际调用数 / tokens：PENDING（以批跑 JSON usage 为准）
- 测试日志：outputs/p2.ingest.engineering.tests.v1.log（401 OK）、outputs/p2.scoring.engineering.tests.v1.log（409 OK）；最终全量日志 PENDING

## 7. 如实局限

1. 单一标注者（hqli631），**IAA 未测**（用户决定取消第二标注者）；人类 gold 噪声上限无法量化。
2. **一致率 ≠ 准确率**；人类 gold 也只是参考之一。
3. qwen4-max 与 qwen3.8-27b **同属 Qwen 家族**：跨模型对照是描述性的，**不是跨家族**；家族特异性偏差无法排除。
4. dev 与泛化分开报告；frozen_test v2 一次性，未调参；frozen_test v1 永久封存零接触。
5. 全部新案例源截断（20k 上限）：decision 按协议只能 uncertain/fail，pass 类泛化**未检验**；clean 案例的"无缺陷"判断受截断证据限制。
6. silver 标签（assistant_silver）≠ human gold；新案例 expected.json 为程序参考提取。
7. Judge 分数仍不作训练奖励（P3 门槛未达）。
8. 小规模工程证据（41 例校准集），不支持生产规模或自然网页广泛准确率声明。

## 8. 批准与修订记录

- 预算批准：PENDING（R4：30 次 / ~563,700 tokens / 上限 650,000）。
- 标注补全与机械修正确认：PENDING（R3）。
- 修订记录：docs/P2_META_EVAL_PLAN.md §8 R1–R4。
