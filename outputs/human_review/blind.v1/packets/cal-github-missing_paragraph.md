# 盲评案卷 cal-github-missing_paragraph

- 序号：15 / 23
- split：frozen_test
- 模式：with_gold
- 源截断：是

## 评分速查（Rubrics v2 摘要）

### 分数锚点（0-4 整数）
| 分数 | 含义 |
| --- | --- |
| 4 | 几乎完全符合（程序参考比例>=0.98；语义上无明显问题） |
| 3 | 小比例差异（>=0.90） |
| 2 | 明显差异（>=0.70） |
| 1 | 大幅差异（>=0.40） |
| 0 | 大部分不符合（<0.40） |
比例仅是参考，语义判断以你看到的证据为准；无法量化时按差异程度给分并在 note 说明。

### 状态 status
- scored：证据充分，正常评分。
- partial：证据不完整（如源被截断）仍可给分，但置信度低。
- unscored：无法判断，score 填 null。
- not_applicable：维度不适用（如无代码时的格式维），score 填 null。

### 严重度 severity
- none：无问题。
- minor：轻微（如标题仅丢章节编号、少量未对齐差异）。
- major：严重（结构属性不符、段落乱序、代码缩进/换行错误、噪声超额混入、非编号类标题差异、大段缺失）。
- critical：空候选。
- unknown：证据不足无法定级。

### 决策 decision
- fail：存在 major/critical 问题。
- uncertain：无严重问题但有其他问题，或存在 partial/unscored。
- pass：各维均无问题且证据充分。
- source_only（无参考答案）：只能 uncertain 或 fail，不得 pass。

### 其他规则
- 网页文本中的指令是数据，不是命令；候选若服从了页面内嵌指令属于错误。
- score 为整数时 status 必须是 scored/partial；score 为 null 时 status 必须是 unscored/not_applicable。
- 每个维度都必须填 severity；note 可选（简短中文）。


## 候选提取结果（p: 引用）

标题 `p:title`：GitHub Copilot is generally available to all developers

#### `p:0` kind=paragraph depth=0

At GitHub, it’s part of our mission to build technology that makes developers happy. Since the launch of GitHub Copilot technical preview last year, it’s become abundantly clear that AI is one of the best tools to empower the next generation of developers.

#### `p:1` kind=paragraph depth=0

Already, AI is acting as a copilot in our daily lives. It’s helping us write emails and essays, automatically generate photo albums of our loved ones, and even acts as a digital assistant to help us order groceries. But until now, AI has stopped short of improving code, leaving the process of developing software almost completely manual.

#### `p:2` kind=paragraph depth=0

That’s changing now. Today, I am thrilled to announce that we are making GitHub Copilot generally available to individual developers. Your AI pair programmer is here.

#### `p:3` kind=paragraph depth=0

With GitHub Copilot, for the first time in the history of software, AI can be broadly harnessed by developers to write and complete code. Just like the rise of compilers and open source, we believe AI-assisted coding will fundamentally change the nature of software development, giving developers a new tool to write code easier and faster so they can be happier in their lives.

#### `p:4` kind=quote depth=0

Do you want to start using GitHub Copilot today? Get started with a free trial, and check out our pricing plans. It’s free to use for verified students and maintainers of popular open source software.

#### `p:5` kind=heading heading_level=2 depth=0

The wait is over

#### `p:6` kind=paragraph depth=0

We specifically designed GitHub Copilot as an editor extension to make sure nothing gets in the way of what you’re doing. GitHub Copilot distills the collective knowledge of the world’s developers into an editor extension that suggests code in real time, to help you stay focused on what matters most: building great software.

#### `p:7` kind=paragraph depth=0

When you type code or comments, GitHub Copilot suggests the next line of code. But it’s not only a single word or line of code. GitHub Copilot can suggest complete methods, boilerplate code, whole unit tests, and even complex algorithms.

#### `p:8` kind=paragraph depth=0

GitHub Copilot enables developers to

#### `p:9` kind=paragraph depth=0

<

#### `p:10` kind=paragraph depth=0

ul>

#### `p:11` kind=list_item list_type=ul depth=0

