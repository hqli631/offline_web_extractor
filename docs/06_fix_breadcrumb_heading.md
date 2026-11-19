# 实操06：清理面包屑并保留h2

你找到的ol.breadcrumb对应噪声清理；h2对应正文结构提取。两项已修复，IANA标准答案没有改变。

在VS Code打开src/webextractor/extractor.py，搜索breadcrumb：NOISE_XPATH新增完整class token匹配，不会把所有ol或所有链接删除。正文有序列表仍保留，drop_tree保留被删节点后的tail文字。

打开src/webextractor/content_blocks.py，搜索 `node.tag == "h2"`：读取文字、清理headerlink锚点，生成heading块并return。主标题h1仍单独保存，不重复进入正文。render_blocks的heading分支使用 `## `，并在标题与列表/段落之间插入空行。当前只处理h2，没有扩展h3–h6级别元数据。

normalize_heading_text统一清理主标题与h2的锚点，normalize_title复用它。

每次在VS Code终端单独粘贴一行：

```powershell
.\run.cmd extract samples/iana_example_domains.html --output outputs/iana.fixed.json --text-output outputs/iana.fixed.md
```

打开outputs/iana.fixed.md，Ctrl+Shift+V预览：两段正文、Further Reading二级标题、三个参考条目；没有Instructions and Guides。

```powershell
.\run.cmd batch
```

对比outputs/batch_report.before_iana_fix.md与outputs/batch_report.md：IANA块文本精确率/召回率从5/6升至1，结构全匹配从False变True，旧页面保持匹配。

```powershell
.\run.cmd test
```

当前33个回归测试通过，包含class完整匹配、普通ol保留、尾文保留、h2顺序和锚点清理。

IANA已用于改规则，清单将它移入development。当前3篇真实开发网页与1个人工案例都匹配，只说明开发回归通过，目前没有未参与调试的验证网页。历史初始划分保存在samples/evaluation_manifest.initial_validation.json，仅用于追溯，不能用新规则重跑后宣称独立验证。下一轮需重新冻结规则和准备新的验证样本。
