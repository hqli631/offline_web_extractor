# Gate10 玩具强化学习协议

环境是有限的一步 XPath 规则搜索 bandit，动作来自四个固定候选规则。sparse 只有结构完全匹配得分，proxy 故意只奖励返回块数量，corrected 同时使用 precision、recall 和结构类型。REINFORCE 使用 softmax policy gradient；grpo-like 在每组采样上做相对奖励标准化，展示 GRPO 的核心思想而非完整大模型 GRPO。

固定随机种子可复现。实验同时保留代理奖励投机案例和修正奖励结果：long-noise 的长度代理高，但包含导航、推荐和评论；修正奖励应选择 exact。轨迹只用于教学，不能外推到真实网页或宣称已完成完整 PPO/GRPO 训练。

运行：python tools/run_toy_rl.py --output outputs/rl_toy.v1.json；测试：run.cmd test。
