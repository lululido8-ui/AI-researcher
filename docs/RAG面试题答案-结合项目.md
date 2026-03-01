# AI Agent 面试题库 - RAG 系统篇 · 答案（结合本项目）

> 本文档基于 gpt-researcher 项目代码，每题均包含：原理阐述 + 项目中的具体实现位置与用法，便于面试时结合项目回答。

---

## 第一部分：RAG 核心原理（必考）

### Q1: 请解释 RAG 的工作原理。与直接对 LLM 进行微调相比，RAG 主要解决了什么问题？有哪些优势？

**知识点：**

RAG（Retrieval-Augmented Generation）的核心是：**先用检索从外部知识库拿到相关文档，再把这些文档作为上下文喂给 LLM 生成回答**。公式化理解就是：`Answer = LLM(Query; Retrieved_Docs)`。

与微调相比，RAG 主要解决三类问题：

1. **知识截止与时效性**：微调后模型参数固定，知识有截止日期；RAG 的知识在检索侧，可随时更新文档/索引，无需重新训练。
2. **幻觉与可追溯性**：模型容易“瞎编”；RAG 强制模型基于检索到的原文生成，便于引用溯源、降低幻觉。
3. **领域/企业知识注入**：微调成本高、需要大量标注数据；RAG 只需构建领域知识库即可低成本接入专业知识。

优势概括：**可更新、可溯源、易扩展、训练成本低**。

**项目结合：**

- 本项目是典型的“先检索后生成”流水线：`ResearchConductor.conduct_research()` 先通过多检索器 + 网页抓取拿到原始内容，再经 `ContextCompressor`（RAG 压缩管道）得到高质量上下文，最后在 `ReportGenerator.write_report()` 中把上下文注入 Prompt 生成报告。
- 与微调的对比在业务上的体现：我们给系统接了**通信领域论文的本地知识库**，只需更新向量库即可让报告更专业，无需对底层 LLM 做微调；报告里的引用都来自真实检索到的 URL/文档，可点击验证，符合 RAG 的可追溯性设计。

---

### Q2: 一个完整的 RAG 流水线包含哪些关键步骤？请从数据准备到最终生成，详细描述整个过程。

**知识点：**

完整 RAG 流水线可拆成**离线**和**在线**两段：

**离线（数据准备）：**  
1. 数据采集与清洗（爬虫、PDF 解析等）  
2. 文档分块（chunking）：按固定长度或语义切分  
3. 向量化：用 Embedding 模型将每块编码为向量  
4. 写入向量库：建立索引，支持相似度检索  

**在线（查询到生成）：**  
1. 查询理解/改写（可选）：同义词扩展、子问题分解  
2. 检索：用查询向量在向量库中做相似度检索，得到 Top-K 文档块  
3. 重排序/过滤（可选）：用更精细的模型或规则对候选做精排、去噪  
4. 上下文构建：将检索结果格式化为 Prompt 的一部分  
5. 生成：LLM 基于「问题 + 上下文」生成最终答案  
6. 后处理（可选）：引用标注、格式校验  

**项目结合：**

- **离线**：本地知识库（如通信论文）通过 `VectorStoreWrapper.load(documents)` 处理：先转成 LangChain `Document`，再用 `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` 分块，最后向量化并写入向量库（见 `vector_store/vector_store.py`）。
- **在线**：  
  - 查询规划：`plan_research_outline()` → `generate_search_queries_prompt()` 生成子查询（相当于查询改写/子问题分解）。  
  - 检索：多检索器（Tavily、arXiv、MCP 等）搜索 → 抓取页面内容 → 得到原始文档列表。  
  - 压缩与过滤：`gpt_researcher/context/compression.py` 中的 `ContextCompressor` 做分块 → `EmbeddingsFilter` 按相似度过滤 → `ContextualCompressionRetriever` 输出最终上下文。  
  - 生成：`generate_report_prompt()` 把 `context` 和 `question` 拼成 Prompt，调用 LLM 写报告。  
- 若开启 `CURATE_SOURCES`，在检索与生成之间还有一步 **SourceCurator**：用 LLM 对来源做相关性、权威性、时效性评估，相当于“重排序/过滤”环节。

---

### Q3: 在构建知识库时，文本切块策略至关重要。你会如何选择合适的切块大小和重叠长度？这背后有什么权衡？

**知识点：**

