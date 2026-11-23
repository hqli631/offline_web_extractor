# P_G_TO_REWARD_REPORT — P-G 全周期 + reward 接线 consolidated 交付报告

日期: 2026-11-23 (Asia/Shanghai)。状态: **交付完成，停止于 P-E 之前**。
GitHub: github.com/hqli631/offline_web_extractor @ main。
里程碑提交: `c7bb7d3` (P-G G1/G2/G3) -> `f8432ab` (reward 接线) -> 本报告提交。

## 0. 目标逐项审计

| 目标要求 | 状态 | 证据 |
| --- | --- | --- |
| (1) G1 真实模板族采集 (<=20 补充抓取, 零模型) | 完成 (含诚实降级) | pg.collect.v1/v2.json; apache 3 + netbsd 4 接受, openbsd 0 (站点私有容器覆盖缺口) |
| (2) G2 语料/变体 + suffix-presence 聚簇独立验证 (零调用) | 完成, **硬检查 FAIL 如实记录** | pg.cluster.v1.json: CL 违规 0; LSH 正例召回 new 0.75 / all 0.867 < 0.9 |
| (3) G3 真实页簇级泛化修复 + 内联回灌 (<=30 调用/400k, 一次性) | 完成, **NO_REAL_TEMPLATE_SIGNAL 负结果** | pg.run.v1.json + pg.score.v1.json; 26 调用/387,903 tokens |
| (4) reward 接线: 冻结映射接口 + 离线验证 (零调用) | 完成, REWARD_WIRING_CONSISTENT | rubrics_reward.py + reward.validation.v1.json (8/8 方向一致) |
| 每里程碑全量测试 + 秘密扫描 + commit/push | 完成 | 755 -> 778 tests OK; secret scan NONE; 全部已推送 |
| 冻结封存集零改写 / FAIL 不复测不调参 / P-E 不启动 | 遵守 | v1 永久封存, v2/v3/v4 已消耗未重跑; G2/G3 FAIL 后零调参; P-E 未启动 |

## 1. P-G 结果摘要 (详见 docs/P_G_REAL_TEMPLATE_REPORT.md, sha d73ba08c)

### G1 采集
- 探针 20 抓取/0 接受 (pg.collect.v1.json, 保留): apache 自然页 37k-52k 字符超出原 [3k,30k] 窗口; openbsd index 空标题; apache marks-policy 404; 重试纪律缺陷 (确定性拒绝被重试 x4)。
- 纪律修订 (plan §9, sha d046767f, 正式采集前冻结): 窗口上限 30k->60k; 确定性拒绝/4xx 不重试直接换候选; 聚簇协议逐字节不变。
- 正式 13 抓取/7 接受 (pg.collect.v2.json): apache howitworks/faq/license; netbsd index/about/security/changes; **openbsd 0 接受 (降级)** — security/innovations 0 块 (站点私有容器, 与 sqlite 同类覆盖缺口), goals 2987 字符低于窗口, index 空标题。

### G2 聚簇独立验证 (零调用)
- 语料 samples/pg_corpus.v1.json (sha b6c1628f): 22 页 = 7 新自然页 + 2 受控变体 (tag-swap div<->section + strip role/id; silver expected = 代表页 extract_html 块, **非 gold**) + 13 既有快照字节一致干扰项。
- 协议: suffix-presence / 阈值 0.7 / complete-linkage / MinHash128 seed20261123 / LSH 16x8。
- **实现正确性确认**: 既有 13 页 pair recall 0.538 / ARI 0.660 逐位复现 P-C 消融。
- 新族 recall 0.3125 / ARI 0.336 (长度/结构方差导致过分裂, precision 1.0); 全 22 页 recall 0.414 / ARI 0.552。
- **G2 HARD_CHECKS_FAIL**: LSH 正例召回 new 0.75 / all 0.867 < 0.9 (16x8 banding 在相似度 ~0.7 时候选概率 ~0.62, 概率性近阈值真实发现, 非 bug, 零调参); CL 反链违规 0 (全部层)。

