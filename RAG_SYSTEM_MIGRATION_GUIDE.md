# RAG系统迁移指南

## 📋 项目中的RAG系统实现结构分析

### 核心架构

本项目实现了一个基于**LangChain + ChromaDB + DashScope Embeddings**的RAG系统，用于问卷生成的检索增强生成。

### 目录结构

```
项目根目录/
├── app/
│   ├── core/
│   │   └── vector_store.py          # 向量数据库核心模块
│   ├── chains/
│   │   └── survey_creation_chain.py # RAG检索链实现
│   └── services/
│       └── survey_service.py        # 服务层（使用RAG）
├── update_rag_materials.py          # 语料库构建脚本
├── rag_materials/                   # 语料库文件夹
│   ├── *.pdf                        # PDF语料文件
│   └── .rag_index.json              # 语料索引文件
└── data/
    └── chroma_db/                   # ChromaDB向量数据库持久化目录
```

---

## 🔧 核心组件详解

### 1. 向量存储模块 (`app/core/vector_store.py`)

**功能：**
- PDF文档加载和文本切分
- 向量化和持久化存储
- 语义相似度检索

**关键类：** `SurveyVectorStore`

**核心方法：**
- `load_and_split_pdf()`: 加载PDF并切分为文本块
- `create_vector_store()`: 创建或加载向量数据库
- `similarity_search()`: 语义相似度检索
- `add_documents()`: 添加文档到已有向量库
- `get_stats()`: 获取向量库统计信息

**配置参数：**
- `persist_directory`: 向量数据库持久化目录 (默认: `./data/chroma_db`)
- `collection_name`: 集合名称 (默认: `"exemplary_surveys"`)
- `embedding_model`: 嵌入模型 (默认: `"text-embedding-v3"`)
- `chunk_size`: 文本块大小 (默认: 1000字符)
- `chunk_overlap`: 文本块重叠 (默认: 200字符)

---

### 2. RAG检索链 (`app/chains/survey_creation_chain.py`)

**功能：**
- 整合向量检索和LLM生成
- 实现检索增强生成流程

**关键类：** `SurveyCreationChain`

**核心方法：**
- `generate_survey()`: 生成问卷（使用RAG）
- `generate_with_rag()`: 生成问卷并返回检索文档
- `_retrieve_context()`: 从向量库检索相关上下文

**工作流程：**
1. 接收用户输入
2. 从向量库检索相似文档 (`retrieval_k` 个)
3. 格式化检索结果为上下文
4. 将上下文和用户输入合并为Prompt
5. 调用LLM生成结果
6. 解析并返回JSON格式结果

---

### 3. 语料库构建脚本 (`update_rag_materials.py`)

**功能：**
- 扫描语料文件夹中的PDF文件
- 增量更新向量数据库（只处理新增/修改的文件）
- 维护文件索引和哈希值

**特性：**
- ✅ 支持嵌套文件夹
- ✅ MD5哈希判断文件变更
- ✅ 自动创建索引文件 `.rag_index.json`
- ✅ 错误处理和失败文件记录

---

### 4. 服务层集成 (`app/services/survey_service.py`)

**功能：**
- 封装RAG系统为服务接口
- 处理需求扩写和问卷生成
- 管理向量存储生命周期

**关键方法：**
- `enhance_requirement()`: 需求扩写优化
- `create_survey()`: 创建问卷（内部使用RAG链）
- `create_survey_with_refs()`: 创建问卷并返回参考文档

---

### 5. Web API集成 (`run_all.py`)

**API端点：**
- `POST /api/upload-rag-material`: 上传PDF语料文件
- `GET /api/rag-materials/list`: 获取已上传的语料列表
- `GET /api/rag-materials/status`: 获取向量数据库状态

**功能：**
- 文件上传和存储
- 自动更新向量数据库
- 索引文件维护

---

## 📦 依赖项

### 核心依赖

```python
# 向量数据库
chromadb>=0.4.0

# LangChain框架
langchain>=0.1.0
langchain-core>=0.1.0
langchain-community>=0.0.10
langchain-dashscope>=0.0.1

# 嵌入模型
dashscope>=1.17.0  # 阿里云DashScope（含text-embedding-v3）

# PDF处理
pypdf>=3.0.0

# 环境变量
python-dotenv>=1.0.0
```