- **chunk_size（块大小）**：  
  - 太小：语义碎片化，单块信息不足，检索到的“句群”不完整。  
  - 太大：噪声多，容易超过单次上下文窗口，且相似度被整块平均，区分度下降。  
  - 常见范围：256～1024 token（或约 200～800 字符），学术/技术文档可偏大（512～1000）。  

- **chunk_overlap（重叠长度）**：  
  - 适当重叠可避免关键信息被切在块边界而丢失。  
  - 重叠过大则重复内容多，浪费向量存储和检索算力。  
  - 通常取 chunk_size 的 10%～20%。  

- **切分方式**：按句/段切比单纯按字符切更保语义；`RecursiveCharacterTextSplitter` 会先按分隔符（如 `\n\n`、`\n`）尝试，再按字符回退，在通用场景下效果较好。

**项目结合：**

- 项目里有两处明确的切块配置：  
  - **RAG 压缩管道**（`context/compression.py`）：`RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)`，即 1000 字符块、100 字符重叠，适合中等长度网页与文档。  
  - **向量库写入**（`vector_store/vector_store.py`）：`_split_documents` 默认 `chunk_size=1000, chunk_overlap=200`，重叠更大，保证边界上的关键信息尽量落在某一块内。  
- 通信领域论文若段落较长、公式多，可以在同一套逻辑下把 chunk_size 调小（如 512）、overlap 调大（如 150），在「语义完整」和「检索精度」之间做权衡，并配合 `similarity_threshold` 做过滤。

---

### Q4: 如何选择一个合适的嵌入模型？评估一个 Embedding 模型的好坏有哪些指标？

**知识点：**

- **选择维度**：  
  - 语言与领域：多语言任务选多语言模型；领域敏感时可考虑领域微调或领域数据评估。  
  - 向量维度与延迟：维度高一般表达力更强但检索更慢；需在准确率和延迟/成本间权衡。  
  - 上下文长度：是否支持长文档一次编码（如 8k token）。  

- **常用评估指标**：  
  - **MTEB（Massive Text Embedding Benchmark）**：综合多任务排名。  
  - **检索任务**：Recall@K、MRR、NDCG，在标准检索数据集（如 BEIR）上测。  
  - **语义相似度任务**：Spearman 与 Pearson 与人工标注的相关性。  
  - **领域数据**：自建 query–doc 对，看 Top-K 命中率、业务侧满意度。  

**项目结合：**

- 嵌入模型通过配置注入，不写死在代码里：`Memory` 类（`memory/embeddings.py`）根据 `embedding_provider` 和 `model` 初始化对应 LangChain Embeddings（如 OpenAI、Cohere、Azure 等），配置来自 `EMBEDDING` 环境变量（格式 `provider:model`）。  
- 因此“选型”在项目里体现为：在默认配置或环境变量中指定 `EMBEDDING=openai:text-embedding-3-small`（或其它模型）。  
- 项目用嵌入做两件事：一是 `ContextCompressor` 里的相似度过滤（与 `similarity_threshold` 配合）；二是向量库的写入与检索。若要在通信领域优化，可针对通信论文构建小规模 query–doc 测试集，对比不同 embedding 的 Recall@5/10 和业务反馈，再决定是否更换为领域更强的模型。

---

## 第二部分：检索优化（算法岗重点）

### Q5: 除了基础的向量检索，你还知道哪些可以提升 RAG 检索质量的技术？

**知识点：**

- **混合检索（Hybrid Retrieval）**：向量检索 + 稀疏检索（如 BM25）。向量擅长语义，BM25 擅长精确词匹配，融合（如 RRF）可提升鲁棒性。  
- **多路召回 + 重排**：多路检索（不同检索器/不同 chunk_size）合并后再用 Cross-Encoder 或 LLM 做精排。  
- **查询改写/扩展**：同义词、子问题分解、假设性文档嵌入（HyDE）等，提升 query 与 doc 的匹配度。  
- **上下文压缩**：检索多取一些候选，再用 LLM 或相似度过滤压缩到真正相关的部分，减轻“Lost in the Middle”。  
- **元数据过滤**：按时间、来源、类型等过滤后再做向量检索，减少无关文档。  

**项目结合：**

