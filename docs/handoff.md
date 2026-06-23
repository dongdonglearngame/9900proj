# COMP9900 Project 18 — 项目交接文档

> 用途:把这个 P18 项目的**核心逻辑 + 最新理解**浓缩成一份自包含文档,方便在新对话里直接继续讨论。
> 标 **【客户最新】** 的是 2026-06-17 和 client 开会后定下来的、会影响做法的关键点。

---

## 0. 一句话概括

做一个**本地小 LLM 的反事实解释工具**:模型在 EmoBench(情绪智能多选题)上选了某个答案,用户指定一个他更期望的答案(**foil**),系统去找**最小、且有意义的 scenario 改动**,让模型从原答案**翻(flip)**到这个 foil;然后**对比多种反事实策略**,失败的也作为 negative results 报告。

---

## 1. 背景与团队

- **Client:** Dr Thao Le(UNSW XAI 研究者;GitHub: `thaole25`)。
- **Team:** 9900-F09C-ALMOND,6 人。
- **产出:** 一个全栈 web 工具(React + FastAPI + Ollama + SQLite),生成反事实解释,并把多种策略放在同一框架下做公平对比。

**成员/角色:**
- Xi Shen(z5547747)— Scrum Master / Backend(=我,引擎+评估负责人)
- Meitong Zhou — Project Manager / Backend
- Yidi Wu — Backend;Zijie Cai — Backend;Jiaxin Liu — Backend
- Jiajun Wang — Frontend

---

## 2. 硬约束(底线,任何方案都不能违反)

- **黑盒 only**:只通过 Ollama(inference-only)访问目标模型,**拿不到 gradients / 内部权重**。
- **不微调(no fine-tuning)、不上云、不跑付费 API**(不用 ChatGPT/Claude 等)。**【客户最新】**
- **只用免费本地开源模型**(Llama 3.2 3B / Phi-3-mini / Qwen2.5 3B 这一档)。
- **必须能在没有独显的 CPU 笔记本上跑**。
- **不做大规模训练,也没有 HPC(Katana)**;优先选**不需要训练**的方法。**【客户最新】**

---

## 3. 任务定义(精确)

- **EmoBench**:手工构建的情绪智能 benchmark,**多选题(4 选 1)**,按 accuracy 评分。两个维度:**EU**(Emotional Understanding)/ **EA**(Emotional Application),共 **3 个 task type**。
- **题目数 ≈ 400,不是 200。【客户最新】** (3 个 task 里,**两个 task 共享同一套题**,第三个 task 是**另一套 200 题**,合计约 400。旧 proposal 里写的 200 需全文改。)
- **用户流程**:选 scenario → 模型给出答案(4 选 1) → 用户选一个 **foil**(他希望模型选的那个) → 系统找**最小改动**让模型翻到 foil。
- **"Flip" 的定义(4 选一)= argmax 变成 foil**(foil 要赢过另外 3 个选项),**不是**二分类那种"概率跌破 50%"。
- **"预算内没找到" 是一个合法 RESULT,不是 error。**

**贯穿全程的具体例子(Regina):**
```
Scenario: Regina's best friend recently broke up with her longtime partner
and is texting Regina in the middle of the night expressing feelings of loneliness.

Choices: A. Ignore the texts and continue sleeping
         B. Tell her friend to seek professional help
         C. Stay up and lend a listening ear        ← 用户选它做 foil
         D. Suggest her friend find a new partner

模型原答案 = A。目标 = 找最小改动把模型从 A 翻到 C。
经典最小改动: "middle of the night" → "early evening"
→ 解释:模型原来的建议靠的是「时间(很晚)」,不是「朋友难过」。
```

---

## 4. 核心架构(分层)

```
React 前端 → FastAPI 后端(controller / service / data-access)
           → 反事实策略框架(围绕一个共享 harness)
           → 本地推理层(Ollama,localhost)   ← 全程本地,无外部 API
```

- **前端组件**:Task & Model Selector、Scenario Input、Prediction View、Foil Selector、Explanation View(彩色 diff + metrics)、Dashboard。
- **Service 层**:`PredictionService`(包住 harness、缓存预测)、`CounterfactualService`(跑某个策略 + 共享后处理流水线)、`EvaluationService`(baseline accuracy + 各项 metrics + 回答 dashboard 查询)。
- **SQLite 四张表**:`scenarios`、`predictions`(按 scenario×model×template 缓存)、`counterfactuals`(改后 scenario + typed diff + strategy id + 成功标志)、`metrics`(每条解释的分数 + strategy id)。
  - **【客户最新】SQLite 是加分项,不是必须**;时间不够直接读原始 **CSV 也完全可以**。

---

## 5. 最关键的设计原则(它让这个项目从"几个实现"变成"一个 study")

