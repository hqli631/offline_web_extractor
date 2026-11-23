# P-F 交付报告：judge v1.4 零调用工程包（审批门待决）

> 状态：**零调用工程包已交付**；模型调用/新采集/人工标注**全部停在审批门**，未花费任何预算。
> 主线：P-B gate FAIL（8/10）→ v1.4 协议周期是 reward 资格的唯一路径。预注册计划：`docs/P_F_V14_PLAN.md`。

## 1. 交付物与哈希

| 文件 | sha256 |
| --- | --- |
| src/webextractor/rubrics_judge_v14.py（JUDGE_VERSION 1.4.0） | `1d87cfb5e83ceb65545fe87a07c68d99ea683a7fd025f4dfe185942c30c2c37c` |
| src/webextractor/rubrics_judge.py（v1.2，**字节冻结保持**） | `edd841efb52961f07891160ccae7fabcc72da65734854da9a86e02bf622ff891`（= pb.freeze.v9 pin） |
| tools/build_pf_v4_kit.py（选项 B 盲评 kit 草案构建器） | 6078769d1388d1cb9411cf8b3c6265b40016862d4245845e1db81139921cbb44 |
| tools/build_pf_v4_slate.py（选项 B slate 草案构建器） | `52553b991537c61c2054e7a2c8b78a6f85558bf796d4c3a495047002284dc5be` |
| docs/P_F_V14_PLAN.md（预注册） | `ead390452fa383a022e2134dca4af2bb172e61c62a7c6fa3a52f174c314bfd8c` |
| outputs/pf.v4.slate.v1/pf_v4_slate.draft.json（DRAFT 未密封） | `cbb7a64389e9e2aac0fe5a09e71216adb4d90a76f8f70c691027b118f84f8855` |

## 2. 完成节点与验证

| 节点 | 内容 | 验证 |
| --- | --- | --- |
| F1 | v1.4 模块：6 条裁决锚点（R1 reorder 绝不 minor / R2 noise 零容忍 / R3 title 空白 minor / missing 关键缺失 severe / duplicate 按量级小重复 minor / injection 污染不服从）追加至 prompt 协议；执行语义镜像 v1.2 | 13 测试 OK：v1.2 源码 sha 冻结、锚点存在与措辞、v1.2 prompt 不被污染、预算、确定性、**v1.2/v1.4 执行逐字段等价**（除 provenance）、severe→fail、截断 partial、错误抑制、缓存 |
| F2 | 预注册计划 + dev gold 冲突审计 | 程序扫描 18 例 dev gold：**3 例冲突**（cal-appetite-missing_paragraph、cal-interpreter-missing_paragraph 均 3/minor；cal-interpreter-reorder 3/minor 违反 R1），其余 15 例一致 |
| F3 | 选项 B v4 slate 草案：iana-abuse/iana-whois ×6 变异=12 例（v3 同构），零调用零网络，未写 samples/、未密封 | 7 测试 OK：12 例、无截断（pass 可达）、同族曝光披露、确定性、拒覆盖、dry-run；python-search 因单段落块 reorder 不可行被诚实排除。**盲评 kit 草案**（tools/build_pf_v4_kit.py → outputs/human_review/pf.v4.blind.draft.v1/，F01–F12）：7 测试 OK，案卷无真实案号/模板名/变异标签/judge 分数（盲度程序验证），锚点入 instructions，gold 先密封后 judge 纪律写入 INDEX；slate 批准后方可正式标注 |
| F4 | 全套件回归 | **Ran 631 tests, OK**（outputs/pf.suite.v2.log；P-C 604 + P-F 27） |

## 3. 关键诚实声明

- v1.4 锚点是 **post-hoc 协议修订**（由 v3 失败+裁决固化），不是独立验证；v3 的 12 例已对 v1.4 曝光，永久降级为 development。frozen v1/v2/v3 均不重跑。
- duplicate 锚点按密封 gold P02/P08 定为**量级制**（小重复 3/minor），非零容忍——与 R1/R2 不同，如实区分。
- 选项 B 两页同属 iana 族（模板经 example_domains 曝光）→ 同族同站转移，独立性显著弱于 v3；**选项 A（新采集 2 新模板短页）仍是推荐路线**。
- 大页面（rfc 1.8MB / whatwg 16MB / webdev 145KB / sphinx 长页 73–140KB）超 20k 字符截断 → pass 不可达，不能入 gate；长页证据工程留待后续。
- v1.4 本身仍 **reward-INELIGIBLE**，直至其 dev 校准 + 密封 v4 gate PASS。

## 4. 审批门（等待用户，未批准不执行）

1. **3 例 dev gold 重裁决**（清单见计划 §3）：按 R1/missing 锚点给出新 score/severity/decision；其余 gold 不动。
2. **v4 slate 选择**：A（新采集，需采集预算）或 B（零采集 slate 草案已就绪，独立性弱）。
3. **阶段 1 预算**：v1.4 smoke 1 + dev 校准 18 = 19 调用，建议上限 20 调用 / 350k tokens（qwen3.8-27b，P-B 实测均值 ≈17.4k/调用）。阶段 2（v4 一次性 12，13 调用/250k）仅在阶段 1 达标后另批。

批准后执行链：重裁决 ingest → dev 校准 → v4 构建+盲评 kit → 用户盲评 12 例 → gold 先密封 → v4 一次性 → gate → 可复现报告，停。

## 5. 复现命令

```powershell
python -m unittest tests.test_pf_judge_v14 tests.test_pf_v4_slate -v
python -m tools.build_pf_v4_slate --output outputs/pf.v4.slate.v1   # 拒覆盖；--dry-run 可行
python -m tools.build_pf_v4_kit --output outputs/human_review/pf.v4.blind.draft.v1   # 拒覆盖
.\run.cmd test
```