- **多路检索**：`get_retrievers()` 支持配置多个检索器（如 `RETRIEVER=tavily,arxiv,mcp`），各检索器结果汇总后再进入后续管道，相当于多路召回。  
- **查询扩展/子问题分解**：`plan_research_outline()` 用 `generate_search_queries_prompt()` 让 LLM 根据主任务生成多条子查询（`generate_sub_queries()`），每条子查询单独检索，等价于子问题分解提升覆盖度。  
- **上下文压缩**：`ContextCompressor` 使用 LangChain 的 `DocumentCompressorPipeline`：先 `RecursiveCharacterTextSplitter` 分块，再用 `EmbeddingsFilter` 按相似度阈值过滤，最后用 `ContextualCompressionRetriever` 输出，是典型的“多召回 + 相似度过滤”的压缩流程。  
- **来源重排/过滤**：`SourceCurator.curate_sources()` 用 LLM 对已抓取来源做评估（Relevance、Credibility、Currency、Quantitative Value），保留高质量来源再参与报告生成，相当于检索后的 LLM 重排。

---

### Q6: 请解释 "Lost in the Middle" 问题。它描述了 RAG 中的什么现象？有什么方法可以缓解？

**知识点：**

- **现象**：当注入的上下文很长时，LLM 对**中间段**的利用率明显低于开头和结尾，导致关键信息若在中间容易被忽略，从而答非所问或遗漏关键点。  

- **缓解思路**：  
  1. **减少注入长度**：检索时少而精（Top-K 小、相似度阈值高），或先压缩再注入。  
  2. **重排序**：把最相关的片段排在开头或结尾；或按相关性排序后只取前 N 段。  
  3. **结构化注入**：按主题/段落分块并加小标题，便于模型“定位”到中间内容。  
  4. **分阶段生成**：先根据部分上下文生成大纲或要点，再对关键段落二次检索与生成，避免一次性塞入超长上下文。  

**项目结合：**

- 项目通过**控制上下文长度与质量**间接缓解 Lost in the Middle：  
  - `ContextCompressor` 的 `EmbeddingsFilter` 用 `similarity_threshold`（默认 0.35，可由 `SIMILARITY_THRESHOLD` 配置）过滤低相关块，只保留高相关片段，减少总长度。  
  - `async_get_context` 的 `max_results` 限制返回文档数（如 5），进一步控制注入量。  
  - `TOTAL_WORDS` 等配置限制报告对上下文的“用量预期”，从 Prompt 设计上约束模型关注最相关部分。  
- 若要进一步针对“中间”优化，可以在构造报告 Prompt 时对检索结果按相似度分数排序，把得分最高的 1～2 段放在 Prompt 的靠前或靠后位置，或对长报告采用分章节检索、分章节生成的策略（项目里已有按 section 的研究与写作，可在此基础上显式控制每段上下文的顺序）。

---

### Q7: 在什么场景下，你会选择使用图数据库或知识图谱来增强或替代传统的向量数据库检索？

**知识点：**

- **适用场景**：  
  - 强关系、多跳推理：如“某协议的演进”“某作者的合作网络”“因果关系链”，图上的边天然表示关系，适合多跳查询。  
  - 实体与关系明确：知识图谱通常有实体、关系、属性，便于做结构化约束（如只查某年的论文、某会议）。  
  - 需要解释路径：图检索可返回“路径”，便于生成可解释的引用链。  

- **与向量检索的关系**：图检索与向量检索可结合（GraphRAG）：先用向量召回相关子图或实体，再在子图上做关系扩展或推理，最后把子图/路径描述注入 LLM。  

**项目结合：**

- 当前项目主要使用**向量检索 + 关键词检索（多检索器）**，没有显式使用图数据库或知识图谱。  
- 若在通信领域做增强，可以在现有 RAG 之上加一层“图增强”：  
  - 把通信论文中的实体（协议、方法、作者、会议）和关系（引用、改进、对比）建知识图谱。  
  - 检索时：先向量检索得到相关文档/段落，再根据文档中的实体在图中做 1～2 跳扩展，把扩展到的相关论文或概念一并放入上下文。  
- 这样既保留现有 RAG 的语义检索能力，又用图解决“关系与演进”类问题，适合综述型、技术路线类报告。

---

## 第三部分：评估与优化（通用）

### Q8: 如何全面地评估一个 RAG 系统的性能？请分别从检索和生成两个阶段提出评估指标。

**知识点：**

- **检索阶段**：  
  - **Recall@K / Precision@K**：检索到的 K 个文档中有多少相关、是否覆盖了所有相关文档。  
  - **MRR、NDCG**：考虑排序质量的指标。  
  - **Context Relevance / Context Precision**：检索到的上下文与问题的相关度、以及是否被生成阶段有效利用。  

- **生成阶段**：  
  - **Faithfulness（忠实度）**：生成内容是否都能从上下文中推出，有无幻觉。  
  - **Answer Relevancy**：回答与问题的匹配程度。  
  - **引用正确性**：引用是否对应真实来源、是否支持对应陈述。  