- 六个策略**共享**:① 冻结 harness `target_predict(scenario, choices)`——**stateless、固定 prompt、temperature 0、永远看不到 foil、constrained parser**;② 共享的 **greedy-restoration minimiser**;③ 共享的 **fluency / perplexity gate**;④ 共享的 **metrics 模块**。
- **六个策略唯一被允许不同的地方,是「怎么提出编辑(how they propose edits)」**。minimality、fluency、metrics 都用**同一把尺**量 → 这才是 head-to-head 对比公平的根据。
- 策略内部那个 **proposer/editor 可以看到 foil、也可以保留自己的(精简)历史**;但它**无权判定成功**——只有干净的冻结目标模型真的翻到 foil 才算成功。

---

## 6. 六个策略(S1–S6)

| | 名称 | 一句话 idea | 改编自 |
|---|---|---|---|
| **S1** | Word-level greedy 基线(MVP) | 对 scenario 做很小的词级改动,每改一次就用冻结模型验证,直到翻 | 机械 brute-force |
| **S2** | LLM propose–verify | editor LLM 根据 foil 直接提"更可能奏效"的改写,逐个验证,可选保留失败记忆 | Bhattacharjee/FIZLE 2024 |
| **S3** | Control-code 生成 | 按固定编辑类型(否定/插入/删除/替换/重组)批量生成候选,再过冻结模型筛 | Polyjuice / Wu 2021 |
| **S4** | Importance-guided infilling | 用 occlusion 在目标模型上找最重要的词 → mask → 用现成模型 infill → 验证 → 缩小 | 黑盒 MiCE / Ross 2021 + Jin 2020 |
| **S5** | Population search | 维护一群候选**编辑集**,靠 mutation/crossover 进化,fitness=翻成功−改动大小 | Alzantot 2018(对抗 GA) |
| **S6** | Concept-level 因果编辑 | 只改一个高层概念(时间/地点/关系/紧迫/强度),其余固定=干净因果干预 | Gat et al. ICLR 2024 |

**各策略关键注意点:**

- **S1**:简单、透明、强基线(其余都跟它比);缺点是调用多、句子可能生硬。**先做这个,作为 MVP 把整个框架打通。**
- **S2**:搜索更高效、更通顺;但很依赖 3B 模型的 instruction-following,且容易 over-edit(和最小化目标冲突)。
- **S3**:可控多样、能告诉用户"哪种编辑类型最能翻";但被预设类型限制。**注意:Polyjuice 本身要训练 GPT-2,而我们不训练;insertion/restructure 较难**——按"行有余力再试"对待。
- **S4(重点厘清过)**:
  - **importance = 在目标模型上做 occlusion**(盖词看答案概率变化,**无需 gradient**);可先用 POS 跳过 a/the、on/in/at 这种虚词省调用。
  - **infill 用预训练 BERT 的 `fill-mask`,off-the-shelf、不训练、CPU 上跑得动**(BERT 的原生 MLM 就是干这个的;110M 比我们要跑的 3B 还小)。**千万别 fine-tune**(S4 本来就是 MiCE 的免训练黑盒版)。
  - BERT 单个 `[MASK]` 只擅长填**一个词**;**多词 span**(如 4 词换 2 词)交给本地 LLM 或 seq2seq。
  - S4 本质偏**替换(substitution)**:重写被标记的词,不能在没标记的位置凭空插新句。
- **S5(重点厘清过)**:
  - **genome = 变长的 edit-set,不是定长**。一个个体 3 个编辑、另一个 4 个编辑可以并存;**add/remove-edit mutation** 就是在"改几处"之间移动的机制。
  - **crossover = 组合两个 parent 的好基因(高 fitness 的那几条编辑)**,之后要 **repair**(同一 span 冲突的只留一条、重新 apply、验证通顺)。
  - **fitness 的平滑信号 = foil 的概率/logprob**(没有 logprobs,fitness 是平的 → 退化成随机搜索)。fitness ≈ `翻成功(argmax==foil)+ foil logprob − 改动大小 − (可选)perplexity`。
  - 最费算力、对参数(种群大小/代数)敏感;价值是给出搜索能力的上界。
- **S6**:可解释性最强、最贴 EmoBench("模型翻是因为时间变了"比"第七个词变了"更像人话);minimality 在**概念粒度**上也量一份。**需要额外一个 LLM 步骤来抽取/定义概念**;只用 prompted-generation 变体(原文那个学 embedding 的 matching 变体要训练 → 不做)。

---

## 7. 共享后处理流水线(任何策略翻成功后都走这条)

