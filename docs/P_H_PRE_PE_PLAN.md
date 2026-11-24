# P_H_PRE_PE_PLAN — 推进至 P-E 阶段边界（预注册，实现前冻结）

批准: 用户 2026-11-24 "再次强调，不需要多标注者 IAA；继续推进，直至P-E阶段" + goal 授权合理预算。
范围: H1-H4 补齐 P-E 前置差距；**P-E 真实 GRPO 训练不启动**（需 GPU/torch/独立批准，见 §5）。
多标注者 IAA 永久移除（用户明确）。冻结封存集零改写；FAIL 不复测不调参；负结果如实。

## H2 — LSH banding 召回修复（零调用，先行，为 H1 提供簇）
- 变更: bands 16x8 -> **32x4**（num_perm=128 不变）。理由: banding 是召回导向候选过滤器，
  s=0.7 时候选概率 1-(1-0.7^4)^32 ≈ 0.99985（16x8 ≈ 0.62）；精确 Jaccard 验证 + CL 阈值 0.7
  逐字节不变 -> 精度由验证层保证。特征/阈值/CL/seed 全部不变。
- 新工具 tools/run_ph_cluster.py（复用 run_pc_cluster_loop.run_corpus），语料不变
  samples/pg_corpus.v1.json（22 页），输出 outputs/ph.cluster.v1.json + ph.cluster.freeze.v1.json。
- 硬检查（沿用冻结定义）: 每层 LSH 正例召回 >= 0.9 + CL 反链违规 0。
- 循环性披露: banding 变更由 G2 FAIL 在同一语料上驱动 -> dev 循环；独立确认推迟到未来新采集。
- 描述性: 与 pg.cluster.v1 的簇差异、既有 13 页召回/ARI 变化（只报告，不调参）。

## H3 — 站点私有容器覆盖缺口（零调用工程 + <=8 次抓取）
- extract_html **逐字节不变**（27 快照回归钉死）。新增 opt-in 函数
  extract_with_density_fallback(source): 先 extract_html；仅当 status in {no_candidate, empty_body}
  时启用密度后备: 候选 //div|//section|//td|//main|//article，text_len>=200 且 link_ratio<=0.5，
  score=text_len*(1-link_ratio) 取最大，remove_noise 后 extract_blocks；产出状态 ok（记录 fallback 诊断）。
- 新采集器 tools/collect_ph_coverage.py: openbsd.org index/innovations/security/goals 4 URL，
  每槽 <=2 次仅瞬时重试，总 <=8 抓取；**无论接受与否保留 raw**（覆盖探针），记录 provenance，拒绝覆盖。
- 预注册成功标准: >=2/4 页密度后备产出 >=3 块且原 extract_html 为 0 块/无候选；27 快照零漂移（测试）。
- 集成边界: 冻结 rule_cache.fallback_extract 不改；密度后备作为未来回路 opt-in（P-E 计划项），披露。

## H1 — 修复闭环 v1.1（预注册后一次性，<=20 调用/300k tokens，qwen3.8-27b）
- 新工具 tools/run_ph_repair.py（镜像 P-D2 回路，冻结助手 reuse_pd2/validate_feedback/Pd2Guard/
  critic_feedback/run_agent/j141 原样复用；冻结模块零改写）。两项预注册门控:
  GATE-1 触发门控: critic 后仅当 decision==fail OR 存在 major/critical 缺陷 OR
    (有 silver expected 且 baseline block_text_recall<1.0) 才触发修复；drift 单独不再触发。
    否则 no_repair_needed（note 记录门控理由）。
  GATE-2 保留守卫: 若 baseline decision!=fail（即仅因 silver recall 触发），repaired 必须保留
    baseline 正文: baseline 块文本在 repaired 中的 Counter 召回 >=0.9，否则拒绝修复保留 baseline
    （status=repair_rejected_retention，不再耗 rejudge 调用）。baseline==fail 时允许重构，无此约束。
- 语料: P-G 新层（H2 新簇），critic/rejudge v1.4.1 SOURCE_ONLY，max_source_chars=20000，
  max_output_tokens=2200。冻结 outputs/ph.repair.freeze.v1.json（含 plan/corpus/cluster/模块 sha + 预算）。
- 评分 tools/score_ph.py: 冻结 classify_pair + bootstrap；硬标准:
  regression_rate<=0.10 且 retention 守卫零违规接受 且 预算未超；描述性: apache-var 改善保持、
  触发削减数、reward 方向（rubrics_reward v1.0.0 对 repaired 对）。
  verdict: GUARDED_LOOP_SIGNAL / NO_GUARDED_LOOP_SIGNAL。
- 循环性披露: 门控由 G3 回归驱动 -> dev 循环，非独立 holdout；真实页 reward 资格仍限 P-F 受控范围。

## H4 — GRPO 训练基础设施就绪（零调用）
- 新模块 src/webextractor/grpo_core.py: 纯 Python 确定性 GRPO 核心 —
  group_advantages（组内均值/标准差归一，std=0 -> 0 并披露）、clip 代理目标 + k3 KL 正则、
  tabular softmax 策略更新；reward 经冻结 rubrics_reward v1.0.0 接口（RubricsRewardProvider）。
- tools/run_grpo_dryrun.py: 离线 dry-run（mock judge 夹具，合成披露），验证 advantage 零均值、
  reward 管线 mapping_version、确定性、策略向高 reward 动作移动；输出 grpo.dryrun.v1.json。
- 环境审计 outputs/grpo.env_audit.v1.json: torch/CUDA/numpy 实测（当前 torch 缺失 -> 真实训练不可行，如实）。
- docs/P_E_TRAINING_PLAN.md: 预注册 P-E 真实训练计划（资源/数据/预算/门控），**不执行**。

## 里程碑与停止
M1=计划+H2；M2=H3；M3=H1；M4=H4+consolidated 报告 docs/P_E_READINESS_REPORT.md。
每里程碑: 全量测试(.\run.cmd test) + 秘密扫描 + commit/push。交付后**停止于 P-E 边界**。
预算合计: 模型 <=20 调用/300k tokens（H1），网络 <=8 抓取（H3），其余零调用。