- **端到端**：RAGAS 等框架会组合 faithfulness、answer_relevancy、context_recall、context_precision 等，对 RAG 管道做统一评估。  

**项目结合：**

- 项目目前没有内置自动化 RAG 评估脚本，但评估思路可以直接套用：  
  - **检索**：对同一批研究问题，记录每个子查询的检索结果（URL/文档 id），人工或规则标注相关/不相关，算 Recall@5、Precision@5；或对比“仅向量库”与“向量库+网络检索”的差异。  
  - **生成**：对报告中的关键事实做引用追溯，检查 URL 是否可访问、内容是否支持陈述（对应 faithfulness + 引用正确性）；可用 RAGAS 的 faithfulness 在“问题 + 检索上下文 + 生成回答”三元组上自动打分。  
  - 通信领域可加**领域指标**：术语正确性、是否引用到我们注入的本地论文、技术深度评分等，用于迭代 Prompt 和检索参数（如 `similarity_threshold`、chunk_size）。

---

### Q9: 传统的 RAG 流程是"先检索后生成"，你是否了解一些更复杂的 RAG 范式，比如在生成过程中进行多次检索或自适应检索？

**知识点：**

- **迭代/多轮 RAG**：根据首轮生成的内容或中间结论，再发起新一轮检索，再生成，如此往复（类似 ReAct 中的多轮工具调用）。  
- **自适应检索**：根据当前生成到哪一段、需要什么类型信息，动态决定是否检索、用什么 query、检索哪类来源。  
- **Self-RAG 等**：在生成过程中插入“检索判断”步骤，只在模型不确定时才检索。  
- **HyDE**：用模型先生成假设性答案，用假设答案的向量去检索，再基于真实检索结果生成最终答案，提升 query 与 doc 的语义对齐。  

**项目结合：**

- 项目在“研究”层面已经有多轮与自适应色彩：  
  - **子查询多轮检索**：`plan_research_outline()` 生成多条子查询，每条子查询独立检索并汇总（`_process_sub_query`），相当于对同一主任务的多次检索。  
  - **深度研究模式**（Deep Research）：在 `deep_research.py` 中会做多轮搜索与生成，根据上一轮结果再生成新的问题再检索，形成迭代。  
  - **MCP 工具选择**：`MCPToolSelector` 用 LLM 根据当前 query 从众多 MCP 工具中选出 2～3 个最相关的再调用，可视为“按需选择检索源”的自适应行为。  
- 报告生成阶段仍是“一次性注入上下文再生成”，若要做真正的“生成中再检索”，可以在 WriterAgent 写某一节时，根据当前小节主题再调一次 RAG，把新检索结果追加到该节的上下文中，这需要在现有架构上增加“按节检索”的接口和调用点。

---

## 第四部分：工程实践（开发岗重点）

### Q10: RAG 系统在实际部署中可能面临哪些挑战？

**知识点：**

- **数据与一致性**：文档更新、去重、版本管理；增量更新时新旧文档分布不一致导致检索偏差。  
- **延迟与成本**：检索延迟（尤其大规模向量库）、LLM 调用延迟与成本、多轮检索时的累积成本。  
- **可观测性**：检索结果是否合理、生成是否忠实于上下文、引用是否有效，需要日志与评估。  
- **安全与合规**：敏感数据脱敏、权限控制、审计。  
- **扩展性**：向量库与检索服务的水平扩展、多租户隔离。  

**项目结合：**

- **延迟**：多检索器 + 多子查询会放大延迟；项目用 `asyncio.gather` 并行处理子查询、MCP 的 `fast` 策略缓存首次 MCP 结果以减轻重复调用。  
- **成本**：通过 `fast_llm` / `smart_llm` / `strategic_llm` 分层使用、`MAX_ITERATIONS` 限制子查询数、`CURATE_SOURCES` 可选关闭来控制。  
- **数据更新**：本地知识库（通信论文）若需增量更新，需考虑重新分块与重新向量化，以及是否做增量索引（取决于所用向量库）；若全量重建，可配合版本号或时间戳避免新旧分布剧烈变化。  
- **可观测性**：项目有 `stream_output`、`print_agent_output` 及日志，可看到每步子查询、检索来源、流式输出；若要量化评估，可在此基础上接 RAGAS 或自建评估脚本。

---

### Q11: 了解搜索系统吗？和 RAG 有什么区别？

**知识点：**