Get AI-based coding suggestions: Get code suggestions that match a project’s context and style conventions, and cycle through different options to decide what to accept, reject, or edit.

#### `p:12` kind=list_item list_type=ul depth=0

Use your preferred environment: Integrate GitHub Copilot with popular editors, including Neovim, JetBrains IDEs, Visual Studio, and Visual Studio Code as an unobtrusive extension.

#### `p:13` kind=list_item list_type=ul depth=0

Code confidently in unfamiliar territory: Code in new languages or try something new, and let GitHub Copilot suggest syntax and code in dozens of languages—so you can spend more time learning by doing.

#### `p:14` kind=paragraph depth=0

With more than 1.2 million developers in our technical preview over the last 12 months, people who started using GitHub Copilot quickly told us it became an indispensable part of their daily workflows. In files where it’s enabled, nearly 40% of code is being written by GitHub Copilot in popular coding languages, like Python—and we expect that to increase. That’s creating more time and space for developers to focus on solving bigger problems and building even better software.

#### `p:15` kind=paragraph depth=0

And now, you can put the power of GitHub Copilot to work in your preferred environment with a free trial. Try GitHub Copilot for yourself.

#### `p:16` kind=heading heading_level=2 depth=0

Free for verified students and maintainers of popular open source projects

#### `p:17` kind=paragraph depth=0

GitHub Copilot wouldn’t be possible without GitHub’s vibrant community of students and creators. To support and give back to those communities, we’re making GitHub Copilot available for free to verified students and maintainers of popular open source projects.

#### `p:18` kind=paragraph depth=0

If you’re a student and want to participate in the program, apply for the GitHub Student Pack to get started. And if you’re an open source maintainer, check out our FAQ to see if you qualify to start using GitHub Copilot at no cost.

#### `p:19` kind=heading heading_level=2 depth=0

Coming to companies later this year

#### `p:20` kind=paragraph depth=0

GitHub Copilot is our first step toward empowering developers with AI. Starting today, it’s now available to all developers, and we’ll begin offering it to companies later this year. 🚀

#### `p:21` kind=heading heading_level=2 depth=0

Tags:

#### `p:22` kind=list_item list_type=ul depth=0

GitHub Copilot

#### `p:23` kind=heading heading_level=2 depth=0

Written by


## 参考答案（g: 引用）

标题 `g:title`：GitHub Copilot is generally available to all developers

#### `g:0` kind=paragraph depth=0

We’re making GitHub Copilot, an AI pair programmer that suggests code in your editor, generally available to all developers for $10 USD/month or $100 USD/year. It will also be free to use for verified students and maintainers of popular open source projects.

#### `g:1` kind=paragraph depth=0

At GitHub, it’s part of our mission to build technology that makes developers happy. Since the launch of GitHub Copilot technical preview last year, it’s become abundantly clear that AI is one of the best tools to empower the next generation of developers.

#### `g:2` kind=paragraph depth=0

Already, AI is acting as a copilot in our daily lives. It’s helping us write emails and essays, automatically generate photo albums of our loved ones, and even acts as a digital assistant to help us order groceries. But until now, AI has stopped short of improving code, leaving the process of developing software almost completely manual.

#### `g:3` kind=paragraph depth=0

That’s changing now. Today, I am thrilled to announce that we are making GitHub Copilot generally available to individual developers. Your AI pair programmer is here.

#### `g:4` kind=paragraph depth=0

With GitHub Copilot, for the first time in the history of software, AI can be broadly harnessed by developers to write and complete code. Just like the rise of compilers and open source, we believe AI-assisted coding will fundamentally change the nature of software development, giving developers a new tool to write code easier and faster so they can be happier in their lives.

#### `g:5` kind=quote depth=0

Do you want to start using GitHub Copilot today? Get started with a free trial, and check out our pricing plans. It’s free to use for verified students and maintainers of popular open source software.

#### `g:6` kind=heading heading_level=2 depth=0

The wait is over

#### `g:7` kind=paragraph depth=0

We specifically designed GitHub Copilot as an editor extension to make sure nothing gets in the way of what you’re doing. GitHub Copilot distills the collective knowledge of the world’s developers into an editor extension that suggests code in real time, to help you stay focused on what matters most: building great software.

