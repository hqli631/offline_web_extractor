# P-F F3 节点报告：v4 正式建集 + 盲评 kit 就绪（A2-minimal，零模型调用）

日期：2026-11-23 ｜ 批准链：路线 A → A1 探针（3 抓取）→ A2-minimal（抽取器末位回退，用户"批准"）
状态：**v4 12 例正式 slate + freeze + 盲评 kit 就绪，等待用户盲评。judge 零调用于 v4；gold 未密封。**

## 1. A1 探针（10/10 抓取预算用满）

freebsd.org/about/ 通过（19,110 字符/18 块）；lua.org/about.html（8,919）与 sqlite.org/whyc.html（12,640）窗内但 0 块——诊断：lua 内容在 table.columns，sqlite 在 div.fancy（站点私有），debian 在通用 div#content。全部抓取含探针均记录于 outputs/pf.collection.v1.log.json。

## 2. A2-minimal 抽取器扩展（已批准、已验证）

- `_candidate_nodes` 仅在**主选择器联合全部落空时**末位回退 `//*[@id='content']`；无站点专用选择器。
- **27 个现有样本快照逐字节零漂移**（基线哈希固化于 tests/test_pf_extractor_fallback.py，补丁前采集）。
- debian social_contract 回退后 38 块/标题正常/接受标准全过；噪声词/注入词冲突预检 NONE。
- 残留覆盖缺口如实披露：lua（表布局）/sqlite（div.fancy）仍不支持，留待后续独立工作。
- dev 候选为冻结文件，不受影响；冻结链（node3/p2/pb.freeze.v9）完整性不变。

## 3. 注入与建集（零网络零调用）

- tools/ingest_pf_v4_probes.py：sha256 对日志校验 + 接受标准重跑 + 双族去重 + 拒绝覆盖 + 日志 fetch 记录不可变审计。注入 pf_v4_debian（debian-org）+ pf_v4_freebsd（freebsd-org）。
- tools/build_pf_v4_calibration.py：12 例（2 模板 × clean/missing/noise/duplicate/reorder/injection，v3 同构），全可行；samples/pf_v4_manifest.json + outputs/pf.freeze.v1.json（judge pin 1.4.1，链 pf.protocol.v2 + pb.freeze.v9）+ 正式 slate。
- 建集器 judge pin 改为从 pf.gate.config.v2.json 读取（单一事实源）；首次构建 pin 1.4.0 为笔误，**提交前**确定性重建修正（全部产物当时未跟踪，删除清单经 git status 核验）。
- 盲评 kit：outputs/human_review/pf.v4.blind.v1/（F01–F12，盲性程序化验证：无 cal-/pf_v4/变异标签/judge 分数泄漏；站点名仅出现于正文内容，与 v3 案卷同构；锚点 R1/R2/R3/missing/duplicate/injection 嵌入说明）。
- 选项 B iana 草案标记 SUPERSEDED 保留（slate + kit 目录各置说明）。

## 4. 独立性披露

- v4 两模板族（debian-org/freebsd-org）对 judge **零曝光**；与 v3 同构的新模板新站独立测试。
- 抽取器回退扩展发生在 v4 建集前、dev 校准后；dev 候选冻结不受影响；v4 候选由扩展后抽取器生成（披露）。
- 单标注者、IAA 未测；一致率≠准确率；v4 一次性，FAIL 不重测不调参。

## 5. 下一步（用户操作节点 F4）

1. 按 kit INDEX 盲评 12 例，填 human_labels.blind.json（annotator/annotation_date + 每例 decision + 五维 score/status/severity；injection 例必填 injection_complied）。
2. 发回助手校验；机械修正（如有）出 config 等确认；ingest 并**在 judge 调用前密封 gold**（outputs/pf.gold.v4.v1/）。
3. 阶段2预算（13 调用/250k）单独审批 → v1.4.1 一次性 12 例 → 冻结阈值 gate（score_p3_gate v3 槽位承载 v4）→ 可复现报告后停止。

## 6. 验证

新增测试：抽取器回退回归 4 + 探针注入 5；全量套件见 outputs/pf.suite.v7.log。Secret scan NONE（提交前）。

复现：
```
python -m tools.ingest_pf_v4_probes
python -m tools.build_pf_v4_calibration
python -m tools.build_pf_v4_kit --slate outputs/pf.v4.slate.v2/pf_v4_slate.formal.json --output outputs/human_review/pf.v4.blind.v1
```
