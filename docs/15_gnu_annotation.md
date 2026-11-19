# 实操15：正文范围包含当前尚不支持的结构

目的：为新页面写独立标准，观察提取器能力边界；这一节不再重复基础 XPath 题，也不先修程序。

文件：samples/gnu.candidate.html；范围草案：samples/gnu.candidate.annotation.md。只审读原 HTML，尚未运行提取器或生成 expected。来源和 HTML 哈希见对应 source.json。

## 在 VS Code 中完成的操作

1. 打开原 HTML，搜索 What is Free Software?，确认 h2 是文章标题。
2. 搜索 History，查看后面的 dl/dt/dd：这些是自由软件定义的实质变更记录，建议保留，区别于页脚 Updated 维护时间。
3. 搜索 id="f1"，查看普通 ol/li 脚注及返回链接。它不是当前支持的语义 aside 脚注，不能因程序不支持就从正文范围删去。
4. 查看 div.toc 和 div#fsf-licensing：前者是页内目录，后者是咨询入口，建议排除；开头 div.important 是正文定义，应保留。

## 本页待冻结的协议

- description-list：每组 dt 与 dd 按原顺序保留，后续标注为 definition_term / definition_description；暂不实现提取，首轮如实记为结构缺失。若一个词有多个解释，依次保留，不并入相邻段落。
- 普通 ol/li 脚注：人工将正文注释标为 footnote，保留引用编号与 source_id；排除返回箭头等控件。程序是否识别在首轮报告中检查。
- 标题：文章级 h2 记作 title，不再重复为正文 heading；下级 h3/h4 按原层级保留。

这些是拟议标注协议，尚未冻结，不根据预测结果取舍。先复核范围草案与原文，再独立转录 expected；冻结后记录哈希、运行首次预测。若实现暂不支持，保留失败案例，进入统一错误分类后再决定是否扩展。

本次人工检查只需记录一处实质判断：History 中任选一条原文，说明它为什么属于正文而不是页脚元数据。其他已掌握的 XPath 语法不重复测验。