- **传统搜索系统**：用户输入 query → 检索（倒排/向量/混合）→ 返回**文档列表或摘要**，用户自行阅读和筛选。目标通常是排序质量（NDCG、CTR 等）。  
- **RAG**：用户输入 query → 检索得到文档/片段 → 将文档作为上下文输入 LLM → 返回**直接答案或结构化文本**。目标是“答案正确、有用、可溯源”。  

区别概括：搜索是“找文档”，RAG 是“用文档生成答案”；RAG 的检索是为生成服务的，评估时除了检索质量还要看生成质量和忠实度。

**项目结合：**

- 项目里“检索”部分（多检索器、Tavily/arXiv/MCP、网页抓取）很像搜索系统：输入 query，输出 URL + 摘要/内容。  
- 与纯搜索的差异在于：检索结果不直接给用户，而是进入 `ContextCompressor` 做压缩和过滤，再作为 `generate_report_prompt()` 的 context 输入，由 LLM 生成**报告**；用户看到的是报告 + 引用链接，而不是搜索列表。  
- 因此可以一句话概括：我们用的是“搜索系统作为 RAG 的检索前端”，整体仍然是 RAG 管线。

---

### Q12: 知道或者使用过哪些开源 RAG 框架比如 Ragflow？如何选择合适场景？

**知识点：**

- 常见开源 RAG/检索框架：LangChain/LlamaIndex、Ragflow、Dify、FastGPT、Haystack 等。  
- **选型考虑**：数据源与格式、是否要可视化编排、是否要内置评估、部署形态（单机/分布式）、与现有代码（如 LangChain）的兼容性。  

**项目结合：**

- 本项目没有用 Ragflow 等一体式 RAG 平台，而是基于 **LangChain** 的组件自建 RAG 管道：  
  - `RecursiveCharacterTextSplitter`、`EmbeddingsFilter`、`ContextualCompressionRetriever`、`DocumentCompressorPipeline` 均来自 LangChain（或 langchain_classic）。  
  - 向量存储通过 `VectorStoreWrapper` 抽象，可换不同后端。  
- 选择自建而非 Ragflow 的原因更偏向：需要与多智能体工作流（LangGraph）、自定义研究流程（子查询、MCP、SourceCurator）深度耦合，框架的灵活性优先；若未来只做“单轮问答 + 知识库”，可以再评估 Ragflow 等以降低运维和搭建成本。

---

## 第五部分：RAG 进阶技术（真题补充）

### Q13: 构建向量检索库时如何处理时间衰减对召回的影响？

**知识点：**

- **问题**：新文档少、旧文档多时，若不做处理，检索容易偏向旧文档；或用户更关心“最新”信息。  
- **思路**：  
  1. **时间加权**：在相似度分数上乘以时间衰减因子（如指数衰减），使越新的文档得分越高。  
  2. **过滤**：检索时加时间范围 filter（如只查最近 N 年），再在候选内做向量排序。  
  3. **混合**：先按时间筛出一批候选，再在这批候选里做向量检索；或向量分与时间分线性/非线性融合。  
  4. **索引分层**：按时间建多个索引或段，查询时优先查近期段，再决定是否查历史段。  

**项目结合：**

- 当前向量检索（`ContextCompressor`、`VectorStoreWrapper`）没有显式的时间衰减或时间过滤，主要依赖相似度阈值和 `max_results`。  
- 在 Prompt 侧有“时效性”引导：`generate_search_queries_prompt()` 里会注入当前日期（`datetime.now(timezone.utc)`），引导 LLM 生成带时间意识的搜索词；`curate_sources` 的 EVALUATION GUIDELINES 中有 “Currency: Prefer recent information”，相当于在来源筛选阶段偏好新内容。  
- 若要在向量库层面做时间衰减，可以在：  
  - 写入时给每个 chunk 打上时间戳（如论文发表年），检索时在向量库的 filter 中加时间范围；或  
  - 检索到候选后，在 Python 里对分数做时间加权再重排，再取 Top-K。这两处都可以在不改核心检索逻辑的前提下接入。

---

### Q14: RAG 中知识库搭建，对知识库的文件文档进行动态增量更新，怎么来避免新旧文档的分布不一致导致的检索偏差问题？

**知识点：**