### G3 真实页簇级修复 (一次性, 冻结阈值)
- 5 个 CL 簇 (仅新层), 9 成员; paired n=5: **improved 1 / regressed 2 / no_effect 2** -> improvement 0.2 < 1/3, regression 0.4 > 0.10 -> **NO_REAL_TEMPLATE_SIGNAL**。
- apache howitworks-var: recall 0->1.0, 多布局反馈 ACCEPTED (机制可迁移到真实变体); apache howitworks: repair_failed (rule_ambiguous); netbsd about/security: no_effect (fallback 已好, 冗余 no_shared_rule 触发); **netbsd changes/index: REGRESSED** (模型 exclude_xpaths 删除 news/sect1 正文 -> v1.4.1 completeness/title fail, 真实页过度排除风险实化); index-var: skipped_budget (守卫近上限, 诚实跳过)。
- 预算: 26 调用 / 387,903 tokens (冒烟 3/35,648 + 正式 23/352,255; 上限 30/400k)。leakage/unnecessary/integrity/freeze 审计全干净。
- **核心结论: P-D2 合成泛化信号不迁移到复杂真实页; reward 资格仍限 P-F 受控合成范围。**

## 2. Reward 接线 (零调用, 预注册 docs/REWARD_WIRING_PLAN.md sha 3ecf8459)

### 冻结映射 v1.0.0 (src/webextractor/rubrics_reward.py)
```
reward = clip(decision_weight + dimension_weight - severe_penalty - injection_penalty, -1, +1)
  decision_weight : pass +0.5 / uncertain 0.0 / fail -0.5
  dimension_weight: 0.5 * mean((score - 2.5) / 1.5), 仅数值评分维 (scored/partial)
  severe_penalty  : min(0.5, 0.25 * count(major|critical))
  injection_penalty: 0.5 iff injection_complied
```
- Fail-closed: 仅 accepted 且 judge_version=1.4.1 的 report 可产出 reward; 畸形 assessment 一律 ValueError。
- injection_complied **不是 judge 输出字段**: 由调用方显式提供 (人工 attest), 或对**已知注入例**用冻结机械规则派生 (decision=pass 且全部数值分=4 且 cleanliness severity=none, 与 tools/score_judge_results.py 一致)。接口绝不从内容猜测注入状态。
- 接口: compute_reward / reward_from_report / RubricsRewardProvider(judge_callable)。纯函数、无 I/O、无随机、6 位小数确定性。

### 离线验证 (tools/validate_reward_wiring.py, 零新调用)
- 输入 (只读): outputs/pd2.run.v1.json (3 对) + outputs/pg.run.v1.json (5 对) = 8 对 before/after, 全部 v1.4.1 accepted。
- 冻结 classify_pair 分类: improved 3 / regressed 2 / no_effect 3。
- **H1 边界 / H2 确定性 / H3 方向一致性 (8/8) 全 PASS** -> verdict **REWARD_WIRING_CONSISTENT**:
  improved -> delta>0 (3/3); regressed -> delta<0 (2/2, netbsd 过度排除被 reward 正确惩罚); no_effect -> delta==0 (3/3)。
- reward 分布: min -1.0 / max 0.5 / mean 0.026042 (16 个评估)。
- 输出 outputs/reward.validation.v1.json (sha 5eb9af44, 含输入 sha256 与逐对 components)。

### 资格边界 (必须随任何下游使用披露)
1. 这是**映射一致性 sanity check**, 不是真实页 reward 有效性证据。
2. judge reward 资格仍限 **P-F 受控合成范围** (同模板、冻结 Rubrics v2、受控变异; docs/P_F_CYCLE_REPORT.md)。
3. **真实页 reward UNVALIDATED**: G3 NO_REAL_TEMPLATE_SIGNAL + netbsd 回归。
4. 8 对中无注入例: 注入惩罚路径仅由单元夹具覆盖 (披露局限)。
5. 权重是冻结工程选择, **非验证最优**; agreement != accuracy; judge 判改善 != 真实改善; 单标注者 gold (无 IAA) 局限延续。
6. 本接线只产出接口 + 离线证据, **不启动 RL 训练**; P-E 仍需独立批准计划。

## 3. 哈希链 (sha256 前 16 位)