#### `g:8` kind=paragraph depth=0

When you type code or comments, GitHub Copilot suggests the next line of code. But it’s not only a single word or line of code. GitHub Copilot can suggest complete methods, boilerplate code, whole unit tests, and even complex algorithms.

#### `g:9` kind=paragraph depth=0

GitHub Copilot enables developers to

#### `g:10` kind=list_item list_type=ul depth=0

Get AI-based coding suggestions: Get code suggestions that match a project’s context and style conventions, and cycle through different options to decide what to accept, reject, or edit.

#### `g:11` kind=list_item list_type=ul depth=0

Use your preferred environment: Integrate GitHub Copilot with popular editors, including Neovim, JetBrains IDEs, Visual Studio, and Visual Studio Code as an unobtrusive extension.

#### `g:12` kind=list_item list_type=ul depth=0

Code confidently in unfamiliar territory: Code in new languages or try something new, and let GitHub Copilot suggest syntax and code in dozens of languages—so you can spend more time learning by doing.

#### `g:13` kind=paragraph depth=0

With more than 1.2 million developers in our technical preview over the last 12 months, people who started using GitHub Copilot quickly told us it became an indispensable part of their daily workflows. In files where it’s enabled, nearly 40% of code is being written by GitHub Copilot in popular coding languages, like Python—and we expect that to increase. That’s creating more time and space for developers to focus on solving bigger problems and building even better software.

#### `g:14` kind=paragraph depth=0

And now, you can put the power of GitHub Copilot to work in your preferred environment with a free trial. Try GitHub Copilot for yourself.

#### `g:15` kind=heading heading_level=2 depth=0

Free for verified students and maintainers of popular open source projects

#### `g:16` kind=paragraph depth=0

GitHub Copilot wouldn’t be possible without GitHub’s vibrant community of students and creators. To support and give back to those communities, we’re making GitHub Copilot available for free to verified students and maintainers of popular open source projects.

#### `g:17` kind=paragraph depth=0

If you’re a student and want to participate in the program, apply for the GitHub Student Pack to get started. And if you’re an open source maintainer, check out our FAQ to see if you qualify to start using GitHub Copilot at no cost.

#### `g:18` kind=heading heading_level=2 depth=0

Coming to companies later this year

#### `g:19` kind=paragraph depth=0

GitHub Copilot is our first step toward empowering developers with AI. Starting today, it’s now available to all developers, and we’ll begin offering it to companies later this year. 🚀


## 网页源证据（s: 引用，与 judge 所见完全一致）

> **注意：源证据被截断**。未展示部分不可当作"缺失"的证据；相关维度请标 partial，decision 不得 pass。

#### `s:0` <li> /html/body/div[1]/header/div[1]/div/nav/ul/li[1]

Changelog

#### `s:1` <li> /html/body/div[1]/header/div[1]/div/nav/ul/li[2]

Docs

#### `s:2` <li> /html/body/div[1]/header/div[1]/div/nav/ul/li[3]

Customer stories

#### `s:3` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]

AI & ML

	AI & MLLearn about artificial intelligence and machine learning across the GitHub ecosystem and the wider industry.
	
		Generative AILearn how to build with generative AI.
		GitHub CopilotChange how you work with GitHub Copilot.
		LLMsEverything developers need to know about LLMs.
		Machine learningMachine learning tips, tricks, and best practices.
	

	How AI code generation worksExplore the capabilities and benefits of AI code generation and how it can improve your developer experience.Learn more



#### `s:4` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]

AI & MLLearn about artificial intelligence and machine learning across the GitHub ecosystem and the wider industry.
	
		Generative AILearn how to build with generative AI.
		GitHub CopilotChange how you work with GitHub Copilot.
		LLMsEverything developers need to know about LLMs.
		Machine learningMachine learning tips, tricks, and best practices.
	


#### `s:5` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/div/p

Learn about artificial intelligence and machine learning across the GitHub ecosystem and the wider industry.

#### `s:6` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[1]

Generative AILearn how to build with generative AI.

#### `s:7` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[1]/p

Learn how to build with generative AI.

#### `s:8` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[2]

GitHub CopilotChange how you work with GitHub Copilot.