- **问题**：新文档用新模型或新 chunk 策略写入，旧文档是历史模型/策略，导致嵌入空间不一致，新文档容易被“冷落”或旧文档被过度召回。  
- **思路**：  
  1. **统一嵌入模型与参数**：增量时仍用同一 embedding 模型和同一 chunk 策略，避免分布漂移。  
  2. **定期全量重建**：按周期用当前模型全量重算向量并重建索引，牺牲一定实时性换一致性。  
  3. **分层索引**：新文档进“新索引”，查询时双路检索再合并；或逐步把旧索引迁移到新模型。  
  4. **归一化/校准**：对新旧向量做简单归一化或域适应，减轻分布差异（实现成本较高）。  

**项目结合：**

- 本地知识库的写入在 `VectorStoreWrapper.load()`：分块与向量化都依赖当前配置的 `Memory`（即当前 `EMBEDDING`）。只要增量更新时**不更换** embedding 模型和 chunk 参数，新旧文档就处在同一嵌入空间，分布一致。  
- 若必须更换模型（如从 text-embedding-ada 迁到 text-embedding-3-small），建议对全量文档用新模型重算并重建索引，而不是只对新文档用新模型；否则会出现“新旧分布不一致”的检索偏差。  
- 项目没有内置增量更新逻辑（如只对新文件做 add_documents），若后续加增量，应保证：同一批文档用同一套 splitter 和 embedding 配置，并做好文档 id 去重，避免同一文档新旧版本同时存在。

---

### Q15: RAG 如果有噪声怎么办？

**知识点：**

- **噪声来源**：无关文档被召回、单文档内无关段落、HTML/格式噪音、重复内容、过时或错误信息。  
- **应对**：  
  1. **检索阶段**：提高相似度阈值、减少 Top-K、使用混合检索或重排减少误召。  
  2. **过滤阶段**：规则过滤（如长度、语言、来源域名）、LLM 过滤（如 SourceCurator 式评估）。  
  3. **生成阶段**：Prompt 中强调“仅基于给定上下文”“不要使用上下文外的信息”，降低模型对噪声的采纳。  
  4. **后处理**：引用校验、事实抽检、与知识库二次核对。  

**项目结合：**

- **相似度过滤**：`ContextCompressor` 的 `EmbeddingsFilter` 用 `similarity_threshold`（默认 0.35）过滤低相关块，直接减少进入 Prompt 的噪声。  
- **来源筛选**：`SourceCurator.curate_sources()` 用 LLM 按 Relevance、Credibility、Currency、Quantitative Value 等维度筛选，并明确 “DO NOT rewrite, summarize, or condense”，保留原文但去掉明显无关或低质来源。  
- **Prompt 约束**：报告类 Prompt 中强调基于给定信息、包含引用链接，从生成侧约束“少用噪声”。  
- 若噪声仍大，可：提高 `SIMILARITY_THRESHOLD`、减小 `max_results`、或对通信领域启用更严格的来源白名单（如仅信任特定会议/期刊域名）。

---

### Q16: 讲一下 BM25 算法原理

**知识点：**

- BM25 是一种**稀疏检索**算法，基于词袋与 TF-IDF 思想，对 query 和文档计算相关性分数。  
- 公式（简化）：对 query 中每个词 t，在文档 D 中的贡献为：  
  `IDF(t) * (f(t,D) * (k1+1)) / (f(t,D) + k1*(1-b+b*|D|/avgdl))`  
  - `f(t,D)`：t 在 D 中的词频  
  - `|D|`、`avgdl`：文档长度与平均文档长度  
  - `k1`、`b`：调节 TF 饱和与长度归一化的超参  
- 特点：可解释、无需训练、对精确词匹配和稀有词敏感；多与向量检索做混合（如 RRF 融合）。  

**项目结合：**

- 当前项目的检索以**向量检索 + 多检索器（搜索引擎 API）**为主：Tavily、arXiv、SerpAPI 等返回的是搜索引擎自身的排序结果（很多搜索引擎底层就含 BM25 或类似稀疏算法），我们没有再单独实现 BM25。  
- 若要在本地知识库上做混合检索，可以在 `VectorStoreWrapper` 或 `ContextCompressor` 前加一层：用 BM25 对同一批文档做稀疏检索，得到 BM25 分数后与向量分数做 RRF 或线性融合，再取 Top-K。这需要为文档维护一份分词后的文本或 BM25 索引（如用 rank_bm25 或 Elasticsearch）。

---

### Q17: 是否做过意图识别？如果要做意图识别，可以怎么实现？

**知识点：**

