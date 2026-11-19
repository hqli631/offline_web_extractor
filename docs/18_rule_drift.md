# 实操18：固定规则适用性与模板漂移

本阶段冻结 //div[@role='main'] 后直接跨页执行，不回退评分器、不逐页修改规则。配置、HTML、参考答案和源码哈希随结果保留。

## 真实同模板复用

    .\run.cmd reuse samples/sphinx_reuse.json --output-dir outputs/rule_reuse_gate4_final

参考页“课前甜点”和迁移页“使用Python的解释器”都唯一命中；输出分别16块和32块。迁移页有6个pre、输出6个code，有5个h2–h6、输出5个heading，2个aside包装保留1个footnote。它们早已参与开发，不是新的未见测试。

迁移页没有完整独立金标，因此quality=null；标签数量相等不证明每个字符、缩进和正文边界都正确。保留的原始/抽取结构计数仅用于检查，不报告迁移准确率。

## 受控合成漂移

    .\run.cmd reuse samples/drift_lab/reuse.json --output-dir outputs/drift_lab_gate4_final

| 变化 | 匹配数 | 状态 | 参考质量 |
| --- | ---: | --- | --- |
| 原始参考 | 1 | ok | 3/3段结构匹配 |
| 只改class | 1 | ok | 3/3段结构匹配 |
| role改名 | 0 | rule_no_match | 不执行，不评分 |
| 桌面/移动两个容器 | 2 | rule_ambiguous | 不执行，不评分 |
| 末段移出容器 | 1 | ok | 2/3段；precision1，recall2/3；结构不全匹配 |

这些是字面正文独立生成的合成机制样本，源码、变异定义和完整答案保存在samples/drift_lab。不能与真实网页混报，也不能声称观察到了真实网站自然漂移。

CLI只在所有运行status为ok时返回0；它不代表quality全部匹配。漂移集合包含0/多匹配，程序应返回2；PowerShell外层工具可能转译非零码，最终以直接Python子进程returncode和逐页JSON为证据。

输出目录非空则拒绝覆盖。参考答案哈希不符会报错，不继续把错误答案当成功；quality基于本次指定规则输出，绝不调用自动容器选择器来代替复用结果。

## 由此得到的策略

- 零匹配：报告模板或规则失效，交给后续配置生成/修复；本阶段不静默改规则。
- 多匹配：报告歧义，不能随便选第一个或把两个响应式副本拼接。
- 唯一匹配：继续检查正文范围、结构和噪声。线上没有完整参考时只能用异常信号报警，不能把启发式置信度当质量真值。
- 规则与HTML分别版本化；改规则后必须重跑旧参考和所有迁移页，检查是否损害旧页。

在VS Code打开 content-moved.html 与对应输出，找到移到兄弟section的末段，观察match_count=1、status=ok仍然漏提。后续Agent能提出新规则，但同样必须通过这些检查。