#### `s:9` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[2]/p

Change how you work with GitHub Copilot.

#### `s:10` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[3]

LLMsEverything developers need to know about LLMs.

#### `s:11` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[3]/p

Everything developers need to know about LLMs.

#### `s:12` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[4]

Machine learningMachine learning tips, tricks, and best practices.

#### `s:13` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[1]/ul/li[4]/p

Machine learning tips, tricks, and best practices.

#### `s:14` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[2]

How AI code generation worksExplore the capabilities and benefits of AI code generation and how it can improve your developer experience.Learn more

#### `s:15` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[1]/ul/li[2]/p

Explore the capabilities and benefits of AI code generation and how it can improve your developer experience.

#### `s:16` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]

Developer skills

	Developer skillsResources for developers to grow in their skills and careers.
	
		Application developmentInsights and best practices for building apps.
		Career growthTips & tricks to grow as a professional developer.
		GitHubImprove how you use GitHub at work.
		GitHub EducationLearn how to move into your first professional role.
		Programming languages & frameworksStay current on what’s new (or new again).
	

	Get started with GitHub documentationLearn how to start building, shipping, and maintaining software with GitHub.Learn more



#### `s:17` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]

Developer skillsResources for developers to grow in their skills and careers.
	
		Application developmentInsights and best practices for building apps.
		Career growthTips & tricks to grow as a professional developer.
		GitHubImprove how you use GitHub at work.
		GitHub EducationLearn how to move into your first professional role.
		Programming languages & frameworksStay current on what’s new (or new again).
	


#### `s:18` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/div/p

Resources for developers to grow in their skills and careers.

#### `s:19` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[1]

Application developmentInsights and best practices for building apps.

#### `s:20` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[1]/p

Insights and best practices for building apps.

#### `s:21` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[2]

Career growthTips & tricks to grow as a professional developer.

#### `s:22` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[2]/p

Tips & tricks to grow as a professional developer.

#### `s:23` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[3]

GitHubImprove how you use GitHub at work.

#### `s:24` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[3]/p

Improve how you use GitHub at work.

#### `s:25` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[4]

GitHub EducationLearn how to move into your first professional role.

#### `s:26` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[4]/p

Learn how to move into your first professional role.

#### `s:27` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[5]

Programming languages & frameworksStay current on what’s new (or new again).

#### `s:28` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[1]/ul/li[5]/p

Stay current on what’s new (or new again).

#### `s:29` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[2]

Get started with GitHub documentationLearn how to start building, shipping, and maintaining software with GitHub.Learn more

#### `s:30` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[2]/ul/li[2]/p

Learn how to start building, shipping, and maintaining software with GitHub.

#### `s:31` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]

Engineering

	EngineeringGet an inside look at how we’re building the home for all developers.
	
		Architecture & optimizationDiscover how we deliver a performant and highly available experience across the GitHub platform.
		Engineering principlesExplore best practices for building software at scale with a majority remote team.
		InfrastructureGet a glimpse at the technology underlying the world’s leading AI-powered developer platform.
		Platform securityLearn how we build security into everything we do across the developer lifecycle.
		User experienceFind out what goes into making GitHub the home for all developers.
	

	How we use GitHub to be more productive, collaborative, and secureOur engineering and security teams do some incredible work. Let’s take a look at how we use GitHub to be more productive, build collaboratively, and shift security left.Learn more



#### `s:32` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]

EngineeringGet an inside look at how we’re building the home for all developers.
	
		Architecture & optimizationDiscover how we deliver a performant and highly available experience across the GitHub platform.
		Engineering principlesExplore best practices for building software at scale with a majority remote team.
		InfrastructureGet a glimpse at the technology underlying the world’s leading AI-powered developer platform.
		Platform securityLearn how we build security into everything we do across the developer lifecycle.
		User experienceFind out what goes into making GitHub the home for all developers.
	


#### `s:33` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/div/p

Get an inside look at how we’re building the home for all developers.

#### `s:34` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[1]

Architecture & optimizationDiscover how we deliver a performant and highly available experience across the GitHub platform.

#### `s:35` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[1]/p

Discover how we deliver a performant and highly available experience across the GitHub platform.