### 文本切分器

使用 `RecursiveCharacterTextSplitter`，切分策略：
- 分隔符优先级: `["\n\n", "\n", "。", "；", " ", ""]`
- 块大小: 1000字符
- 块重叠: 200字符

---

## 🚀 迁移到其他项目的Cursor指令

### 指令模板

```markdown
请帮我将RAG系统迁移到当前项目。具体要求如下：

## 需要迁移的组件

1. **向量存储模块** (`app/core/vector_store.py`)
   - 类名：`SurveyVectorStore`
   - 功能：PDF加载、文本切分、向量存储、相似度检索
   - 依赖：LangChain + ChromaDB + DashScope Embeddings

2. **RAG检索链** (`app/chains/survey_creation_chain.py`)
   - 类名：`SurveyCreationChain`
   - 功能：整合向量检索和LLM生成
   - 需要适配当前项目的LLM调用方式

3. **语料库构建脚本** (`update_rag_materials.py`)
   - 功能：扫描PDF文件、增量更新向量库
   - 支持MD5哈希判断文件变更

## 目录结构要求

请创建以下目录结构：
```
项目根目录/
├── app/ (或当前项目的模块目录)
│   ├── core/
│   │   └── vector_store.py
│   └── chains/ (或services/)
│       └── [自定义名称]_chain.py
├── rag_materials/        # 语料库文件夹
│   └── .rag_index.json  # 索引文件（自动生成）
├── data/
│   └── chroma_db/       # 向量数据库（自动生成）
└── update_rag_materials.py
```

## 适配要求

1. **嵌入模型适配**
   - 当前使用：DashScope `text-embedding-v3`
   - 如果需要更换：修改 `vector_store.py` 中的 `embedding_model` 参数
   - 支持其他嵌入模型：OpenAI、HuggingFace等

2. **LLM适配**
   - 当前使用：LangChain DashScope (`ChatDashScope`)
   - 需要根据项目使用的LLM框架适配 `survey_creation_chain.py`
   - 保持RAG检索流程不变，只需修改LLM调用部分

3. **文件路径适配**
   - 将所有硬编码路径改为可配置参数
   - 使用 `pathlib.Path` 处理路径

4. **环境变量**
   - `DASHSCOPE_API_KEY`: DashScope API密钥
   - 如需使用其他服务，添加对应的API密钥配置

## 功能要求

1. **向量存储**
   - ✅ PDF文档加载和切分
   - ✅ 向量化和持久化
   - ✅ 语义相似度检索
   - ✅ 支持增量添加文档

2. **语料库管理**
   - ✅ 自动扫描PDF文件
   - ✅ 增量更新（基于文件哈希）
   - ✅ 索引文件维护
   - ✅ 错误处理和日志

3. **RAG检索链**
   - ✅ 查询向量库检索相关文档
   - ✅ 格式化检索结果为上下文
   - ✅ 合并上下文和用户输入
   - ✅ 调用LLM生成结果

## 测试要求

迁移完成后，请提供：
1. 测试脚本，验证向量数据库构建
2. 测试脚本，验证语义检索功能
3. 测试脚本，验证RAG生成流程

## 文档要求

请生成：
1. README说明如何使用RAG系统
2. 配置文件示例（.env）
3. API使用示例
```

---

## 📝 详细实现步骤

### Step 1: 创建向量存储模块

**文件：** `app/core/vector_store.py`

**关键代码结构：**
```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class SurveyVectorStore:
    def __init__(self, persist_directory, collection_name, embedding_model):
        # 初始化嵌入模型
        self.embeddings = DashScopeEmbeddings(model=embedding_model)
        # 初始化文本切分器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "；", " ", ""]
        )
    
    def load_and_split_pdf(self, pdf_path):
        # 加载PDF
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        # 切分文档
        split_docs = self.text_splitter.split_documents(documents)
        return split_docs
    
    def create_vector_store(self, documents=None):
        # 创建或加载向量存储
        if documents:
            self.vector_store = Chroma.from_documents(...)
        else:
            self.vector_store = Chroma(...)
    
    def similarity_search(self, query, k=4):
        # 语义相似度检索
        return self.vector_store.similarity_search(query, k=k)
```

