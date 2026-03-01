# 科学论文 AI 研究代理 — 技术调研报告

> 调研日期: 2026-03-01

---

## 目录

1. [arXiv API 与编程访问](#1-arxiv-api-与编程访问)
2. [IEEE Xplore API 与编程访问](#2-ieee-xplore-api-与编程访问)
3. [科学论文检索 API 概览](#3-科学论文检索-api-概览)
4. [开源科学研究代理项目](#4-开源科学研究代理项目)
5. [PDF 解析与科学文档理解](#5-pdf-解析与科学文档理解)
6. [电信/通信领域特定资源](#6-电信通信领域特定资源)
7. [推荐技术栈与实现路径](#7-推荐技术栈与实现路径)

---

## 1. arXiv API 与编程访问

### 1.1 官方 API

- **文档**: https://info.arxiv.org/help/api/user-manual.html
- **入口**: https://info.arxiv.org/help/api/index.html
- **使用条款**: https://info.arxiv.org/help/api/tou.html
- **响应格式**: Atom XML feed

**API 端点**:
```
http://export.arxiv.org/api/query?search_query=all:quantum&start=0&max_results=10
```

**查询语法**:
- `ti:` — 标题搜索
- `au:` — 作者搜索
- `abs:` — 摘要搜索
- `cat:` — 分类搜索（如 `cat:cs.AI`）
- `all:` — 全字段搜索
- 支持 `AND`, `OR`, `ANDNOT` 布尔运算符

### 1.2 Python 库

#### arxiv.py（推荐）

```bash
pip install arxiv
```

```python
import arxiv

client = arxiv.Client(
    page_size=100,
    delay_seconds=5.0,   # 请求间隔
    num_retries=5
)

# 关键词搜索
search = arxiv.Search(
    query="5G massive MIMO",
    max_results=50,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

for result in client.results(search):
    print(result.title)
    print(result.summary)         # 摘要
    print(result.pdf_url)         # PDF 链接
    print(result.published)       # 发布日期
    print(result.categories)      # 分类

    # 下载 PDF
    result.download_pdf(dirpath="./papers", filename="paper.pdf")

    # 下载 LaTeX 源码
    result.download_source(dirpath="./sources")

# 按 ID 查询
search_by_id = arxiv.Search(id_list=["2301.12345", "2302.67890"])
```

#### aioarxiv（异步版本）

```bash
pip install aioarxiv  # v0.2.1, 2025年4月发布, Python ≥ 3.9
```

### 1.3 速率限制与最佳实践

| 事项 | 建议 |
|------|------|
| 请求频率 | 每 5 秒不超过 1 个请求 |
| 大批量下载 | 使用 OAI-PMH 接口或 bulk data |
| 归属声明 | 必须注明: "Thank you to arXiv for use of its open access interoperability" |
| PDF 下载 | 通过 `result.download_pdf()` 或直接访问 `result.pdf_url` |
| 元数据批量获取 | 使用 OAI-PMH: `http://export.arxiv.org/oai2` |

### 1.4 PDF 全文获取流程

1. 通过 API 搜索获取论文元数据
2. 从 `pdf_url` 字段提取下载链接（格式: `https://arxiv.org/pdf/XXXX.XXXXX`）
3. 使用 `arxiv.py` 的 `download_pdf()` 方法下载
4. 使用 GROBID / Docling / PyMuPDF 解析 PDF 结构

---

## 2. IEEE Xplore API 与编程访问

### 2.1 官方 API

- **开发者门户**: https://developer.ieee.org/
- **API 文档**: https://developer.ieee.org/docs

**可用 API**:

| API | 说明 | 认证 |
|-----|------|------|
| Metadata Search API | 搜索 600 万+ 文档的元数据和摘要 | 需要 API Key |
| IEEE Open Access API | 获取开放获取论文全文 | 需要 API Key（免费内容） |
| Full-Text Access API | 获取付费论文全文 | 需要 API Key + 订阅 |
| DOI API | 通过 DOI 查询（每次最多 25 个） | 需要 API Key |

**API 端点示例**:
```
https://ieeexploreapi.ieee.org/api/v1/search/articles?querytext=5G&apikey=YOUR_KEY
```

### 2.2 免费可访问内容

- **元数据和摘要**: 注册 API Key 后可免费搜索
- **开放获取文章**: 通过 Open Access API 免费获取全文
- **全文**: 需要机构订阅或付费
- **文本数据挖掘**: 仅限非商业研究用途，需机构订阅

### 2.3 替代方案（绕过付费墙）

| 替代方案 | 说明 |
|----------|------|
| Semantic Scholar | 免费 API，覆盖 IEEE 论文元数据 |
| CrossRef | 通过 DOI 获取元数据 |
| Unpaywall | 查找论文的 OA 版本 |
| CORE | 300M+ 开放获取论文 |
| Google Scholar | 可找到预印本和作者自存档版本 |
| 作者个人主页 / ResearchGate | 许多作者自行上传了论文 |

---

## 3. 科学论文检索 API 概览

### 3.1 Semantic Scholar API

- **官网**: https://api.semanticscholar.org/
- **Python 库**: `pip install semanticscholar`
- **速率限制**: 100 请求 / 5 分钟（无认证）; 有 API Key 可提高

**核心功能**:
- 论文搜索、作者搜索
- 引用网络（被引/参考文献）
- 论文推荐
- SPECTER2 语义嵌入向量
- PDF URL 和摘要

```python
from semanticscholar import SemanticScholar

sch = SemanticScholar(api_key="YOUR_KEY")  # api_key 可选

# 搜索论文
results = sch.search_paper("OFDM channel estimation", limit=20)
for paper in results:
    print(paper.title)
    print(paper.abstract)
    print(paper.citationCount)
    print(paper.openAccessPdf)  # OA PDF 链接

# 按 ID 获取论文详情
paper = sch.get_paper("DOI:10.1109/xxx")

# 获取引用
citations = sch.get_paper_citations("CorpusId:12345")
references = sch.get_paper_references("CorpusId:12345")
```

**API 端点**:
```
GET https://api.semanticscholar.org/graph/v1/paper/search?query=5G+MIMO&limit=10
GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}
GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations
GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references
GET https://api.semanticscholar.org/graph/v1/author/search?query=author_name
GET https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{paper_id}
```

### 3.2 OpenAlex API

- **文档**: https://docs.openalex.org/
- **Python 库**: `pip install openalex-official`（也可用 `pyalex`）
- **定价**: 免费 API Key 提供 $1/天额度（约 1,000 搜索请求或 10,000 过滤请求）

**实体类型**: Works（论文）、Authors、Sources（期刊）、Institutions、Topics、Publishers、Funders

```python
import pyalex
from pyalex import Works

# 搜索论文
works = Works().search("massive MIMO beamforming").get()

# 带过滤的搜索
works = Works().filter(
    publication_year=2024,
    primary_location={"source": {"type": "journal"}},
    open_access={"is_oa": True}
).search("5G").get()

# 按 DOI 获取
work = Works()["https://doi.org/10.1109/xxx"]
```

**API 端点**:
```
GET https://api.openalex.org/works?search=quantum+computing&per_page=25
GET https://api.openalex.org/works?filter=publication_year:2024,open_access.is_oa:true
GET https://api.openalex.org/authors?search=author_name
GET https://api.openalex.org/sources?search=IEEE+Communications
```

**搜索功能**:
- 全文搜索（标题 + 摘要 + 全文）
- 布尔运算符（AND, OR, NOT）
- 精确匹配、模糊搜索、通配符、邻近搜索
- 语义搜索（beta，基于 AI 嵌入）

### 3.3 CrossRef API

- **文档**: https://github.com/CrossRef/rest-api-doc
- **Python 库**: `pip install habanero`（v2.2.0, 2025年2月）
- **速率限制**: 使用 "Polite Pool"（提供 email）可获得更快响应

```python
from habanero import Crossref

cr = Crossref(mailto="your@email.com")  # 启用 Polite Pool

# 搜索论文
results = cr.works(query="5G channel estimation", limit=20)

# 按 DOI 查询
work = cr.works(ids="10.1109/TCOMM.2023.xxx")

# 过滤搜索
results = cr.works(
    query="MIMO",
    filter={"from-pub-date": "2023", "type": "journal-article"}
)

# 期刊搜索
journals = cr.journals(query="IEEE Communications")
```

**API 端点**:
```
GET https://api.crossref.org/works?query=5G&rows=20
GET https://api.crossref.org/works/{DOI}
GET https://api.crossref.org/journals?query=IEEE
GET https://api.crossref.org/members/{member_id}/works
```

### 3.4 CORE API

- **官网**: https://core.ac.uk/services/api
- **数据量**: 300M+ 开放获取论文
- **Python 库**: `core_api_pylib`
- **认证**: 需注册免费 API Key

```python
import requests

API_KEY = "YOUR_CORE_API_KEY"
headers = {"Authorization": f"Bearer {API_KEY}"}

# 搜索论文
response = requests.get(
    "https://api.core.ac.uk/v3/search/works",
    params={"q": "5G MIMO", "limit": 10},
    headers=headers
)
results = response.json()
```

**特色**: 提供全文内容（不仅是元数据），支持 Elasticsearch 风格查询语法

### 3.5 Unpaywall API

- **官网**: https://unpaywall.org/api/v2
- **Python 库**: `pip install unpywall`
- **速率限制**: 100,000 次/天
- **用途**: 通过 DOI 查找论文的开放获取版本

```python
from unpywall import Unpywall

# 按 DOI 查找 OA 版本
result = Unpywall.get_paper("10.1109/TCOMM.2023.xxx", email="your@email.com")

# 获取 PDF 链接
pdf_url = Unpywall.get_pdf_link("10.1109/TCOMM.2023.xxx", email="your@email.com")

# 直接下载 PDF
Unpywall.download_pdf("10.1109/TCOMM.2023.xxx", email="your@email.com", filepath="paper.pdf")
```

**API 端点**:
```
GET https://api.unpaywall.org/v2/{DOI}?email=YOUR_EMAIL
```

### 3.6 Google Scholar 访问

Google Scholar 没有官方 API，可通过以下方式访问:

| 方法 | 库/工具 | 说明 |
|------|---------|------|
| scholarly | `pip install scholarly` | Python 库，模拟浏览器访问 |
| SerpAPI | 付费 API | 提供结构化 Google Scholar 数据 |
| ScraperAPI | 付费代理 | 避免被封锁 |

```python
from scholarly import scholarly

# 搜索论文
search_query = scholarly.search_pubs("5G massive MIMO")
paper = next(search_query)
print(paper['bib']['title'])
print(paper['bib']['abstract'])
print(paper['num_citations'])
```

> **注意**: Google Scholar 会积极封锁自动化访问，生产环境中建议优先使用 Semantic Scholar 或 OpenAlex。

### 3.7 API 对比总结

| API | 免费 | 全文 | 速率限制 | 覆盖范围 | 推荐指数 |
|-----|------|------|----------|----------|----------|
| arXiv | ✅ | ✅ PDF | 1 req/5s | 预印本(CS/物理/数学) | ⭐⭐⭐⭐⭐ |
| Semantic Scholar | ✅ | 部分 OA | 100/5min | 200M+ 论文 | ⭐⭐⭐⭐⭐ |
| OpenAlex | ✅(有限) | 链接 | $1/天免费额度 | 250M+ 论文 | ⭐⭐⭐⭐ |
| CrossRef | ✅ | 元数据 | Polite Pool | 150M+ DOI | ⭐⭐⭐⭐ |
| CORE | ✅ | ✅ 全文 | 需注册 | 300M+ OA 论文 | ⭐⭐⭐⭐ |
| Unpaywall | ✅ | OA 链接 | 100K/天 | DOI 索引 | ⭐⭐⭐⭐ |
| IEEE Xplore | 需Key | 付费 | 需注册 | IEEE 论文 | ⭐⭐⭐ |
| Google Scholar | ❌ API | 链接 | 易被封 | 最广 | ⭐⭐ |

---

## 4. 开源科学研究代理项目

### 4.1 PaperQA2（推荐）

- **GitHub**: https://github.com/future-house/paper-qa （8,192 stars）
- **许可**: Apache 2.0
- **安装**: `pip install paper-qa`

**核心功能**:
- 基于 RAG 的科学文档问答
- 自动 PDF 解析和文本提取
- 带引用的答案生成
- 元数据自动获取（引用数、撤稿检查）
- 支持本地和云端 LLM/嵌入模型
- Agentic RAG（迭代查询优化）

**工作流程**:
1. **论文搜索** — 生成候选论文并嵌入文本块
2. **证据收集** — 排序相关块，用 LLM 评分摘要
3. **答案生成** — 合并最佳摘要生成带引用的答案

```python
from paperqa import Settings, ask

answer = ask(
    "What are the latest advances in massive MIMO?",
    settings=Settings(llm="gpt-4o", paper_directory="./papers")
)
print(answer.formatted_answer)
```

### 4.2 Open Deep Research（LangGraph 实现）

- **来源**: LangChain 官方博客 (2025)
- **框架**: LangGraph
- **地址**: https://blog.langchain.com/open-deep-research

**三阶段流程**:
1. **范围界定 (Scoping)** — 理解研究问题
2. **研究 (Research)** — 使用代理灵活应用搜索策略
3. **写作 (Writing)** — 生成结构化报告

**特色**:
- 可配置模型、搜索工具和 MCP 服务器
- 支持产品对比、候选排名、事实验证等任务
- 基于 LangGraph 的有状态工作流

### 4.3 AGORA 框架

- **论文**: arXiv:2505.24354 (2025)
- **全称**: Agent Graph-based Orchestration for Reasoning and Assessment

**核心发现**: 简单方法（如 Chain-of-Thought）在许多场景下优于复杂方法，且计算开销显著更低。

### 4.4 DocuFetch

- **GitHub**: https://github.com/papabored/docufetch
- **功能**: 集成多个论文源的自动化发现和下载工具

**支持的数据源**:
- arXiv, Google Scholar, Semantic Scholar
- CrossRef, Unpaywall, PubMed
- CORE, DOAJ, OpenAIRE

### 4.5 Papers with Code 工具

- **GitHub**: https://github.com/paperswithcode
- **axcell**: 从 ML 论文中提取表格和结果
- **sota-extractor**: 提取 SOTA 结果的管道
- **paperswithcode-data**: 完整数据集（论文、代码链接、评估表）

### 4.6 GPT-Researcher（本项目）

本项目 (`gpt-researcher`) 本身就是一个研究代理框架，可以扩展以支持学术论文检索。可考虑:
- 添加专门的学术论文 Retriever
- 集成 arXiv / Semantic Scholar / CORE API
- 添加 PDF 解析流水线

---

## 5. PDF 解析与科学文档理解

### 5.1 工具对比

| 工具 | 类型 | 准确率 | 速度 | 特色 |
|------|------|--------|------|------|
| **GROBID** | ML 模型 | ~90% F1 | 中等 | 最成熟的科学 PDF 解析器 |
| **Docling** | ML 模型 | 97.9%（复杂表格） | 快 | IBM 开源，2025 年基准最佳 |
| **Marker** | 规则+ML | 高 | 快 | PDF → Markdown，适合 LLM |
| **pymupdf4llm** | 规则 | 中等 | 最快 | 轻量，LlamaIndex 集成 |
| **SciPDF Parser** | 基于 GROBID | 高 | 中等 | 专为科学论文设计 |
| **Unstructured** | ML | 100%(简单表) / 75%(复杂表) | 慢(51-141s) | 强 OCR，通用文档 |
| **LlamaParse** | 云服务 | 高 | 最快(~6s) | 云端处理，速度一致 |

### 5.2 GROBID（详细）

- **GitHub**: https://github.com/kermitt2/grobid （4,666 stars）
- **最新版**: v0.8.2 (2025年5月)
- **技术**: Java, CRF + Transformer 模型
- **Python 客户端**: `pip install grobid_client_python`

**提取能力**:
- 文档头部/元数据（标题、作者、摘要、关键词）
- 参考文献解析和链接
- 全文提取（保留文档结构）
- 引用上下文识别
- 图表标注提取

**部署方式**:
```bash
# Docker 部署
docker pull lfoppiano/grobid:0.8.2
docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.2

# Python 客户端使用
from grobid_client.grobid_client import GrobidClient

client = GrobidClient(config_path="./config.json")
client.process("processFulltextDocument", "./papers", output="./parsed")
```

### 5.3 Docling（推荐用于 LLM 场景）

```bash
pip install docling
```

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("paper.pdf")

# 获取 Markdown 格式输出
markdown = result.document.export_to_markdown()

# 获取结构化 JSON
json_output = result.document.export_to_dict()
```

**优势**:
- 2025 基准测试中复杂表格提取准确率最高 (97.9%)
- 保留文档结构
- IBM 开源项目，活跃维护

### 5.4 Marker（PDF → Markdown）

```bash
pip install marker-pdf
```

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

models = create_model_dict()
converter = PdfConverter(artifact_dict=models)
rendered = converter("paper.pdf")
markdown_text = rendered.markdown
```

**优势**: 保留标题、图表、公式格式，输出 LLM 友好的 Markdown

### 5.5 pymupdf4llm（轻量方案）

```bash
pip install pymupdf4llm
```

```python
import pymupdf4llm

# PDF 转 Markdown
md_text = pymupdf4llm.to_markdown("paper.pdf")

# 分块输出（适合 RAG）
chunks = pymupdf4llm.to_markdown("paper.pdf", page_chunks=True)
```

**优势**: 速度最快，LlamaIndex 原生集成，适合 RAG 流水线

### 5.6 处理图表、表格、公式

| 元素 | 推荐工具 | 说明 |
|------|----------|------|
| 表格 | Docling, GROBID | Docling 准确率最高 |
| 图表 | SciPDF, Marker | 提取图片并关联标注 |
| 公式 | Marker, Nougat | Marker 保留 LaTeX 格式 |
| 参考文献 | GROBID | 结构化解析最佳 |
| 全文结构 | GROBID + Docling | 段落、章节层级 |

---

## 6. 电信/通信领域特定资源

### 6.1 核心会议

| 会议 | 全称 | 级别 | 频率 |
|------|------|------|------|
| **IEEE ICC** | International Conference on Communications | 旗舰 | 年度 |
| **IEEE GLOBECOM** | Global Communications Conference | 旗舰 | 年度 |
| **IEEE VTC** | Vehicular Technology Conference | A 类 | 每年两次 |
| **IEEE WCNC** | Wireless Communications and Networking Conference | A 类 | 年度 |
| **IEEE PIMRC** | Personal, Indoor and Mobile Radio Communications | B 类 | 年度 |
| **IEEE CTW** | Communication Theory Workshop | 专题 | 年度 |
| **ACM MobiCom** | Mobile Computing and Networking | 顶级 | 年度 |
| **ACM SIGCOMM** | Data Communication | 顶级 | 年度 |

### 6.2 核心期刊

| 期刊 | 影响因子级别 | 说明 |
|------|-------------|------|
| **IEEE Trans. on Communications** | 高 | 创刊于 1972 |
| **IEEE JSAC** | 最高 | Journal on Selected Areas in Communications |
| **IEEE Communications Letters** | 中高 | 短篇论文 |
| **IEEE Comm. Surveys & Tutorials** | 最高 | 综述论文，免费在线 |
| **IEEE Trans. on Wireless Communications** | 高 | 无线通信 |
| **IEEE Trans. on Signal Processing** | 高 | 信号处理 |
| **IEEE Trans. on Vehicular Technology** | 高 | 车联网 |
| **IEEE Open Journal of ComSoc** | 中 | 开放获取 |
| **IEEE Network Magazine** | 高 | 网络技术 |
| **IEEE Wireless Communications Magazine** | 最高 | 无线通信综述 |

### 6.3 重要数据库

| 数据库 | 说明 |
|--------|------|
| IEEE Xplore | IEEE/IET 论文主要数据库 |
| ComSoc Digital Library | IEEE ComSoc 专用（基于 Xplore） |
| ACM Digital Library | ACM 会议和期刊 |
| arXiv (cs.IT, eess.SP) | 信息论和信号处理预印本 |
| Google Scholar | 最广泛的学术搜索 |

### 6.4 arXiv 相关分类

| 分类代码 | 名称 | 说明 |
|----------|------|------|
| `cs.IT` / `math.IT` | Information Theory | 信息论 |
| `eess.SP` | Signal Processing | 信号处理 |
| `cs.NI` | Networking and Internet Architecture | 网络架构 |
| `cs.ET` | Emerging Technologies | 新兴技术 |
| `eess.SY` | Systems and Control | 系统与控制 |

### 6.5 领域特定搜索策略

**关键术语**:
```
5G NR, 6G, massive MIMO, beamforming, OFDM, channel estimation,
mmWave, sub-6GHz, terahertz, RIS (reconfigurable intelligent surface),
NOMA, full-duplex, network slicing, edge computing, MEC,
cell-free massive MIMO, ISAC (integrated sensing and communications),
semantic communications, over-the-air computation, federated learning,
digital twin, O-RAN, Open RAN, spectrum sharing, cognitive radio,
UAV communications, satellite communications, NTN (non-terrestrial network),
V2X, IoT, URLLC, eMBB, mMTC
```

**搜索查询构建示例**:
```python
# arXiv 搜索通信论文
search = arxiv.Search(
    query='cat:cs.IT AND (ti:"massive MIMO" OR ti:"beamforming")',
    max_results=100,
    sort_by=arxiv.SortCriterion.SubmittedDate
)

# Semantic Scholar 搜索
results = sch.search_paper(
    "reconfigurable intelligent surface channel estimation",
    year="2023-2025",
    fields_of_study=["Computer Science", "Engineering"],
    limit=50
)

# OpenAlex 过滤搜索
works = Works().filter(
    publication_year="2023-2025",
    primary_location={"source": {"id": "S4210168953"}}  # IEEE Trans. Comm.
).search("MIMO beamforming").get()
```

---

## 7. 推荐技术栈与实现路径

### 7.1 推荐架构

```
┌─────────────────────────────────────────────────┐
│                  用户查询                        │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│              查询理解与规划 (LLM)                 │
│  - 关键词提取                                    │
│  - 搜索策略制定                                  │
│  - 数据源选择                                    │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│           多源论文检索 (并行)                     │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌───────┐ │
│  │ arXiv   │ │ Semantic │ │OpenAlex│ │ CORE  │ │
│  │ API     │ │ Scholar  │ │  API   │ │  API  │ │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └───┬───┘ │
└───────┼───────────┼────────────┼──────────┼─────┘
        └───────────┼────────────┼──────────┘
                    ▼            ▼
┌─────────────────────────────────────────────────┐
│         去重 & 排序 & OA 版本查找                 │
│  - DOI 去重                                      │
│  - Unpaywall 查找 OA 链接                        │
│  - 相关性排序                                    │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│            PDF 下载 & 解析                       │
│  ┌─────────────┐  ┌────────────┐               │
│  │ PDF 下载    │→ │ Docling /  │               │
│  │ (限速控制)  │  │ GROBID     │               │
│  └─────────────┘  └─────┬──────┘               │
└──────────────────────────┼──────────────────────┘
                           ▼
┌─────────────────────────────────────────────────┐
│          文本分块 & 向量化                        │
│  - 按章节/段落分块                               │
│  - 嵌入模型向量化                                │
│  - 存入向量数据库                                │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│         RAG 问答 & 报告生成 (LLM)                │
│  - 检索相关文本块                                │
│  - 生成带引用的答案                              │
│  - 综合分析报告                                  │
└─────────────────────────────────────────────────┘
```

### 7.2 推荐 Python 依赖

```txt
# 论文检索
arxiv>=2.1.0
semanticscholar>=0.8.0
habanero>=2.2.0
unpywall>=0.2.0
pyalex>=0.14.0
requests>=2.31.0
aiohttp>=3.9.0

# PDF 解析
docling>=2.0.0
pymupdf4llm>=0.0.10
grobid_client_python>=0.0.7

# LLM 与 RAG
langchain>=0.2.0
langgraph>=0.2.0
openai>=1.0.0
chromadb>=0.5.0
sentence-transformers>=3.0.0

# 工具
feedparser>=6.0.0
pandas>=2.0.0
tqdm>=4.66.0
```

### 7.3 实现步骤建议

1. **论文检索模块**: 封装 arXiv + Semantic Scholar + CORE API 为统一接口
2. **PDF 获取模块**: 整合 Unpaywall 查找 OA 版本 + 限速下载
3. **PDF 解析模块**: Docling（主）+ pymupdf4llm（备选/轻量场景）
4. **向量化存储**: 文本分块 → 嵌入 → ChromaDB/Qdrant
5. **RAG 问答**: LangChain/LangGraph 工作流，带引用的答案生成
6. **报告生成**: 按 gpt-researcher 现有模式输出结构化报告

### 7.4 关键注意事项

- **速率限制**: 所有 API 都有速率限制，必须实现重试和退避逻辑
- **版权合规**: 只下载和分析开放获取的论文全文
- **去重**: 同一论文可能出现在多个数据源，通过 DOI 去重
- **缓存**: 已下载的 PDF 和解析结果应缓存，避免重复请求
- **元数据标准化**: 不同 API 返回格式不同，需统一数据模型