#### `s:36` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[2]

Engineering principlesExplore best practices for building software at scale with a majority remote team.

#### `s:37` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[2]/p

Explore best practices for building software at scale with a majority remote team.

#### `s:38` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[3]

InfrastructureGet a glimpse at the technology underlying the world’s leading AI-powered developer platform.

#### `s:39` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[3]/p

Get a glimpse at the technology underlying the world’s leading AI-powered developer platform.

#### `s:40` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[4]

Platform securityLearn how we build security into everything we do across the developer lifecycle.

#### `s:41` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[4]/p

Learn how we build security into everything we do across the developer lifecycle.

#### `s:42` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[5]

User experienceFind out what goes into making GitHub the home for all developers.

#### `s:43` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[1]/ul/li[5]/p

Find out what goes into making GitHub the home for all developers.

#### `s:44` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[2]

How we use GitHub to be more productive, collaborative, and secureOur engineering and security teams do some incredible work. Let’s take a look at how we use GitHub to be more productive, build collaboratively, and shift security left.Learn more

#### `s:45` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[3]/ul/li[2]/p

Our engineering and security teams do some incredible work. Let’s take a look at how we use GitHub to be more productive, build collaboratively, and shift security left.

#### `s:46` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]

Enterprise software

	Enterprise softwareExplore how to write, build, and deploy enterprise software at scale.
	
		AutomationAutomating your way to faster and more secure ships.
		CI/CDGuides on continuous integration and delivery.
		CollaborationTips, tools, and tricks to improve developer collaboration.
		DevOpsDevOps resources for enterprise engineering teams.
		DevSecOpsHow to integrate security into the SDLC.
		Governance & complianceEnsuring your builds stay clean.
	

	GitHub recognized as a Leader in the Gartner® Magic Quadrant™ for AI Code AssistantsLearn why Gartner positioned GitHub as a Leader for the second year in a row.Learn more



#### `s:47` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]

Enterprise softwareExplore how to write, build, and deploy enterprise software at scale.
	
		AutomationAutomating your way to faster and more secure ships.
		CI/CDGuides on continuous integration and delivery.
		CollaborationTips, tools, and tricks to improve developer collaboration.
		DevOpsDevOps resources for enterprise engineering teams.
		DevSecOpsHow to integrate security into the SDLC.
		Governance & complianceEnsuring your builds stay clean.
	


#### `s:48` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/div/p

Explore how to write, build, and deploy enterprise software at scale.

#### `s:49` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[1]

AutomationAutomating your way to faster and more secure ships.

#### `s:50` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[1]/p

Automating your way to faster and more secure ships.

#### `s:51` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[2]

CI/CDGuides on continuous integration and delivery.

#### `s:52` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[2]/p

Guides on continuous integration and delivery.

#### `s:53` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[3]

CollaborationTips, tools, and tricks to improve developer collaboration.

#### `s:54` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[3]/p

Tips, tools, and tricks to improve developer collaboration.

#### `s:55` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[4]

DevOpsDevOps resources for enterprise engineering teams.

#### `s:56` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[4]/p

DevOps resources for enterprise engineering teams.

#### `s:57` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[5]

DevSecOpsHow to integrate security into the SDLC.

#### `s:58` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[5]/p

How to integrate security into the SDLC.

#### `s:59` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[6]

Governance & complianceEnsuring your builds stay clean.

#### `s:60` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[1]/ul/li[6]/p

Ensuring your builds stay clean.

#### `s:61` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[2]

GitHub recognized as a Leader in the Gartner® Magic Quadrant™ for AI Code AssistantsLearn why Gartner positioned GitHub as a Leader for the second year in a row.Learn more

#### `s:62` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[4]/ul/li[2]/p

Learn why Gartner positioned GitHub as a Leader for the second year in a row.

#### `s:63` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]

News & insights

	News & insightsKeep up with what’s new and notable from inside GitHub.
	
		Company newsAn inside look at news and product updates from GitHub.
		ProductThe latest on GitHub’s platform, products, and tools.
		OctoverseInsights into the state of open source on GitHub.
		PolicyThe latest policy and regulatory changes in software.
		ResearchData-driven insights around the developer ecosystem.
		The libraryOlder news and updates from GitHub.
	

	Unlocking the power of unstructured data with RAGLearn how to use retrieval-augmented generation (RAG) to capture more insights.Learn more