---

### Step 2: 创建RAG检索链

**文件：** `app/chains/survey_creation_chain.py` (或自定义名称)

**关键代码结构：**
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

class SurveyCreationChain:
    def __init__(self, vector_store, llm_model, retrieval_k=3):
        self.vector_store = vector_store
        self.llm = ChatDashScope(model=llm_model)
        self.retrieval_k = retrieval_k
    
    def _create_chain(self):
        def retrieve_context(user_input):
            # 检索相关文档
            docs = self.vector_store.similarity_search(user_input, k=self.retrieval_k)
            # 格式化上下文
            return format_context(docs)
        
        # 创建RAG链
        chain = (
            RunnablePassthrough.assign(
                retrieved_context=lambda x: retrieve_context(x["user_input"])
            )
            | self.prompt_template
            | self.llm
            | self.output_parser
        )
        return chain
```

---

### Step 3: 创建语料库构建脚本

**文件：** `update_rag_materials.py`

**核心流程：**
1. 扫描 `rag_materials/` 文件夹的PDF文件
2. 计算文件MD5哈希
3. 对比索引文件，找出新增/修改的文件
4. 加载PDF并切分
5. 添加到向量数据库
6. 更新索引文件

**关键函数：**
```python
def get_file_hash(file_path):
    # 计算MD5哈希
    
def scan_pdf_files(materials_dir):
    # 递归扫描PDF文件
    
def main():
    # 主流程：扫描 → 对比 → 处理 → 更新索引
```

---

### Step 4: 集成到服务层

**文件：** `app/services/survey_service.py` (或对应服务文件)

**集成方式：**
```python
class SurveyService:
    def __init__(self):
        # 初始化向量存储
        self.vector_store = SurveyVectorStore(...)
        self.vector_store.create_vector_store()
        
        # 初始化RAG链
        self.chain = SurveyCreationChain(
            vector_store=self.vector_store,
            llm_model="qwen-max",
            retrieval_k=3
        )
    
    def create_survey(self, user_input):
        # 使用RAG链生成
        return self.chain.generate_survey(user_input)
```

---

## 🔄 适配不同LLM框架

### 方案A: 使用OpenAI

**修改点：**
```python
# vector_store.py
from langchain_openai import OpenAIEmbeddings
self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# survey_creation_chain.py
from langchain_openai import ChatOpenAI
self.llm = ChatOpenAI(model="gpt-4", temperature=0.7)
```

### 方案B: 使用本地模型

**修改点：**
```python
# 使用HuggingFace嵌入
from langchain_huggingface import HuggingFaceEmbeddings
self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# 使用Ollama等本地LLM
from langchain_ollama import OllamaLLM
self.llm = OllamaLLM(model="llama2")
```

---

## 📊 配置参数总结

### 向量存储配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `persist_directory` | `./data/chroma_db` | 向量数据库存储目录 |
| `collection_name` | `"exemplary_surveys"` | ChromaDB集合名称 |
| `embedding_model` | `"text-embedding-v3"` | 嵌入模型名称 |
| `chunk_size` | `1000` | 文本块大小（字符） |
| `chunk_overlap` | `200` | 文本块重叠（字符） |

### RAG检索配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `retrieval_k` | `3` | 检索返回的文档数量 |
| `llm_model` | `"qwen-max"` | LLM模型名称 |
| `temperature` | `0.7` | LLM温度参数 |

---

## ✅ 迁移检查清单

- [ ] 复制 `vector_store.py` 到目标项目
- [ ] 复制 `survey_creation_chain.py` 并适配LLM调用
- [ ] 复制 `update_rag_materials.py` 并适配路径
- [ ] 安装依赖：`chromadb`, `langchain`, `pypdf` 等
- [ ] 配置环境变量（API密钥）
- [ ] 创建 `rag_materials/` 文件夹
- [ ] 创建 `data/chroma_db/` 目录（或配置持久化路径）
- [ ] 适配项目中的LLM调用方式
- [ ] 测试向量数据库构建
- [ ] 测试语义检索功能
- [ ] 测试RAG生成流程
- [ ] 编写使用文档

---

## 🎯 快速迁移命令模板

```bash
# 1. 安装依赖
pip install chromadb langchain langchain-community langchain-dashscope dashscope pypdf python-dotenv

