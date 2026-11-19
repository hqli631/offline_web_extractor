# 实操10：新站点先标注，再预测

实操09已由你核对：三级标题正确，脚注只出现一次，heading_level=3、footnote_label=[1]、source_id=id2。

## 已准备

- samples/w3c_accessibility_intro_zh.html：W3C《Web无障碍简介》公开网页，成功响应200，本地完整HTML快照。
- 同名.html.source.json：来源、抓取时间与SHA256。
- baselines/rules-v1-before-w3c/：首次W3C预测前的源码副本与逐文件哈希，不是Git提交。
- samples/w3c_accessibility_intro_zh.annotation.md：待你填写的人工范围笔记。

未运行这篇网页的正文提取，没有加入批量评测清单，也没有创建空expected.json。

## 现在只做一件事

查看布局时打开samples/w3c_accessibility_intro_zh.preview.html：在VS Code右键该文件，选择“在文件资源管理器中显示”，再双击HTML用浏览器查看。HTML不是Markdown，不使用Ctrl+Shift+V作为网页预览。原始快照的根相对资源在file://下失效，菜单全部展开，确实会干扰人工判断；不要用失去样式的原快照硬做视觉标注。

preview副本保留原文与DOM标签结构，只调整资源路径，主CSS和四个界面脚本保存在w3c_preview_assets中；字体、图片和SVG仍可能需要网络，因此不是完全离线页面。原始.html及其哈希保持不变，后续extract/evaluate只输入原始.html，不输入.preview.html。需要核对文字或节点时仍查看原始HTML。构建脚本为项目根目录build_w3c_preview.py。

打开旁边的annotation.md，填写标题、正文第一句和最后一句、应保留的结构、应排除的内容，以及一处不确定边界。判断以保存的HTML为准。需要查看标签时回到VS Code搜索原文即可，不要求重复填写基础XPath题。

这一步只确定评测口径，还不是逐段完整标准答案。你反馈范围后，我们从原始HTML整理完整title、paragraphs和blocks，再冻结标注、运行首次预测和评测。样本一旦用于调规则，就转为development；保留首次报告。

## 本轮范围

评估静态HTML中的文章文字和已支持的结构。纳入文章解释性文字、小标题和内容列表；排除全站导航、页内目录、语言切换、反馈控件、更新/署名元数据及网站页脚。延伸阅读的取舍先记录理由再固定；媒体内容仅记录存在，不要求提取视频或图片中的文字。