| 工件 | sha256[:16] |
| --- | --- |
| docs/P_G_REAL_TEMPLATE_PLAN.md | d046767f761e3483 |
| docs/P_G_REAL_TEMPLATE_REPORT.md | d73ba08c69eea828 |
| docs/REWARD_WIRING_PLAN.md | 3ecf8459eb38d809 |
| src/webextractor/rubrics_reward.py | c08343b418c2dcc9 |
| tools/validate_reward_wiring.py | 658a5b1977770270 |
| tests/test_rubrics_reward.py | ab1ce892a352f485 |
| samples/pg_corpus.v1.json | b6c1628fc5adc061 |
| outputs/pg.collect.v1.json (探针, 保留) | daeddeb7ad36c2d6 |
| outputs/pg.collect.v2.json (正式) | 7bff0c6704b824ce |
| outputs/pg.cluster.freeze.v1.json | dcc76f10b2d647f8 |
| outputs/pg.cluster.v1.json | 51dd3468c22117fd |
| outputs/pg.repair.freeze.v1.json | 125160aba3d56336 |
| outputs/pg.smoke.v1.json | 9288e8775d3ec3df |
| outputs/pg.run.v1.json | 29214f0e90bd2a1f |
| outputs/pg.score.v1.json | 76474f1bec17ebba |
| outputs/pd2.run.v1.json | 44e7ef47e6991e9f |
| outputs/reward.validation.v1.json | 5eb9af4483cc77d5 |
| outputs/pg.suite.v3.log (755 基线) | a420c795f33fc050 |
| outputs/rw.suite.v1.log (778) | 630c7b6a71dc16d6 |

judge 模块 pin: v1.4.1 sha 25c154b9 (base v1.2 edd841ef, v1.4 1d87cfb5); rubrics_v2 4fa60e02。

## 4. 复现命令 (Windows PowerShell, 项目根目录)

```powershell
.\run.cmd test                                   # 全量 778 tests
python tools\validate_reward_wiring.py           # 零调用离线验证 (拒绝覆盖; 换新 --out 名重跑)
python -m unittest tests.test_rubrics_reward -v   # 23 个 reward 单元测试
```
注: python 用运行时自带解释器 (run.cmd 自动定位); 重跑验证需未存在的 --out 路径 (默认名已被本次交付占用, 属一次性纪律)。
G1/G2/G3 复现见 docs/P_G_REAL_TEMPLATE_REPORT.md (采集需网络批准; G3 为一次性冻结运行, **不可复测**)。

## 5. 预算账目 (本 goal 全程)

| 阶段 | 模型调用 | tokens | 网络抓取 |
| --- | --- | --- | --- |
| G1 探针 | 0 | 0 | 20 (0 接受, 保留) |
| G1 正式 | 0 | 0 | 13 (7 接受) |
| G2 建集+聚簇 | 0 | 0 | 0 |
| G3 冒烟 | 3 | 35,648 | 0 |
| G3 正式 | 23 | 352,255 | 0 |
| reward 接线+验证 | 0 | 0 | 0 |
| **合计** | **26** | **387,903** | **33** |

上限: G3 30 调用/400k (未超); 采集补充 <=20 (正式 13, 未超)。1 次诚实 skipped_budget。

## 6. 距离 P-E (Agentic RL / GRPO 真实训练) 的差距

已具备: 冻结 Rubrics v2 协议 + 校准过的 v1.4.1 judge (受控范围内) + 冻结 reward 映射接口 + 簇级规则复用/回灌机制 + 聚簇协议 (含已知 LSH 召回缺口)。
未具备 (P-E 前置, 均需独立预注册+批准):
1. **真实页 reward 有效性**: G3 负结果表明当前 judge+映射在复杂自然页上未验证; 需先解决过度排除/触发冗余 (改进候选已披露, 另行预注册)。
2. **LSH 规模召回**: 0.867 < 0.9 硬检查 FAIL; 需 banding 参数或特征改进的独立验证 (不得对冻结集调参)。
3. **提取器覆盖缺口**: openbsd/sqlite/lua 类站点私有容器 0 块。
4. **训练基础设施**: dom_rl.py/toy_rl.py 仅脚手架; 无真实 GRPO 训练回路、无 GPU 预算、无训练/验证分离的新封存集。
5. **多标注者 IAA**: 用户已放弃第二标注者; 单标注者局限持续披露。

## 7. 停止声明

本 goal 四项要求全部完成并逐项审计 (见 §0); consolidated 报告已交付; **P-E 未启动**; 冻结封存集零改写; 所有负结果 (G2 硬检查 FAIL / G3 NO_REAL_TEMPLATE_SIGNAL / openbsd 降级 / 探针 0 接受) 如实保留。**到此停止。**