# 2. 创建目录结构
mkdir -p app/core app/chains rag_materials data/chroma_db

# 3. 复制文件
# (通过Cursor或其他方式复制文件)

# 4. 配置环境变量
echo "DASHSCOPE_API_KEY=your_key_here" > .env

# 5. 构建向量数据库
python update_rag_materials.py

# 6. 测试RAG功能
python -m app.services.survey_service
```

---

## 📚 参考文件清单

迁移时需要参考的源文件：

1. **核心模块**
   - `app/core/vector_store.py` (278行)
   - `app/chains/survey_creation_chain.py` (668行)
   - `app/services/survey_service.py` (311行)

2. **工具脚本**
   - `update_rag_materials.py` (240行)

3. **配置文件**
   - `requirements.txt` (RAG相关依赖)
   - `.env.example` (环境变量示例，如果有)

4. **文档**
   - `rag_materials/README.md` (语料库使用说明)
   - `docs/RAG_TEST_REPORT.md` (测试报告，了解功能)

---

## 💡 使用示例

### 基本使用

```python
from app.core.vector_store import SurveyVectorStore
from app.chains.survey_creation_chain import SurveyCreationChain

# 1. 初始化向量存储
vector_store = SurveyVectorStore(
    persist_directory="./data/chroma_db",
    collection_name="exemplary_surveys"
)
vector_store.create_vector_store()

# 2. 初始化RAG链
chain = SurveyCreationChain(
    vector_store=vector_store,
    llm_model="qwen-max",
    retrieval_k=3
)

# 3. 生成内容
result = chain.generate_survey("用户满意度调查")
print(result)
```

### 添加新语料

```python
# 方法1: 使用脚本
python update_rag_materials.py

# 方法2: 程序化添加
documents = vector_store.load_and_split_pdf("new_corpus.pdf")
vector_store.add_documents(documents)
vector_store.persist()
```

---

## 🔍 调试和测试

### 测试向量存储

```python
from app.core.vector_store import SurveyVectorStore

vector_store = SurveyVectorStore()
vector_store.create_vector_store()

# 测试检索
results = vector_store.similarity_search("用户满意度", k=3)
for i, doc in enumerate(results, 1):
    print(f"结果 {i}: {doc.page_content[:200]}...")

# 查看统计
stats = vector_store.get_stats()
print(stats)
```

### 测试RAG链

```python
from app.chains.survey_creation_chain import SurveyCreationChain

chain = SurveyCreationChain(retrieval_k=3)
survey, refs = chain.generate_with_rag("产品体验调研")

print(f"检索到 {len(refs)} 个参考文档")
print(f"生成问卷包含 {len(survey['questions'])} 个问题")
```

---

## ⚠️ 注意事项

1. **API密钥安全**
   - 不要将API密钥提交到版本控制
   - 使用环境变量或配置文件管理

2. **向量数据库路径**
   - 确保有写入权限
   - 生产环境建议使用持久化存储

3. **文档切分参数**
   - `chunk_size` 和 `chunk_overlap` 需要根据文档类型调整
   - 中文文档建议使用较小的chunk_size

4. **检索数量**
   - `retrieval_k` 影响上下文长度和生成质量
   - 建议值：3-5个文档

5. **错误处理**
   - 向量库未初始化时的降级处理
   - 检索失败时的备用方案

---

## 📞 迁移支持

如果在迁移过程中遇到问题，请检查：

1. **依赖安装**
   ```bash
   pip list | grep -E "chromadb|langchain|dashscope"
   ```

2. **环境变量**
   ```bash
   echo $DASHSCOPE_API_KEY
   ```

3. **向量数据库状态**
   ```python
   vector_store.get_stats()
   ```

4. **日志输出**
   - 查看控制台输出的警告和错误信息
   - 检查 `debug_failed_json.txt`（如果有JSON解析错误）

---

**生成时间：** 2025-01-XX  
**版本：** 1.0  
**适用项目：** ai_survey_assistant_2.0




