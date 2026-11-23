# P-F 阶段1b 报告：v1.4.1 校准通过；路线 A 采集受阻（预注册候选全不合格）

日期：2026-11-23 ｜ 批准：选项 A（v1.4.1 修订 + 阶段1b 预算）
状态：**阶段1b 校准全部接受标准满足；F3 采集失败停下，等待用户选路。v4 未建、未密封、零曝光。**

## 1. v1.4.1 修订与校准（成功）

- 仅改 missing-body 锚点一条（零裁量措辞）；其余 5 锚点逐字节继承 v1.4（测试断言）；v1.2/v1.4 冻结链完整。
- 预算：**19/20 调用，317,359/350k tokens**（冒烟 1=15,542 + orig 12=176,144 + p2 6=125,673）；无需重试（v1.4 的空响应案例 blurb-missing 在 v1.4.1 下正常返回）。

| 预注册接受标准 | 观测 | 判定 |
| --- | --- | --- |
| reject_rate < 0.10 | 0.0（18/18 accepted） | 通过 |
| severe_miss ≤ 1 | 0 | 通过 |
| false_alarm ≤ 0.15 | 0.0 | 通过 |
| orig decision_match ≥ 0.85 | 1.0 | 通过 |
| orig Cohen κ ≥ 0.75（非退化） | 1.0（fail/pass/uncertain 三类） | 通过 |
| missing 锚点遵循（全部 accepted missing 案例） | 3/3 completeness 2/major/fail | 通过 |

- 锚点全景：reorder 3/3 fail、noise 3/3 fail、injection 1/1 fail、missing 3/3 fail、duplicate/title minor 轨 uncertain。
- **循环披露（重要）**：dev match=1.0 含 6/18 锚定循环（overlay 3 + 重裁决 3），且 missing 措辞由其中 2 例失败塑造——dev 完美一致**不等于**独立准确率；独立结论只能来自 v4 一次性测试。
- 机械轨（密封原始 gold，仅披露）：match 0.667、false_alarm 0.333——v1.4.1 严格锚点与旧 minor 标注的预期冲突，裁决史已改判，密封件不改写。

## 2. 路线 A 采集（失败，7/10 抓取）

| URL | raw chars | 结果 |
| --- | ---: | --- |
| sqlite.org/whentouse.html | 21,223 | 超 20k 上限 |
| sqlite.org/famous.html | 20,845 | 超 20k 上限 |
| apache.org/foundation/how-it-works.html | 52,122 | 超限（两槽位各试一次，共 2 次） |
| debian.org/social_contract | 16,550 | 窗内但 extract_html 0 块 |
| debian.org/intro/about | 19,305 | 窗内但 extract_html 0 块 |
| debian.org/social_contract（诊断探针，已记日志） | 16,550 | 确认页面真实；div#content 布局 |

**根因**：debian 用 `<div id="content">` 容器，不在抽取器选择器（`//article | //main | //*[@role='main'] | //*[@id='main'] | div.article | div.article-body …`）内 → 候选为空，v4 不可用。与 P-C role-drift `no_candidate` 发现同类的抽取器覆盖缺口。sqlite 两页仅超限 ~0.8–1.2k 字符。

按预注册计划"候选全不合格 → 停下等用户重新选路，不自动降级 B"，采集停止。抓取日志：outputs/pf.collection.v1.log.json（含探针）。

## 3. 供用户决策

- **A1（推荐）批准 3 次探针抓取**验证新候选（抽取器不动）：lua.org/about.html、sqlite.org/whyc.html、freebsd.org/about/；探针通过即正式采集+建集+kit（剩余抓取预算内）。
- **A2 批准抽取器小扩展**（容器选择器加 `//*[@id='content']`，披露；dev 候选为冻结文件不受影响）+ 重采 debian + 探针 sqlite 短页。改动抽取协议，侵入性更大。
- **B 回退零采集 iana 草案**（slate+kit 已就绪，同族同站独立性弱于 v3，须显著披露）。

## 4. 复现

```
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/pf1b.smoke.v1.json --judge-version 1.4.1 --max-source-chars 20000 --max-calls 1 --split development --ignore-cache
python -m tools.run_rubrics_judge samples/calibration_manifest.json --output outputs/pf1b.dev.orig.v1.json --judge-version 1.4.1 --max-source-chars 20000 --max-calls 12 --split development --ignore-cache
python -m tools.run_rubrics_judge samples/p2_manifest.json --output outputs/pf1b.dev.p2.v1.json --judge-version 1.4.1 --max-source-chars 20000 --max-calls 6 --split development --ignore-cache
python -m tools.score_pf_dev --gate-config outputs/pf.gate.config.v2.json --dev-batch orig=outputs/pf1b.dev.orig.v1.json --dev-gold orig=outputs/pf.dev.gold.v2/dev.orig.gold.json --dev-freeze orig=outputs/rubrics_judge.node3.freeze.v4.json --dev-manifest orig=samples/calibration_manifest.json --dev-batch p2=outputs/pf1b.dev.p2.v1.json --dev-gold p2=outputs/pf.dev.gold.v2/dev.p2.gold.json --dev-freeze p2=outputs/p2.freeze.v5.json --dev-manifest p2=samples/p2_manifest.json --mechanical-gold orig=outputs/human_review/final.v1/human_gold.final.json --mechanical-gold p2=outputs/human_review/p2.gold.v1/human_gold.p2.blind.json --output outputs/pf1b.dev.calibration.v1
python -m tools.collect_pf_v4_sources --log outputs/pf.collection.v1.log.json
```

哈希见 outputs/pf1b.dev.calibration.v1/pf.dev.json 与 outputs/pf.protocol.v2.json。全量 676 测试 OK（outputs/pf.suite.v5.log）。
