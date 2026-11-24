# P_E_READINESS_REPORT — P-H 全周期 consolidated 交付（停止于 P-E 边界）

日期: 2026-11-24 (Asia/Shanghai)。状态: **H1-H4 交付完成，P-E 真实训练未启动**。
GitHub: github.com/hqli631/offline_web_extractor @ main。
里程碑: `bca19d8` (M1 计划+H2) -> `1c52adf` (M2 H3) -> `a82c7e0` (M3 H1+H4) -> 本报告提交。
预注册: docs/P_H_PRE_PE_PLAN.md (sha 74274566, 实现前冻结)。多标注者 IAA 按用户明确指示永久移除。

## 0. 目标逐项审计

| 要求 | 状态 | 证据 |
| --- | --- | --- |
| H1 修复闭环 v1.1 (<=20 调用/300k, 一次性, 披露 dev 循环) | 完成, GUARDED_LOOP_SIGNAL | ph.run.v1 + ph.score.v1; 总 18 调用/291,067 tokens |
| H2 LSH banding 召回修复 (零调用, 召回>=0.9 + CL 违规 0) | 完成, H2_HARD_CHECKS_PASS | ph.cluster.v1: 三层召回均 1.0, CL 违规 0 |
| H3 覆盖缺口修复 (零调用工程 + <=8 抓取) | 完成, H3_COVERAGE_FIX_CONFIRMED 3/4 | ph.coverage.eval.v3; 6 抓取/4 保留 |
| H4 GRPO 就绪 (零调用 dry-run + 环境审计) | 完成, GRPO_PLUMBING_READY | grpo.dryrun.v2 (7/7); 审计: torch/CUDA 缺失 |
| 每里程碑全量测试+秘密扫描+commit/push | 完成 | 784 -> 796 -> 822 tests OK; NONE; 全推送 |
| 冻结封存集零改写 / FAIL 不复测调参 / P-E 不启动 | 遵守 | v1-v4 封存未动; 冻结模块 sha 钉死; P-E 仅预注册草案 |

## 1. H2 — LSH banding 16x8 -> 32x4（零调用）
- 理由: s=0.7 候选概率 ~0.62 -> ~0.99985；精确 Jaccard + CL 0.7 验证层逐字节不变（精度保持）。
- 结果: 三层 LSH 正例召回 **1.0**（原 new 0.75 / all 0.867）；CL 违规 0；**簇分区与 v1 完全一致**
  （new 5 簇 recall 0.3125/ARI 0.336；既有 13 页 0.538/0.660 仍逐位复现 P-C 消融；all 0.414/0.552）。
- 诚实结论: 过分裂源于 0.7 阈值下的真实结构方差，**非** LSH 候选遗漏；banding 修复只消除概率性漏检。
- 循环性披露: 变更由 G2 FAIL 在同一语料驱动（dev）；独立确认推迟到未来新采集。

## 2. H3 — 站点私有容器覆盖（6 抓取/4 保留，零模型）
- 根因: openbsd innovations/security/goals 为**裸 body 经典布局**（全页无 div/section/td/main/article）。
- extract_html **逐字节冻结**；新 opt-in extractor_density.py: 密度候选含 //body，>=200 字符 + 链接比<=0.5，
  最深充分容器规则（后代保留>=90% 得分则淘汰祖先）。
- 首轮 ph.coverage.collect.v1 **NOT_CONFIRMED**（候选集缺 //body）保留为诚实负记录；dev 迭代披露；
  离线重评 ph.coverage.eval.v3 **CONFIRMED 3/4**: innovations 0->160 块、security 0->53、goals 0->14（标题恢复）；
  index 原本 ok 5 块（G1 拒绝是空标题标准，非覆盖缺口）。
- 集成边界: 冻结 rule_cache.fallback_extract 未接线（未来回路 opt-in；P-E 计划项）。

## 3. H1 — 修复闭环 v1.1（一次性，总 18 调用/291,067 tokens <= 20/300k）
- GATE-1 触发门控: 仅 fail / major+critical 缺陷 / silver recall<1.0 触发；drift 单独不再触发。
- GATE-2 保留守卫: baseline!=fail 时 repaired 须保留 >=0.9 baseline 块文本，否则拒绝保留 baseline（省 rejudge）。
- 冻结助手逐字节复用（reuse_pd2/validate_feedback/Pd2Guard/critic_feedback/run_agent/j141，sha 钉死含工具链）。
- 冒烟 3/47,261（机制验证；apache-var repair_failed 为一次性采样诚实结果）；正式前 v2 冻结余额 17/252,739（v1 零改写）。
- 正式 15 调用/243,806: **GUARDED_LOOP_SIGNAL**（硬检查全过）:
  回归率 **0**（G3 为 0.4；changes/index 回归源被 GATE-1 拦截）；retention 违规 0；泄漏/完整性/预算干净；
  GATE-1 削减 5 个冗余触发（faq/license/about/changes/index）。
- **诚实负结果**: apache howitworks+var repair_failed（rule_no_match/rule_ambiguous，G3 var 成功未复现 -> 采样方差）；
  本轮改善证据 **0**；index-var skipped_budget；paired n=1（security no_effect，reward Δ=0）。
- 解读: 门控**防住了伤害**（回归 0 + 成本削减），但**未证明修复能改善真实页**；改善信号仍待独立新集。
- 循环性披露: 门控由 G3 回归驱动（同语料 dev）；reward 资格仍限 P-F 受控合成范围。

## 4. H4 — GRPO 训练基础设施就绪（零调用）
- grpo_core.py: 纯 Python 确定性 GRPO 数学（组内 advantage 零均值/单位方差、std=0 退化旗标、
  clip 代理 + k3 KL、tabular softmax）；reward 经冻结 rubrics_reward v1.0.0 接口。
