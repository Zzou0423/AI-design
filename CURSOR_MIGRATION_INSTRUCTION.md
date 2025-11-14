# RAG系统迁移 - Cursor指令

## 🎯 指令内容

请帮我将本项目中的RAG系统迁移到新的项目中。以下是需要迁移的组件和具体要求：

---

## 📦 需要迁移的核心文件

### 1. 向量存储模块
**源文件：** `app/core/vector_store.py`
- **类名：** `SurveyVectorStore`
- **功能：** PDF文档加载、文本切分、向量化存储、语义检索
- **依赖：** `langchain`, `chromadb`, `DashScopeEmbeddings`
- **关键参数：**
  - `persist_directory`: 向量数据库存储路径（默认：`./data/chroma_db`）
  - `collection_name`: 集合名称（默认：`"exemplary_surveys"`）
  - `embedding_model`: 嵌入模型（默认：`"text-embedding-v3"`）
  - `chunk_size`: 文本块大小（默认：1000字符）
  - `chunk_overlap`: 块重叠（默认：200字符）

### 2. RAG检索链
**源文件：** `app/chains/survey_creation_chain.py`
- **类名：** `SurveyCreationChain`
- **功能：** 整合向量检索和LLM生成，实现检索增强生成
- **关键方法：**
  - `generate_survey()`: 生成内容（使用RAG）
  - `generate_with_rag()`: 生成内容并返回检索文档
  - `_retrieve_context()`: 从向量库检索上下文
- **默认检索数量：** `retrieval_k=3`

### 3. 语料库构建脚本
**源文件：** `update_rag_materials.py`
- **功能：** 扫描PDF文件、增量更新向量库
- **特性：** MD5哈希判断文件变更、支持嵌套文件夹
- **输出：** `.rag_index.json` 索引文件

---

## 📁 目标目录结构

```
新项目根目录/
├── app/ (或现有模块目录)
│   ├── core/
│   │   └── vector_store.py           # 向量存储模块
│   └── chains/ (或services/)
│       └── rag_chain.py              # RAG检索链（可重命名）
├── rag_materials/                    # 语料库文件夹
│   └── .rag_index.json              # 索引文件（自动生成）
├── data/
│   └── chroma_db/                    # 向量数据库（自动生成）
└── update_rag_materials.py           # 语料库构建脚本
```

---

## 🔧 适配要求

### 1. LLM调用适配
- **当前实现：** 使用 `langchain_dashscope.ChatDashScope`
- **需要适配：** 根据新项目使用的LLM框架修改 `survey_creation_chain.py` 中的LLM初始化
- **保持：** RAG检索流程不变，只修改LLM调用部分

### 2. 嵌入模型适配（可选）
- **当前实现：** DashScope `text-embedding-v3`
- **如需更换：** 修改 `vector_store.py` 中的 `embedding_model` 参数
- **支持其他模型：** OpenAI、HuggingFace等（需相应修改导入）

### 3. 路径配置
- 将所有硬编码路径改为可配置参数
- 使用 `pathlib.Path` 处理路径
- 确保与新项目的目录结构兼容

### 4. 环境变量
- **必需：** `DASHSCOPE_API_KEY` (如果使用DashScope)
- **可选：** 添加其他LLM/嵌入模型的API密钥配置

---

## 📋 依赖项

```txt
# 核心依赖
chromadb>=0.4.0
langchain>=0.1.0
langchain-core>=0.1.0
langchain-community>=0.0.10
langchain-dashscope>=0.0.1  # 如使用DashScope
pypdf>=3.0.0
python-dotenv>=1.0.0

# LLM SDK (根据实际需求选择)
dashscope>=1.17.0  # DashScope
# 或
langchain-openai>=0.0.1  # OpenAI
# 或
langchain-ollama>=0.0.1  # Ollama (本地)
```

---

## 🚀 迁移步骤