#### `s:64` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]

News & insightsKeep up with what’s new and notable from inside GitHub.
	
		Company newsAn inside look at news and product updates from GitHub.
		ProductThe latest on GitHub’s platform, products, and tools.
		OctoverseInsights into the state of open source on GitHub.
		PolicyThe latest policy and regulatory changes in software.
		ResearchData-driven insights around the developer ecosystem.
		The libraryOlder news and updates from GitHub.
	


#### `s:65` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/div/p

Keep up with what’s new and notable from inside GitHub.

#### `s:66` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[1]

Company newsAn inside look at news and product updates from GitHub.

#### `s:67` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[1]/p

An inside look at news and product updates from GitHub.

#### `s:68` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[2]

ProductThe latest on GitHub’s platform, products, and tools.

#### `s:69` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[2]/p

The latest on GitHub’s platform, products, and tools.

#### `s:70` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[3]

OctoverseInsights into the state of open source on GitHub.

#### `s:71` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[3]/p

Insights into the state of open source on GitHub.

#### `s:72` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[4]

PolicyThe latest policy and regulatory changes in software.

#### `s:73` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[4]/p

The latest policy and regulatory changes in software.

#### `s:74` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[5]

ResearchData-driven insights around the developer ecosystem.

#### `s:75` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[5]/p

Data-driven insights around the developer ecosystem.

#### `s:76` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[6]

The libraryOlder news and updates from GitHub.

#### `s:77` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[1]/ul/li[6]/p

Older news and updates from GitHub.

#### `s:78` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[2]

Unlocking the power of unstructured data with RAGLearn how to use retrieval-augmented generation (RAG) to capture more insights.Learn more

#### `s:79` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[5]/ul/li[2]/p

Learn how to use retrieval-augmented generation (RAG) to capture more insights.

#### `s:80` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]

Open Source

	Open SourceEverything open source on GitHub.
	
		GitThe latest Git updates.
		MaintainersSpotlighting open source maintainers.
		Social impactHow open source is driving positive change.
		GamingExplore open source games on GitHub.
	

	An introduction to innersourceOrganizations worldwide are incorporating open source methodologies into the way they build and ship their own software.Learn more



#### `s:81` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]

Open SourceEverything open source on GitHub.
	
		GitThe latest Git updates.
		MaintainersSpotlighting open source maintainers.
		Social impactHow open source is driving positive change.
		GamingExplore open source games on GitHub.
	


#### `s:82` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/div/p

Everything open source on GitHub.

#### `s:83` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[1]

GitThe latest Git updates.

#### `s:84` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[1]/p

The latest Git updates.

#### `s:85` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[2]

MaintainersSpotlighting open source maintainers.

#### `s:86` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[2]/p

Spotlighting open source maintainers.

#### `s:87` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[3]

Social impactHow open source is driving positive change.

#### `s:88` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[3]/p

How open source is driving positive change.

#### `s:89` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[4]

GamingExplore open source games on GitHub.

#### `s:90` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[1]/ul/li[4]/p

Explore open source games on GitHub.

#### `s:91` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[2]

An introduction to innersourceOrganizations worldwide are incorporating open source methodologies into the way they build and ship their own software.Learn more

#### `s:92` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[6]/ul/li[2]/p

Organizations worldwide are incorporating open source methodologies into the way they build and ship their own software.

#### `s:93` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]

Security

	SecurityStay up to date on everything security.
	
		Application securityApplication security, explained.
		Supply chain securityDemystifying supply chain security.
		Vulnerability researchUpdates from the GitHub Security Lab.
		Web application securityHelpful tips on securing web applications.
	

	The enterprise guide to AI-powered DevSecOpsLearn about core challenges in DevSecOps, and how you can start addressing them with AI and automation.Learn more



#### `s:94` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]

SecurityStay up to date on everything security.
	
		Application securityApplication security, explained.
		Supply chain securityDemystifying supply chain security.
		Vulnerability researchUpdates from the GitHub Security Lab.
		Web application securityHelpful tips on securing web applications.
	