- **意图识别**：判断用户 query 的意图类型（如事实问答、综述、比较、推荐、闲聊等），以便走不同 pipeline（如综述走多轮检索+长报告，事实问答走单轮检索+短答）。  
- **实现方式**：  
  1. 分类模型：用 BERT/小模型对 query 做多分类，输出意图标签。  
  2. LLM 判断：用 Prompt 让 LLM 输出意图类别或结构化字段，再根据结果分支。  
  3. 规则 + 关键词：针对明确意图设规则（如包含“对比”“优缺点”则走比较流程）。  

**项目结合：**

- 项目没有独立的“意图识别”模块，但有**语义层面的任务分流**：  
  - `choose_agent()` 根据用户 query 用 LLM 选择“Agent 类型 + 角色 Prompt”（如财经分析、学术研究等），相当于用 LLM 做一次粗粒度意图/领域识别。  
  - `plan_research_outline()` 和 `generate_search_queries_prompt()` 会根据主任务生成子查询和章节结构，隐含了“这是需要深度研究的任务”的假设。  
- 若要做显式意图识别，可以：在 `conduct_research` 入口处增加一步 LLM 或分类模型，输出如 `intent: factoid | survey | comparison`，再根据 intent 选择 `max_iterations`、是否开启深度研究、报告长度等，从而在不同 RAG 策略间切换。

---

### Q18: 介绍检索做的优化，具体追问子问题分解怎么做，有没有做意图识别？

**知识点：**

- 检索优化可从多路召回、查询改写、子问题分解、重排、过滤、时间与元数据等多方面讲。  
- **子问题分解**：把复杂 query 拆成多个子 query，分别检索再合并，能提高覆盖度和长尾信息召回。  
- 意图识别见 Q17。  

**项目结合：**

- **子问题分解**：  
  - 在 `actions/query_processing.py` 中，`plan_research_outline()` 会调用 `generate_sub_queries()`，后者使用 `generate_search_queries_prompt()` 让 LLM 根据主任务和（可选）父 query、report_type、已有 context 生成多条子查询（数量由 `max_iterations` 控制，默认 3）。  
  - 在 `skills/researcher.py` 中，`_get_context_by_web_search()` 会对每条 `sub_query` 分别执行 `_process_sub_query()`：搜索 → 抓取 → MCP（若启用）→ `context_manager.get_similar_content_by_query()`（RAG 压缩）→ 合并到总 context。  
  - 多智能体模式下，`EditorAgent.plan_research()` 会生成 sections（章节），每个 section 再作为 topic 进入子图做“研究→审查→修订”，相当于章节级子问题分解。  
- **意图识别**：见 Q17；当前用 `choose_agent()` 做角色/领域选择，没有单独的意图分类模块，但可以在此基础上加一层意图识别并驱动不同的检索深度与报告格式。

---

### Q19: 在 RAG 里的"召回-过滤-生成"三段式 pipeline 能细讲一下吗？

**知识点：**

- **召回**：用向量检索（或混合 BM25+向量）从大库中取出较多候选（如 Top-50），保证 recall。  
- **过滤**：对候选做精排或过滤，包括相似度阈值、重排模型、规则（时间、来源）、或 LLM 筛选，得到少量高质量片段（如 Top-5～10），减少噪声和长度。  
- **生成**：将过滤后的内容格式化为 Prompt 的 context，交给 LLM 生成最终答案。  

**项目结合：**

- **召回**：多检索器（Tavily、arXiv、MCP 等）搜索并抓取页面/文档，得到“原始文档列表”；对本地知识库则通过 `VectorStoreWrapper.asimilarity_search()` 或 `ContextCompressor` 使用的 `SearchAPIRetriever` 得到候选块。  
- **过滤**：  
  - 在 `ContextCompressor` 中：先分块，再用 `EmbeddingsFilter(embeddings, similarity_threshold)` 过滤低相似度块，`ContextualCompressionRetriever` 输出最终片段，等价于“相似度过滤”。  
  - 若开启 `CURATE_SOURCES`，`SourceCurator.curate_sources()` 用 LLM 对来源做多维度评估并保留 top `max_results`，相当于“LLM 过滤”。  
- **生成**：`generate_report_prompt()` 将过滤后的 context 与 question 拼成 Prompt，`ReportGenerator.write_report()` 调用 LLM 生成报告。  
- 因此项目 pipeline 可以明确对应为：**多路检索+抓取（召回）→ EmbeddingsFilter + 可选 SourceCurator（过滤）→ Report Prompt + LLM（生成）**。

---

### Q20: 介绍一下 function calling 和 MCP

**知识点：**

