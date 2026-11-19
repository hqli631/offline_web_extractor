# 正文标注协议 v1.2：统一引用结构

本版本继承 ANNOTATION_PROTOCOL.md（v1.1）的内容范围、文本规范、列表、代码、表格、定义列表、脚注及冻结要求；以下引用规则补足 v1.1 未定义的 quote 类型。本版本用于后续统一结构基线，不能回写历史首次评测的协议。

## 引用块

- 正文范围内 blockquote 中的每个实际 p 记作一个 quote 块。多个 p 分别保留，不把整段 blockquote 合成一个长块。
- quote 使用基础字段 kind、text、list_type=null、depth=0、ordinal=null。文字仍按普通文字规范解码实体和合并空白。
- 普通正文 p 仍为 paragraph。块类型取决于原始语义包装，与当前提取器是否支持无关。
- 引用内的代码、列表继续使用原 code/list_item 规则，不把它们的文字再次并入 quote。没有 p 包装的复杂引用需先记录独立范围决定，不能按预测结果临时取舍。
- 旧 paragraphs 视图仍记录范围内实际 p，包含引用中的 p；本次结构类型迁移不改变其内容、数量或顺序。

## 迁移与解释

- W3C link text 的五个 blockquote/p 由 v1 paragraph 迁移为 v2 quote；其余字段与全文文字、顺序完全不变。
- GitHub Copilot 的既有单段 quote 已符合本规则，无需修改或复制其 expected。GNU、NASA 无正文引用块，不需迁移。
- 这是跨页面结构口径统一，不是修复正文文本错误，也不是为了匹配生产提取结果。
- 所有 v1 expected 与 first_evaluation 保留原字节。W3C 的 v2 使用独立文件，迁移依据及 SHA256 记录在 samples/annotation_revision.quote_v2.json。
- 后续基线若使用 v1.2，W3C 应读取 expected.v2.json；历史首次报告仍明确为 v1，不以新标准替换旧结论。比较引用结构时必须声明协议版本，不能混报。

本版本由助手根据原始 HTML 和独立审查制定，未经用户逐项复核；仍遵循 v1.1 的标注独立性限制。