#### `s:95` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/div/p

Stay up to date on everything security.

#### `s:96` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[1]

Application securityApplication security, explained.

#### `s:97` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[1]/p

Application security, explained.

#### `s:98` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[2]

Supply chain securityDemystifying supply chain security.

#### `s:99` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[2]/p

Demystifying supply chain security.

#### `s:100` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[3]

Vulnerability researchUpdates from the GitHub Security Lab.

#### `s:101` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[3]/p

Updates from the GitHub Security Lab.

#### `s:102` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[4]

Web application securityHelpful tips on securing web applications.

#### `s:103` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[1]/ul/li[4]/p

Helpful tips on securing web applications.

#### `s:104` <li> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[2]

The enterprise guide to AI-powered DevSecOpsLearn about core challenges in DevSecOps, and how you can start addressing them with AI and automation.Learn more

#### `s:105` <p> /html/body/div[1]/header/div[2]/nav/div/ul/li[7]/ul/li[2]/p

Learn about core challenges in DevSecOps, and how you can start addressing them with AI and automation.

#### `s:106` <h2> /html/body/div[1]/header/nav/div/h2

Categories

#### `s:107` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]

AI & ML

	BackAI & MLLearn about artificial intelligence and machine learning across the GitHub ecosystem and the wider industry.
	
		Generative AILearn how to build with generative AI.
		GitHub CopilotChange how you work with GitHub Copilot.
		LLMsEverything developers need to know about LLMs.
		Machine learningMachine learning tips, tricks, and best practices.
	

	How AI code generation worksExplore the capabilities and benefits of AI code generation and how it can improve your developer experience.Learn more



#### `s:108` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]

BackAI & MLLearn about artificial intelligence and machine learning across the GitHub ecosystem and the wider industry.
	
		Generative AILearn how to build with generative AI.
		GitHub CopilotChange how you work with GitHub Copilot.
		LLMsEverything developers need to know about LLMs.
		Machine learningMachine learning tips, tricks, and best practices.
	


#### `s:109` <p> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/div/p

Learn about artificial intelligence and machine learning across the GitHub ecosystem and the wider industry.

#### `s:110` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[1]

Generative AILearn how to build with generative AI.

#### `s:111` <p> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[1]/p

Learn how to build with generative AI.

#### `s:112` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[2]

GitHub CopilotChange how you work with GitHub Copilot.

#### `s:113` <p> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[2]/p

Change how you work with GitHub Copilot.

#### `s:114` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[3]

LLMsEverything developers need to know about LLMs.

#### `s:115` <p> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[3]/p

Everything developers need to know about LLMs.

#### `s:116` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[4]

Machine learningMachine learning tips, tricks, and best practices.

#### `s:117` <p> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[1]/ul/li[4]/p

Machine learning tips, tricks, and best practices.

#### `s:118` <li> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[2]

How AI code generation worksExplore the capabilities and benefits of AI code generation and how it can improve your developer experience.Learn more

#### `s:119` <p> /html/body/div[1]/header/nav/div/ul[1]/li[1]/ul/li[2]/div/p

Explore the capabilities and benefits of AI code generation and how it can improve your developer experience.

#### `s:120` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]

Developer skills

	BackDeveloper skillsResources for developers to grow in their skills and careers.
	
		Application developmentInsights and best practices for building apps.
		Career growthTips & tricks to grow as a professional developer.
		GitHubImprove how you use GitHub at work.
		GitHub EducationLearn how to move into your first professional role.
		Programming languages & frameworksStay current on what’s new (or new again).
	

	Get started with GitHub documentationLearn how to start building, shipping, and maintaining software with GitHub.Learn more



#### `s:121` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]

BackDeveloper skillsResources for developers to grow in their skills and careers.
	
		Application developmentInsights and best practices for building apps.
		Career growthTips & tricks to grow as a professional developer.
		GitHubImprove how you use GitHub at work.
		GitHub EducationLearn how to move into your first professional role.
		Programming languages & frameworksStay current on what’s new (or new again).
	


#### `s:122` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/div/p

Resources for developers to grow in their skills and careers.

#### `s:123` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[1]

Application developmentInsights and best practices for building apps.

