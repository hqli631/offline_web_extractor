# Gate7：跨样本规则与Agent评测

数据：1页reference，仅用于Agent输入；4页test及expected只在生成结束后评测。全部为受控合成漂移，不代表真实网页泛化。

| 页面 | 状态 | 标题 | 块文本P | 块文本R | 结构 |
| --- | --- | --- | ---: | ---: | --- |
| class-drift | ok / 期望 ok | True | 1.000 | 1.000 | True |
| role-drift | rule_no_match / 期望 ok | None | 0.000 | 0.000 | None |
| duplicate-main | rule_ambiguous / 期望 ok | None | 0.000 | 0.000 | None |
| content-moved | ok / 期望 ok | True | 1.000 | 0.667 | False |

修复回放状态：`runtime_accepted`；尝试次数：2；`quality_evaluated`：true（只在本评测层）。

role-drift 的 role XPath 失配、duplicate-main 的多匹配和 content-moved 的召回下降均被保留；这三类失败不能通过把测试页送入提示来修复。回放 provider 是人工响应，不能当真实Qwen效果或成本。
