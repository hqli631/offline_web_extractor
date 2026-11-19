# 样本级标注例外记录

统一协议与样本原文不完全同构时，先写样本决定，再冻结答案。例外不是依据预测结果倒推的修正。以下决定都在各自首次预测前写入 annotation 和独立转录脚本。

## GitHub Copilot

- 信息性 blockquote 保留为 quote；旧 paragraphs 仍保留其中的实际 p。这超出 v1.1 基础类型列表，当前生产提取器可能只表达为 paragraph，单列为引用结构差异。
- 损坏 aside 的孤立 li 按原语义保留为3个 ul 列表项；两个只含伪标签碎片的 p 排除，不改原始 HTML。
- UTF-8 根据 HTTP Content-Type 明确解码。首次结果是否乱码由实测决定，独立转录脚本的默认解析试验不能代替生产结果。

## W3C link text

- blockquote 中的实际 p 按 paragraph 保存，引用包装样式不纳入当前参考。这与 GitHub 的 quote 口径不同，两页的结构全匹配不可直接混合解释为统一引用支持率。
- Further Reading 是文章参考，About QA Tips 是系列说明，前者保留、后者排除。

当前阶段记录异质结构口径。进入统一基线前，需要确定引用风格是否属于目标结构；如修订参考，使用 v2 文件保留 v1 和首次报告，不能静默替换。