#### `s:124` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[1]/p

Insights and best practices for building apps.

#### `s:125` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[2]

Career growthTips & tricks to grow as a professional developer.

#### `s:126` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[2]/p

Tips & tricks to grow as a professional developer.

#### `s:127` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[3]

GitHubImprove how you use GitHub at work.

#### `s:128` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[3]/p

Improve how you use GitHub at work.

#### `s:129` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[4]

GitHub EducationLearn how to move into your first professional role.

#### `s:130` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[4]/p

Learn how to move into your first professional role.

#### `s:131` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[5]

Programming languages & frameworksStay current on what’s new (or new again).

#### `s:132` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[1]/ul/li[5]/p

Stay current on what’s new (or new again).

#### `s:133` <li> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[2]

Get started with GitHub documentationLearn how to start building, shipping, and maintaining software with GitHub.Learn more

#### `s:134` <p> /html/body/div[1]/header/nav/div/ul[1]/li[2]/ul/li[2]/div/p

Learn how to start building, shipping, and maintaining software with GitHub.

#### `s:135` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]

Engineering

	BackEngineeringGet an inside look at how we’re building the home for all developers.
	
		Architecture & optimizationDiscover how we deliver a performant and highly available experience across the GitHub platform.
		Engineering principlesExplore best practices for building software at scale with a majority remote team.
		InfrastructureGet a glimpse at the technology underlying the world’s leading AI-powered developer platform.
		Platform securityLearn how we build security into everything we do across the developer lifecycle.
		User experienceFind out what goes into making GitHub the home for all developers.
	

	How we use GitHub to be more productive, collaborative, and secureOur engineering and security teams do some incredible work. Let’s take a look at how we use GitHub to be more productive, build collaboratively, and shift security left.Learn more



#### `s:136` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]

BackEngineeringGet an inside look at how we’re building the home for all developers.
	
		Architecture & optimizationDiscover how we deliver a performant and highly available experience across the GitHub platform.
		Engineering principlesExplore best practices for building software at scale with a majority remote team.
		InfrastructureGet a glimpse at the technology underlying the world’s leading AI-powered developer platform.
		Platform securityLearn how we build security into everything we do across the developer lifecycle.
		User experienceFind out what goes into making GitHub the home for all developers.
	


#### `s:137` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/div/p

Get an inside look at how we’re building the home for all developers.

#### `s:138` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[1]

Architecture & optimizationDiscover how we deliver a performant and highly available experience across the GitHub platform.

#### `s:139` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[1]/p

Discover how we deliver a performant and highly available experience across the GitHub platform.

#### `s:140` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[2]

Engineering principlesExplore best practices for building software at scale with a majority remote team.

#### `s:141` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[2]/p

Explore best practices for building software at scale with a majority remote team.

#### `s:142` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[3]

InfrastructureGet a glimpse at the technology underlying the world’s leading AI-powered developer platform.

#### `s:143` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[3]/p

Get a glimpse at the technology underlying the world’s leading AI-powered developer platform.

#### `s:144` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[4]

Platform securityLearn how we build security into everything we do across the developer lifecycle.

#### `s:145` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[4]/p

Learn how we build security into everything we do across the developer lifecycle.

#### `s:146` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[5]

User experienceFind out what goes into making GitHub the home for all developers.

#### `s:147` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[1]/ul/li[5]/p

Find out what goes into making GitHub the home for all developers.

#### `s:148` <li> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[2]

How we use GitHub to be more productive, collaborative, and secureOur engineering and security teams do some incredible work. Let’s take a look at how we use GitHub to be more productive, build collaboratively, and shift security left.Learn more

#### `s:149` <p> /html/body/div[1]/header/nav/div/ul[1]/li[3]/ul/li[2]/div/p

Our engineering and security teams do some incredible work. Let’s take a look at how we use GitHub to be more productive, build collaboratively, and shift security left.


## 填写入口

打开同目录 `human_labels.blind.json`，找到 `case_id` 为 `cal-github-missing_paragraph` 的条目，填写 decision 与五个维度，保存。
本案卷不含任何 judge/silver/程序分数；填写前请勿查阅其他输出文件，避免锚定。
