# P_E_TRAINING_PLAN — Agentic RL / GRPO 真实训练（预注册草案，未执行）

状态: **PRE-REGISTERED DRAFT, NOT STARTED**。执行前需: 用户明确批准 + GPU/API 训练资源 + 独立预算。
本文件是 P-H 交付的一部分（就绪边界），不是执行授权。

## 1. 已就绪（P-H 证据）
- 冻结 reward 映射 v1.0.0（rubrics_reward.py, sha c08343b4）+ 离线方向一致性 8/8。
- GRPO 核心数学离线验证 GRPO_PLUMBING_READY（grpo.dryrun.v2.json）: 组内 advantage 零均值/单位方差、
  clip 代理 + k3 KL、确定性、策略向高 reward 移动（tabular 脚手架，合成夹具披露）。
- 修复闭环 v1.1 门控（GATE-1 触发 / GATE-2 保留）GUARDED_LOOP_SIGNAL: 回归率 0、冗余触发削减 5。
- LSH 32x4 召回 1.0（H2）；密度后备覆盖修复 3/4（H3, opt-in 未接冻结 rule_cache）。

## 2. 未就绪 / 前置缺口（执行前必须解决或披露接受）
1. **资源**: 本机审计 torch=False / CUDA=False（grpo.env_audit.v2.json）-> 真实训练不可行。
   需 CUDA GPU（建议 >=24GB 显存用于 0.5B-1.5B LoRA + judge 并发）或外部 API 训练服务。
2. **真实页 reward 有效性**: 仍 UNVALIDATED（G3/H1 负结果: apache 修复一次性采样失败、改善证据 0）。
   初始训练必须限定 P-F 受控合成范围（同模板、冻结 Rubrics v2、受控变异）；真实页课程需先另行验证。
3. **新封存 holdout**: v1-v4 已消耗；P-E 评测需新采集独立封存集（一次性，预注册阈值）。
4. **密度后备集成**: 接入 rule_cache.fallback_extract 会改冻结 sha -> 需新冻结版本链（P-E 内预注册）。
5. **judge 成本**: 每 rollout 一次 v1.4.1 调用 ~15k tokens；G=4-8 组采样成本线性放大。

## 3. 拟议配置（执行时冻结）
- 策略模型: Qwen2.5-0.5B/1.5B-Instruct + LoRA（或规则搜索 agent 策略）；参考模型冻结副本。
- 算法: GRPO（组内归一 advantage，clip_eps=0.2，kl_coef=0.01 k3，与 grpo_core 一致）；
  per-sequence reward 经 RubricsRewardProvider -> v1.4.1 judge（source_only）。
- 数据课程: 阶段 A 仅 P-F 受控合成 slate（reward 资格范围内）；阶段 B 真实页（需先通过独立验证）。
- 种子/确定性: 固定 seed；rollout/judge 缓存哈希；每步记录 prompt/response/usage/sha。
- 预算框架（需逐项批准）: 试点 ~500 rollouts x G=4 x ~15k tokens ≈ 30M judge tokens + 训练 GPU 时；
  分阶段门控，任一阶段 FAIL 即停，不复测调参。

## 4. 预注册成功门控（草案，执行前冻结）
- 新封存 holdout 上提取 F1 / judge decision 改善 >= 预注册阈值；回归率 <= 0.10；
- reward-hacking 审计: 程序化召回/精度与 judge reward 方向一致（不一致 -> 停下披露）；
- 泄漏审计全过；预算未超；冻结链完整。

## 5. 风险与诚实边界
- judge 判改善 != 真实改善；agreement != accuracy；单标注者 gold（用户已移除多标注者 IAA 要求）。
- dev 循环性: H1 门控由 G3 回归驱动；P-E 评测必须用未曝光新集。
- 合成范围资格不可外推到自然网页（G3/H1 已证伪迁移）。
- 本计划不启动任何训练、不采集新数据、不调用模型；一切执行需另行批准。
