# 实操09：标题层级与脚注边界

总体路线见LEARNING_PLAN.md。本次补齐当前开发网页已知的结构缺口，然后停止围绕这几页无限扩展，进入新页验证。

## 运行与检查

```powershell
.\run.cmd reuse
```

VS Code打开outputs/rule_reuse/interpreter-transfer.md，Ctrl+Shift+V预览。检查三个三级标题：传入参数、交互模式、源文件的字符编码。它们使用###，其父标题使用##。然后搜索备注，末尾应出现[1]与Unix系统的脚注解释。原始引用仍在对应正文中，没有实现点击跳转。

当前参考页16块，新页32块；新页包含3个三级标题、6个代码块、1条脚注。原始2个aside是脚注外包装与内部单条脚注，不是2条脚注。数量和定向回归并不替代完整人工标准答案。

## 代码中的三个决定

1. content_blocks.py把h2–h6转换为heading，并保存heading_level，渲染时按级别生成#，而不是全都扁平为二级标题。h1仍单独作为文章标题。
2. extractor.py不再删除所有aside：带doc-footnote角色、完整footnote class的脚注及其footnote-list包装保留，普通侧栏仍删除；明确的ad/comments等规则仍可删除噪声。这个语义规则也不能覆盖所有网站的脚注实现。
3. 脚注提取为单独footnote块，保存footnote_label与source_id，去掉标签和backlink控件后读取正文，避免脚注内容作为普通p再输出一次。多段脚注保留段间空行；复杂列表/代码脚注尚未做到无损。

JSON中heading_level、footnote_label、source_id只在有值时输出，普通段落旧字段不变。IANA的h2标准答案新增heading_level=2，这是标注协议扩展，不是修改正文口径。旧p视图会包含脚注内部p，因此这次不能简单沿用旧新页段落数作为完整性答案。

## 亲手查JSON

打开outputs/rule_reuse/report.json，搜索“源文件的字符编码”，查看kind与heading_level。再搜索footnote_label，查看[1]、source_id和text。把对应原始HTML与输出对照，确认脚注不是侧栏广告。

下一次只需回报该标题的heading_level、脚注source_id及预览中是否重复。然后冻结当前版本，选择一篇不同站点的新文章，先人工标注再运行，至少记录一次新页错误；不继续只用目前开发样本提高分数。