- 离线 dry-run（合成 mock judge 夹具，披露）: **GRPO_PLUMBING_READY** 7/7（含确定性、策略向高 reward 移动、
  最优动作 reward=1.0）；worst-two 夹具同 clip 至 -1.0（冻结映射正确行为，检查允许平局）。
  首轮 v1 NOT_READY 保留为检查规格 bug 记录（严格排序断言过严，非映射问题）。
- **环境审计（诚实）**: torch=False / CUDA=False / transformers=False / trl=False -> 本机真实训练**不可行**。
- 披露简化: tabular REINFORCE 式 logit 更新（非梯度反传）；per-sequence reward；非真实 LLM 训练。

## 5. 哈希链 (sha256 前 16 位)

| 工件 | sha256[:16] |
| --- | --- |
| docs/P_H_PRE_PE_PLAN.md | 742745660ae270e0 |
| docs/P_E_TRAINING_PLAN.md (草案, 未执行) | f3a7c81263b56aec |
| tools/run_ph_cluster.py | f0e987c6f005765c |
| tools/run_ph_repair.py | 7dc20e15b0eba44c |
| tools/score_ph.py | cd3d759a5153e365 |
| tools/collect_ph_coverage.py | 1a660a3d29d1cc67 |
| tools/run_grpo_dryrun.py | 651b1898bf3f7652 |
| src/webextractor/extractor_density.py | 982ac22f6dd54373 |
| src/webextractor/grpo_core.py | 4474973c93f70309 |
| outputs/ph.cluster.freeze.v1.json | a971244ee8d5162f |
| outputs/ph.cluster.v1.json | 3e17888a2dca81e9 |
| outputs/ph.coverage.collect.v1.json (首轮负记录) | c0e464db97ef7ed2 |
| outputs/ph.coverage.eval.v3.json | 82ebf2c20889251f |
| outputs/ph.repair.freeze.v1.json | ddc220ff7b4ca133 |
| outputs/ph.repair.freeze.v2.json (余额修正) | 06dbd1647a4e2ca6 |
| outputs/ph.smoke.v1.json | 8f528f1a3994b4fd |
| outputs/ph.run.v1.json | 8b7497ea69f259ec |
| outputs/ph.score.v1.json | aeec490bc2909a4a |
| outputs/grpo.dryrun.v2.json | 8654a7c60798128a |
| outputs/grpo.env_audit.v2.json | 3297769c5e35a874 |
| outputs/ph.suite.v3.log (822) | b80659e2752eca0c |

冻结模块 pin: v1.4.1 25c154b9 (base v1.2 edd841ef / v1.4 1d87cfb5); rubrics_v2 4fa60e02;
reward 映射 c08343b4; extract_html 冻结（27+ 快照零漂移测试钉死）。

## 6. 复现命令 (Windows PowerShell, 项目根目录)

```powershell
.\run.cmd test                                    # 全量 822 tests
python tools\run_ph_cluster.py --run --output outputs\ph.cluster.NEW.json   # H2 零调用 (需先 --freeze)
python tools\collect_ph_coverage.py --reeval --output outputs\ph.coverage.NEW.json  # H3 离线重评
python tools\run_grpo_dryrun.py --dry-out outputs\grpo.dryrun.NEW.json --audit-out outputs\grpo.env.NEW.json
python -m unittest tests.test_ph_repair tests.test_grpo_core tests.test_ph_cluster tests.test_ph_coverage -v
```
H1 正式运行为**一次性冻结**（ph.run.v1 已消耗，不可复测）；复现需新冻结+新预算批准。
python 用运行时自带解释器（run.cmd 自动定位）；输出拒绝覆盖，重跑换新文件名。

## 7. 预算账目 (本 goal 全程)

| 阶段 | 模型调用 | tokens | 网络抓取 |
| --- | --- | --- | --- |
| H2 聚簇 | 0 | 0 | 0 |
| H3 采集 | 0 | 0 | 6 (4 保留) |
| H1 冒烟 | 3 | 47,261 | 0 |
| H1 正式 | 15 | 243,806 | 0 |
| H4 dry-run | 0 | 0 | 0 |
| **合计** | **18** | **291,067** | **6** |

上限: H1 20 调用/300k（未超）；H3 <=8 抓取（未超）。1 次诚实 skipped_budget（index-var）。

## 8. 距 P-E 真实训练的剩余差距（详见 docs/P_E_TRAINING_PLAN.md）
1. **资源**: 需 CUDA GPU + torch/transformers/trl（本机审计全缺）或外部 API 训练服务。
2. **真实页 reward 有效性**: 仍 UNVALIDATED；初始训练限 P-F 受控合成范围，真实页课程需先独立验证。
3. **新封存 holdout**: v1-v4 已消耗，P-E 评测需新采集独立一次性封存集。
4. **密度后备集成**: 接 rule_cache 需新冻结版本链。
5. **judge 成本**: 每 rollout ~15k tokens，G=4-8 线性放大；试点 ~30M judge tokens + GPU 时需逐项批准。
6. **改善信号**: H1 防住伤害但改善证据 0；apache 修复采样方差大，需更稳健的规则生成或多次采样预算。

## 9. 停止声明
H1-H4 全部完成并逐项审计（§0）；consolidated 报告已交付；**P-E 真实训练未启动**（仅预注册草案）；
冻结封存集零改写；所有负结果（H3 首轮 NOT_CONFIRMED / H1 apache repair_failed 改善 0 / H4 首轮检查 bug /
环境不可行）如实保留。多标注者 IAA 按用户指示永久移除。**到此停止于 P-E 边界。**