- **Function calling**：LLM 输出结构化“工具调用”（如工具名+参数），系统执行工具并把结果回填给 LLM，形成“模型决定调什么、系统执行”的闭环。常用于搜索、计算、查库等。  
- **MCP（Model Context Protocol）**：一种开放协议，统一“工具/数据源”的暴露方式，使不同前端（如 Cursor、Claude）能连接同一套工具服务；Agent 通过 MCP 发现并调用工具，而不必为每个环境写死接口。  

**项目结合：**

- **MCP**：项目集成了 MCP 检索器（`retrievers/mcp/retriever.py`）。`MCPRetriever` 的两阶段流程是：  
  1. **Tool Selection**：`MCPToolSelector` 使用 `generate_mcp_tool_selection_prompt()` 让 LLM 从所有 MCP 工具中选出 2～3 个最相关的工具（返回 JSON：selected_tools、relevance_score、reason）。  
  2. **Research Execution**：`MCPResearchSkill` 用选中的工具执行研究，相当于“LLM 选工具 + 执行工具”的 function-calling 式用法。  
- **Function calling**：MCP 研究执行阶段会调用 LangChain 或 MCP 客户端的工具调用接口，把“工具名 + 参数”交给 LLM 或执行器执行，与常见 function calling 模式一致。  
- 因此可以概括：我们通过 **MCP 协议接入外部工具（如通信领域专用数据源）**，在内部用 **LLM 做工具选择 + 工具执行**，实现可扩展的“检索+工具”能力。

---

### Q21: 在高并发查询 Agent 系统中，你会如何优化召回和生成阶段的延迟？

**知识点：**

- **召回**：向量索引优化（IVF、HNSW）、批量请求、缓存热门 query、多路召回并行、预计算或预热。  
- **生成**：模型与批处理、流式输出、缓存相同 query、缩短上下文、使用更小/更快模型做首轮生成。  
- **系统**：异步化、连接池、限流、队列与背压。  

**项目结合：**

- **召回**：  
  - 子查询级并行：`_process_sub_query` 在多个子查询上可用 `asyncio.gather` 并行执行，减少总等待时间。  
  - MCP 策略：`fast` 模式下首次 MCP 结果被缓存，后续子查询复用，减少重复 MCP 调用延迟。  
  - 向量库：若使用 FAISS/本地向量库，可调索引参数（如 nlist、nprobe）在延迟与 recall 间权衡；大规模时考虑分布式向量库。  
- **生成**：  
  - 分层模型：`fast_llm` 处理查询生成等轻量任务，`smart_llm` 只用于报告撰写，降低平均延迟与成本。  
  - 流式：`create_chat_completion(..., stream=True)` 配合 WebSocket 实现流式输出，首 token 延迟更低、体感更快。  
- **系统**：`rate_limiter.py` 对请求做限流，避免瞬时并发压垮 API；多任务时每个任务独立 `ChiefEditorAgent` 和 `GPTResearcher` 实例，通过 `task_id` 隔离，便于水平扩展。

---

### Q22: 如果让 agent 调用搜索引擎，如何避免无关结果影响回答？

**知识点：**

- **检索侧**：提高检索精度（更准的 query、更严格的过滤）、使用高质量或垂直搜索引擎、对结果做重排或过滤。  
- **生成侧**：在 Prompt 中强调“仅基于提供的上下文”“忽略无关内容”“引用需来自上下文”，并限制上下文长度使模型更聚焦。  
- **评估与闭环**：对来源做相关性标注或模型打分，过滤低分结果再注入。  

**项目结合：**

- **检索与过滤**：  
  - 子查询由 `generate_search_queries_prompt()` 生成，强调与任务相关，减少无关搜索词。  
  - 抓取到的内容进入 `ContextCompressor` 后，`EmbeddingsFilter` 按 `similarity_threshold` 过滤，只保留与当前子查询高相关的块。  
  - 可选 `SourceCurator.curate_sources()`：用 LLM 按 Relevance、Credibility、Currency、Quantitative Value 评估，只保留高质量来源，直接减少无关结果进入报告。  
- **Prompt**：报告生成 Prompt 中要求基于给定信息、包含引用、使用权威来源等，从生成侧约束“少用无关内容”。  
- **来源多样性**：配置多检索器（如 Tavily + arXiv + MCP）时，不同来源的无关结果会被其他来源的优质结果“稀释”；同时 `curate_sources` 的“多样性”要求也有助于避免单一噪声源主导。

---

以上 22 题均结合了本项目中的文件、类名、函数和配置，面试时可按“原理 + 我们项目里是在哪里、怎么做的”的结构回答，既体现理解深度，又体现落地经验。
