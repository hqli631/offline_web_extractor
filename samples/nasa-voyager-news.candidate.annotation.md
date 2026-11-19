# nasa-voyager-news 人工范围笔记

状态：独立标注已冻结，待首次预测。助手审读原始 DOM 后确定范围并辅助转录，未经用户逐项复核；未导入生产源码，未运行正文提取器，未查看预测。

来源：https://www.nasa.gov/news-release/nasa-invites-media-public-to-join-voyager-1-one-light-day-activities/

本地文件：nasa-voyager-news.candidate.html

模板标签：news

建议用途：开发诊断样本。正式 split/source/registry 由主任务统一更新；本次不自行修改来源或清单。

- 文章标题：NASA Invites Media, Public to Join Voyager 1 One-Light Day Activities
- 正文第一句（原文）：Launched nearly 50 years ago in 1977, NASA’s Voyager 1 on Wednesday, Nov. 18 will have traveled one light-day from Earth, which is more than 16 billion miles (25.9 billion kilometers).
- 正文最后一个说明句：For more information about NASA’s Voyager mission, visit:
- 正文最后一块（原文）：https://science.nasa.gov/mission/voyager/
- 应保留：开头至任务信息链接的15个 p 段落；参与者5条 ul/li 列表；段落内链接文字，包括活动、在线观看、NASA任务信息链接。正文内 RSVP 报名条件与联系邮件属于本新闻报道的活动参加信息，保留。正文无独立 h2/h3 小标题，无代码、表格或注释。
- 应排除：顶部导航、文章日期/署名/阅读时间/发布编号及地点元数据、社交分享按钮、图片及图注/署名、正文末尾 -end- 标记和其后的两段 press contacts、Details/Related Terms、页脚机构介绍与导航、反馈表单。
- 一处边界判断：正文中 RSVP 段落虽然含 josh.smooha@jpl.nasa.gov，仍说明参加本次活动的具体条件，保留；-end- 后两段仅是新闻联络人名/电话/邮件，属于发布元数据，排除。不能用“含邮箱即噪声”的规则取代语义判断。

## DOM 定位与独立转录证据

- 标题 XPath：//main/article//h1，唯一命中。
- 正文候选 XPath：//div[contains(concat(' ',normalize-space(@class),' '),' entry-content ')]，唯一命中。
- 原始绝对路径：/html/body/main/article/section/div[2]/div[2]/div。
- 该候选有20个直接子元素，按0起算：第0项为图与图注；第1—16项为正文段落及参与者列表；第17项为 -end-；第18—19项为 press contacts。标准答案只转录第1—16项。
- 第9项为含5条 li 的列表，其余正文项均是 p；网页活动信息中含推广式用语，但属于本新闻主题，不误当站点推广删去。
- 本轮范围将图片与图注排除，不对图片作OCR；如以后扩展图注口径，必须建立新版标准，保留本次首轮证据。

## 冻结记录

- HTML SHA256：e7f443d226454244fd9c4a6532a1de1697c7463d69aadac8751c1ab396510e22。
- expected：nasa-voyager-news.candidate.expected.json，20个blocks（15 paragraph、5 list_item），旧p视图15段。
- expected SHA256：9d5e38d2394800e9652bc09d15d8b875da9c19acba7fba93aa2f5769e801ea08。
- 转录方法：tools/annotations/nasa_reference.py，独立lxml读取并按已审读的具体子元素序号生成，非人工逐字键入，也未复用生产提取/渲染函数。脚本校验原HTML哈希、标题、子元素数量、列表项数量和末尾边界；已冻结expected存在时只校验相同内容，不覆盖。
- 2026-11-13：独立标注冻结完成；首轮预测尚未执行。

先人工确定正文边界，再独立转录 expected.json；首次预测前不能依据程序输出修改标准答案。快照为完整响应，未静默截断。
