# P-G 预注册计划：真实模板族 + LSH 规模（suffix-presence 独立验证 + 真实页泛化修复）

> 状态：预注册（执行前冻结；采集/模型调用均待批准）。前置：P-D2 GENERALIZATION_SIGNAL（3304a30）；P-C 诚实负面（full-counts 真实语料对召回 0.077/ARI 0.122 过分裂）+ post-hoc 消融（suffix-presence 0.538/0.660，明示"采纳须独立预注册+新独立采集语料"）。本计划即该独立验证。judge 分数仍非训练奖励。

## 1. 目标与范围

1. **聚簇协议采纳验证**：把 suffix-presence 特征模式作为新冻结协议，在**新独立采集**的真实多页模板族上验证召回/纯度/复用（不在 P-C dev 语料选优后直接宣称泛化）。
2. **LSH 规模机制**：混合真实语料（新采 + 既有快照）上的候选召回、抗链式、派生节省代理；描述性，非生产规模宣称。
3. **真实页泛化修复**：P-D2 簇级泛化修复 + 内联回灌机制在真实 HTML 上运行（含受控漂移变体保证触发），检验 union 规则在真实页的噪声风险（P-D2 局限）。

范围边界：3 个新模板族 × 4 自然页 + 3 受控变体 + 13 既有 dev 快照 = 28 页；描述性信号非奖励门槛；无人类 gold（变体 silver expected 程序侧核；自然页仅 judge source_only 质量代理，不做准确率宣称）。

## 2. 语料与采集（G1，网络预算待批准）

**新族候选（主→备，全部未曝光于 judge v1.4.x）**：
- **apache.org**：foundation/how-it-works.html → foundation/faq.html → foundation/marks-policy.html → licenses/LICENSE-2.0.html
- **openbsd.org**：index.html → goals.html → security.html → innovations.html
- **netbsd.org**：index.html → about/ → security/ → changes/
- 备选族（主族失败时启用，如实披露）：freebsd.org / debian.org（**v4 已曝光**，降级披露）。排除族沿用 P-F 清单（python/sphinx、iana、rfc、whatwg、web.dev、mdn、w3c、gnu、npr-text、github-blog、nasa）+ sqlite（P-F 探针 0 块覆盖缺口）。

**接受标准**：raw 3k–30k 字符；extract_html ≥3 块 + 非空标题；每槽位 ≤4 次尝试，**总 ≤20 次抓取**；每次抓取记 URL/final_url/sha256/raw_chars/时间戳/接受检查；拒覆盖。某族 <3 页接受 → 该族降级为单例/对照，如实报告；全部失败 → 停下等用户重选（不自动降级到曝光族）。

**受控变体（G2 本地构建，零网络）**：每族 rep 页 1 个漂移变体（role/属性替换或容器标签变更，正文逐字保留）；**silver expected = rep 页 extract_html  blocks**（程序产出，披露 silver≠gold；仅用于程序侧核与回灌 recall 校验，永不进 prompt）。

**既有快照**：samples/dom_similarity.expanded_development.json 13 页（字节不变，家族标签沿用）作混合语料干扰项；仅参与聚簇/复用度量，**不做 critic/修复**（范围边界）。

## 3. 聚簇协议（新冻结，采纳动机披露）

feature_mode=**suffix-presence**（采纳动机：P-C post-hoc 消融；本计划在**新语料**上独立验证，非调参）；threshold=0.7、complete-linkage、MinHash num_perm=128/seed=20261123、LSH bands=16×rows=8、drift_threshold=0.7（全部继承冻结值）。
度量（分层报告）：新 15 页 / 全 28 页 / 既有 13 页（与 P-C full-counts 基线 0.077/0.122 及消融 suffix 0.538/0.660 同页对照，披露为协议采纳检查）；LSH 候选数/全对数、正例召回（固定 seed 实测）；CL 抗链式违规；对精度/召回/ARI（vs manual_group）；派生次数/页数节省代理、复用成功率、回退/漂移计数。

## 4. 真实页泛化修复（G3，模型预算待批准）

复用 P-D2 冻结机制（触发/分类/回灌/泛化复用语义逐字沿用），适配披露：
- 修复参考 = 簇内页源（≤8；evidence_chars=16000 截断真实长页，披露）。
- critic/rejudge：v1.4.1 source_only（gold=None）；max_source_chars=20000。
- **回灌校验适配（预注册）**：结构校验（唯一匹配+ok+非空）适用于全部成员；recall 不降校验仅对有 silver expected 的变体成员生效；自然页质量证据仅 judge 分类（无 gold，披露）。
- 仅新 15 页进入 critic/修复；既有 13 页不进入。
- 修复 ≤1 干预/成员（max_attempts=2）；内联回灌；泄漏审计；Pd2Guard 双守卫。

