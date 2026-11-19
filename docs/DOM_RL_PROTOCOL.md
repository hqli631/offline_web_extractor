# Gate10 实际 DOM 奖励实验

dom_rl.py 在本地 HTML 上调用受限 execute_rule：第一步选择容器 XPath，第二步选择停止或删除噪声。gold 只用于奖励评价，不进入 observation。当前是两步有限环境，不是完整 PPO/GRPO 或 Agentic RL。

proxy 只奖励块数量，corrected 同时考虑 precision、recall 和顺序匹配。环境用缓存避免在每个训练回合重复创建解析子进程；缓存首次填充仍会实际执行 XPath。缓存键和命中状态必须与输入版本一起解释。

运行：

    python tools/run_dom_rl.py --output outputs/dom_rl.reproduce.json

使用新的文件名，历史实验不覆盖。固定种子结果仅是教学反例，不能外推到真实网页或大模型训练收益。