1. **复制核心文件**
   - `app/core/vector_store.py` → 新项目的 `app/core/vector_store.py`
   - `app/chains/survey_creation_chain.py` → 新项目的相应目录
   - `update_rag_materials.py` → 新项目根目录

2. **创建目录结构**
   - `rag_materials/` 文件夹（存放PDF语料）
   - `data/chroma_db/` 文件夹（向量数据库持久化）

3. **安装依赖**
   ```bash
   pip install chromadb langchain langchain-community langchain-dashscope dashscope pypdf python-dotenv
   ```

4. **配置环境变量**
   ```bash
   # .env文件
   DASHSCOPE_API_KEY=your_api_key_here
   ```

5. **适配LLM调用**
   - 根据新项目使用的LLM框架，修改 `survey_creation_chain.py` 中的LLM初始化
   - 保持RAG检索流程不变

6. **测试验证**
   - 运行 `python update_rag_materials.py` 构建向量数据库
   - 测试向量检索功能
   - 测试RAG生成流程

---

## 💻 使用示例

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
    llm_model="qwen-max",  # 适配新项目的LLM模型
    retrieval_k=3
)

# 3. 生成内容
result = chain.generate_survey("用户满意度调查")
```

### 添加语料

```python
# 方法1: 使用脚本
python update_rag_materials.py

# 方法2: 程序化添加
documents = vector_store.load_and_split_pdf("new_corpus.pdf")
vector_store.add_documents(documents)
vector_store.persist()
```

---

## ✅ 检查清单

迁移完成后请验证：

- [ ] 向量存储模块正常工作
- [ ] 可以加载PDF并切分为文本块
- [ ] 向量数据库可以创建和持久化
- [ ] 语义检索功能正常
- [ ] RAG链可以检索上下文
- [ ] LLM调用适配成功
- [ ] 语料库构建脚本可以扫描和处理PDF
- [ ] 增量更新功能正常（文件哈希判断）
- [ ] 环境变量配置正确
- [ ] 所有依赖已安装

---

## 🎯 关键配置参数

### 向量存储配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `persist_directory` | `./data/chroma_db` | 向量数据库目录 |
| `collection_name` | `"exemplary_surveys"` | ChromaDB集合名 |
| `embedding_model` | `"text-embedding-v3"` | 嵌入模型 |
| `chunk_size` | `1000` | 文本块大小 |
| `chunk_overlap` | `200` | 块重叠大小 |

### RAG检索配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `retrieval_k` | `3` | 检索文档数量 |
| `llm_model` | `"qwen-max"` | LLM模型（需适配） |
| `temperature` | `0.7` | LLM温度参数 |

---

## 📝 注意事项

1. **API密钥安全**：不要提交到版本控制
2. **路径权限**：确保向量数据库目录有写入权限
3. **文档切分**：中文文档建议较小的chunk_size
4. **错误处理**：向量库未初始化时的降级处理
5. **检索数量**：retrieval_k建议3-5个文档

---

## 🔍 测试验证

迁移后请运行以下测试：

```python
# 测试1: 向量存储
from app.core.vector_store import SurveyVectorStore
vector_store = SurveyVectorStore()
vector_store.create_vector_store()
stats = vector_store.get_stats()
print(stats)

# 测试2: 语义检索
results = vector_store.similarity_search("测试查询", k=3)
print(f"检索到 {len(results)} 个结果")

# 测试3: RAG生成
from app.chains.survey_creation_chain import SurveyCreationChain
chain = SurveyCreationChain(retrieval_k=3)
result = chain.generate_survey("测试主题")
print(result)
```

---

**迁移完成标志：**
- ✅ 可以成功构建向量数据库
- ✅ 语义检索返回相关文档
- ✅ RAG生成使用检索到的上下文
- ✅ 可以增量更新语料库

---

**如需详细文档，请参考：** `RAG_SYSTEM_MIGRATION_GUIDE.md`