## 5. 预注册判据

**硬检查**：CL 抗链式违规=0；LSH 正例召回 ≥0.9（固定 seed）；泄漏审计全通过；unnecessary_repair=0；candidate/freeze integrity 无不符。
**描述性期望（非门槛，如实报告）**：新族对召回 ≥0.5（消融动机值）；复用成功率、节省代理。
**修复信号判据**：improvement_rate ≥1/3（paired n）；regression_rate ≤0.10；feedback_accepted ≥1（结构+silver 校验）；reuse_recovery ≥1。
**verdict**：REAL_TEMPLATE_SIGNAL / NO_REAL_TEMPLATE_SIGNAL（n 小 CI 宽如实降级；若无修复触发则 NO_REPAIR_NEEDED 如实交付聚簇+复用报告）。

## 6. 预算（分阶段审批）

- **G1 采集**：≤20 次 HTTP 抓取，零模型调用。（本次请求批准）
- **G2 聚簇+复用+变体构建**：零调用零网络。（本次请求批准）
- **G3 修复**：≤30 调用 / 400k tokens 硬顶（qwen3.8-27b）；估算 15 critic + ≤10 生成 + ≤5 rejudge ≈ 25–30 调用 / ~340k tokens（真实页 5–30k 字符，单次 ~13–20k tokens）。**G2 完成后单独请求批准**，届时按实际漂移成员数细化。

## 7. 纪律与局限

协议 sha 冻结（suffix-presence 实现 / dom_lsh / dom_cluster / rule_cache / rule_agent / v1.4.1 / rubrics v2）；运行前后校验。新采集语料一次性建集冻结；不回填不调参；负结果如实。
局限：28 页非生产规模；LSH O(n²) 规避收益描述性；suffix-presence 采纳动机来自 dev 消融（新语料验证是诚实检验，可能回归）；真实页 union 规则噪声风险由 judge cleanliness 检验但无 gold 校准；silver≠gold；自然页无准确率宣称；单标注者背景延续；judge 分数非训练奖励；曝光备选族降级披露。

## 8. 复现命令（届时细化）

```
python -m tools.collect_pg_sources --output outputs/pg.collect.v1.json
python -m tools.build_pg_corpus --collect outputs/pg.collect.v1.json --output outputs/pg.corpus.v1.json
python -m tools.run_pg_cluster --corpus outputs/pg.corpus.v1.json --output outputs/pg.cluster.v1.json
python -m tools.run_pg_repair --freeze --freeze-path outputs/pg.freeze.v1.json --approval-quote "..."
python -m tools.run_pg_repair --run --output outputs/pg.run.v1.json
python -m tools.score_pg --run outputs/pg.run.v1.json --output outputs/pg.score.v1.json
.\run.cmd test
```

## 9. G1 探针细化声明（形式采集前；聚簇协议未改）

**首轮探针诚实负面**（outputs/pg.collect.v1.json，20 抓取 / 0 接受，保留不删除）：
- apache.org 自然页 37k–52k 字符，超出原 [3000, 30000] 窗口（该上界是 P-F critic 可达性遗留假设；聚簇/复用本身无需小页）。
- openbsd.org index.html 抽取标题为空被拒（标题接受标准保留）。
- apache marks-policy.html 返回 404。
- **重试纪律缺陷**：对确定性拒绝（字符超限/404）重复抓同一 URL 至 4 次，浪费预算，致 netbsd 未触及即耗尽 20 次上限。

**细化（仅接受标准与采集纪律，正式建集前冻结）**：
1. 字符窗口上界 30000 → **60000**（下界 3000 不变）。G3 critic 仍 max_source_chars=20000 截断（披露）；聚簇/复用不受页长限制。
2. 重试纪律：**确定性拒绝（接受标准不符 / 4xx）转下一候选 URL，不重试**；仅瞬态网络错误在槽位预算内重试。每槽 ≤4 次、总 ≤20 次上限不变。
3. 标题接受标准保留（无标题页拒）。

此细化**不改** suffix-presence / threshold 0.7 / complete-linkage / MinHash / LSH / drift_threshold / 判据。首轮探针为接受标准探针，非正式建集；正式采集另用 outputs/pg.collect.v2.json（**补充抓取预算待用户批准**，首轮 20 次已耗尽）。