1. **Greedy-restoration minimiser**:把原句和改后句 diff 成 typed spans,逐个 span 试着还原成原文(先 clause 级、再 word 级),**只有"还原后会丢掉 flip"的改动才保留**;纯插入(没有原词可还原)用一次受约束的 LLM 调用缩短。
2. **Fluency gate**:用一个**隔离的小 LM 算 perplexity**(数值前向,不是聊天式"通顺吗"判断);只有低于阈值才做受约束 polish(不加新内容、不变长),polish 后**重新验证 flip + 重测编辑距离**,变差就回滚。
3. **Metrics**:flip success、token edit distance(绝对值)、changed-word fraction(按长度归一)、perplexity、调用次数;连同 strategy id 存起来;**"not found" 也存**。
- 含义:**策略只需找到「一个」能翻的改动**,把它修到最小这件事交给共享 minimiser。

---

## 8. 已敲定的关键技术决策(避免在新对话里重新纠结)

- **Ollama vs vLLM → 用 Ollama**。约束是"无 GPU 笔记本";vLLM 的吞吐优势只在 GPU 上;混后端(GGUF vs fp16)会破坏"同一个函数"的前提。
- **logprobs(从 harness 暴露每个选项的概率)→ 要用**。它**不改变模型的选择**(是从产生 argmax 的同一次前向里**抽取**出来的,不是反馈进去的);给所有搜索策略一个平滑梯度,**对 S5 尤其关键**。**flip 判据仍用 argmax** 以保证公平;CPU 上走 llama.cpp 的 `n_probs`;答案用单字母 token。
- **diff-match-patch / difflib → 是基础设施,不是第 6 个策略**。用于 typed diff、彩色 UI、编辑距离 metric、按 diff 重叠去重。配成 word-level + semantic cleanup。
- **Attack ≠ Explanation(重要观念)**:S5 改编自对抗样本方法,但**目标相反**。对抗攻击 = 找"人看不出来、却能骗过模型"的扰动(meaning-preserving、imperceptible);**我们要的反事实解释 = 改一个真有意义的情境因素、模型跟着翻**,让用户看懂决策靠什么。所以 fitness 要奖励**最小 + 通顺 + 有意义**的改动,"成功"指 faithful 的翻转。**不要用 "attacker" 的框架/措辞。**

---

## 9. 计划 / Sprint

- **Sprint 1(基础)**:用 **S1(greedy)把整条框架端到端打通**,**Week 5 Progressive Demo A 之前**完成(harness、数据导入、单模型 baseline、S1 引擎、单页 UI、可插拔策略接口)。
- **Sprint 2(最重)**:在共享接口上加更多策略、metrics、对比视图、多模型 + warm-up、异步任务。
- **Sprint 3(最轻)**:跑完整对比(含失败)、做完 dashboard、Docker Compose、文档、Final Demo(Week 10)。
- **工程规范(client 要求)**:小颗粒 commit 关联 GitHub Issue;feature/策略走独立分支 + PR review;仓库共享给 `thaole25`。

---

## 10. 客户最新反馈汇总(2026-06-17)— 最重要

1. **不必六个全做、也不必"一人一个"**;**学期末能做出 2–3 个就很好**;**progress > results**,失败也写进报告(negative results 是 first-class)。
2. **只用 Ollama 免费本地模型,不花钱用 API**。
3. **不做大规模训练、不用 HPC**;优先选不需要训练的做法(S3/S5/S6 谨慎)。
4. **先做 S1**,Week 5 前完成,再加 1–2 个。
5. **EmoBench 题目 ≈ 400 不是 200**(回去核对数据集)。
6. **架构图箭头要修**(S1→框架那里有双箭头、标签压在线条中间 → 方向理顺、标签靠边)。
7. **SQLite 可选**,只用 CSV 也行(能做 SQL 更好)。
8. **别在 slides/report 上花太多时间**;proposal 基本可以交了,别过度打磨。

---

## 11. proposal/仓库待办(全局)

- [ ] **200 → ~400**:P18-1、lit review、dashboard(P18-16)、SP6、Data layer 等多处统一改。
- [ ] **去掉"one strategy per member"措辞**(1.1、F5、F8 都有),改成"先 S1、按 capacity 增量加做"。
- [ ] **架构图改箭头**(双箭头 / 中间标签)。
- [ ] **S5 措辞**:fitness 用 foil logprob + 最小化 + 通顺;flip = argmax==foil;genome 为变长 edit-set。
- [ ] **S4 措辞**:occlusion 在目标模型、infill 用现成预训练 BERT、不 fine-tune。
- [ ] 路线上**优先免费本地 + 免训练**;S3(训练)/S5(算力)/S6(额外 LLM)标注"行有余力再试"。

---

*技术栈一句话:React(前端)+ FastAPI(后端三层)+ Ollama(本地推理)+ SQLite/CSV(存储);一个冻结 harness + 一套共享 minimiser/fluency/metrics + 六个只在"怎么提编辑"上不同的策略。*
