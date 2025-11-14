# RAG系统实现结构总结

## 📊 实现概览

本项目实现了一个完整的RAG（检索增强生成）系统，用于问卷生成的检索增强。系统基于 **LangChain + ChromaDB + DashScope Embeddings** 构建。

---

## 🏗️ 架构图

```
用户输入
    ↓
需求扩写 (enhance_requirement)
    ↓
向量检索 (similarity_search)
    ↓
检索到k个相关文档
    ↓
格式化上下文 (format_context)
    ↓
合并上下文 + 用户输入
    ↓
LLM生成 (ChatDashScope)
    ↓
JSON解析 (CustomJsonParser)
    ↓
生成的问卷
```

---

## 📁 文件结构及功能

### 核心模块

#### 1. `app/core/vector_store.py` (278行)
**功能：** 向量数据库核心模块

**类：** `SurveyVectorStore`

**主要功能：**
- ✅ PDF文档加载 (`load_document_from_pdf`)
- ✅ 文档文本切分 (`split_documents`)
- ✅ 向量存储创建/加载 (`create_vector_store`)
- ✅ 语义相似度检索 (`similarity_search`, `similarity_search_with_score`)
- ✅ 文档增量添加 (`add_documents`)
- ✅ 向量库持久化 (`persist`)
- ✅ 统计信息获取 (`get_stats`)

**关键配置：**
```python
chunk_size = 1000        # 文本块大小
chunk_overlap = 200      # 块重叠
embedding_model = "text-embedding-v3"
persist_directory = "./data/chroma_db"
collection_name = "exemplary_surveys"
```

**依赖：**
- `Chroma` (向量数据库)
- `DashScopeEmbeddings` (嵌入模型)
- `PyPDFLoader` (PDF加载)
- `RecursiveCharacterTextSplitter` (文本切分)

---

#### 2. `app/chains/survey_creation_chain.py` (668行)
**功能：** RAG检索链实现

**类：** `SurveyCreationChain`

**主要功能：**
- ✅ RAG链构建 (`_create_chain`)
- ✅ 向量检索上下文 (`retrieve_context`)
- ✅ 上下文格式化 (`format_context`)
- ✅ LLM Prompt构建 (`_create_prompt_template`)
- ✅ JSON解析（带错误修复）(`_create_custom_parser`)
- ✅ 问卷生成 (`generate_survey`)
- ✅ 带参考文档的生成 (`generate_with_rag`)

**工作流程：**
1. 接收用户输入
2. 从向量库检索相关文档（`retrieval_k` 个）
3. 格式化检索结果为上下文
4. 合并上下文和用户输入为Prompt
5. 调用LLM生成
6. 解析JSON结果（自动修复常见错误）

**关键特性：**
- 自定义JSON解析器，处理LLM输出中的格式问题
- 错误修复：前导零、特殊字符、未闭合字符串等
- 备用方案：链执行失败时使用备用LLM调用

**依赖：**
- `ChatDashScope` (LLM)
- `ChatPromptTemplate` (提示词模板)
- `RunnablePassthrough` (链构建)
- `JsonOutputParser` (输出解析)

---

#### 3. `app/services/survey_service.py` (311行)
**功能：** 服务层，封装RAG系统

**类：** `SurveyService`

**主要功能：**
- ✅ 向量存储初始化
- ✅ RAG链初始化
- ✅ 需求扩写优化 (`enhance_requirement`)
- ✅ 问卷生成 (`create_survey`)
- ✅ 带参考文档的生成 (`create_survey_with_refs`)
- ✅ 问卷验证和清理

**初始化流程：**
```python
1. 初始化向量存储 (SurveyVectorStore)
2. 尝试加载已有向量库
3. 初始化RAG链 (SurveyCreationChain)
4. 初始化需求扩写LLM
```

---

### 工具脚本

#### 4. `update_rag_materials.py` (240行)
**功能：** 语料库构建和更新脚本

**主要功能：**
- ✅ 扫描 `rag_materials/` 文件夹中的PDF文件（支持嵌套）
- ✅ MD5哈希计算和文件变更检测
- ✅ 增量更新（只处理新增/修改的文件）
- ✅ 索引文件维护 (`.rag_index.json`)
- ✅ 错误处理和失败文件记录
- ✅ 统计信息输出

**工作流程：**
```
扫描PDF文件
    ↓
计算文件哈希
    ↓
对比索引文件
    ↓
识别新增/修改的文件
    ↓
加载PDF并切分
    ↓
添加到向量数据库
    ↓
更新索引文件
```

**关键函数：**
- `get_file_hash()`: MD5哈希计算
- `load_index()`: 加载索引文件
- `save_index()`: 保存索引文件
- `scan_pdf_files()`: 递归扫描PDF
- `main()`: 主流程

---

### Web API集成

#### 5. `run_all.py` (相关部分)
**功能：** Web API端点，管理RAG语料

**API端点：**
- `POST /api/upload-rag-material`: 上传PDF语料文件
- `GET /api/rag-materials/list`: 获取语料列表
- `GET /api/rag-materials/status`: 获取向量数据库状态

**上传流程：**
```
接收PDF文件
    ↓
保存到 rag_materials/
    ↓
自动加载和切分
    ↓
添加到向量数据库
    ↓
更新索引文件
    ↓
返回处理结果
```

---

## 🔄 数据流

### 向量数据库构建流程

```
PDF文件
    ↓
PyPDFLoader加载
    ↓
RecursiveCharacterTextSplitter切分
    ↓
DashScopeEmbeddings向量化
    ↓
Chroma存储
    ↓
持久化到 ./data/chroma_db/
```

### RAG生成流程

```
用户输入 "用户满意度调查"
    ↓
向量检索 (similarity_search)
    ↓
检索到3个相关文档块
    ↓
格式化上下文:
    "案例1: ...\n案例2: ...\n案例3: ..."
    ↓
构建Prompt:
    System: 你是问卷设计专家...
    User: 用户需求：用户满意度调查
          参考案例：[检索到的上下文]
          任务要求：...
    ↓
调用LLM (ChatDashScope)
    ↓
JSON输出解析 (CustomJsonParser)
    ↓
返回问卷JSON
```

---

## 📊 语料库结构

### 目录结构

```
rag_materials/
├── 关键场景问卷示例语料库.pdf
├── 小众及垂直领域问卷示例语料库.pdf
├── 真实感问卷示例语料库（增强版）.pdf
├── 真实问卷示例语料库.pdf
├── 面向AI问卷生成的RAG语料库.pdf
└── .rag_index.json          # 索引文件（自动生成）
```

### 索引文件格式

```json
{
  "filename1.pdf": {
    "hash": "md5_hash_value",
    "size": 1234567,
    "modified": 1698765432.0,
    "processed_at": "2025-01-XX T XX:XX:XX"
  },
  "filename2.pdf": {
    ...
  },
  "_last_updated": "2025-01-XX T XX:XX:XX"
}
```

---

## 🔧 配置参数总结

### 向量存储参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `embedding_model` | `"text-embedding-v3"` | DashScope嵌入模型 |
| `chunk_size` | `1000` | 每个文本块最大字符数 |
| `chunk_overlap` | `200` | 文本块之间的重叠字符数 |
| `persist_directory` | `"./data/chroma_db"` | 向量数据库持久化目录 |
| `collection_name` | `"exemplary_surveys"` | ChromaDB集合名称 |

### 文本切分策略

**分隔符优先级：**
```python
separators = ["\n\n", "\n", "。", "；", " ", ""]
```

**切分逻辑：**
1. 优先按双换行符 `\n\n` 切分
2. 其次按单换行符 `\n` 切分
3. 按中文句号 `。` 切分
4. 按中文分号 `；` 切分
5. 按空格切分
6. 最后按字符切分

### RAG检索参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `retrieval_k` | `3` | 默认检索文档数量 |
| `llm_model` | `"qwen-max"` | LLM模型（需求扩写） |
| `generation_model` | `"qwen-plus"` | LLM模型（问卷生成） |
| `temperature` | `0.7` | LLM温度参数 |
| `enhancement_temperature` | `0.5` | 需求扩写温度（更稳定） |

---

## 🎯 关键设计决策

### 1. 文本切分策略
- **为什么选择 `chunk_size=1000`？**
  - 平衡上下文完整性和检索精度
  - 适合中文问卷文档的平均段落长度
  - 避免切分过小丢失语义，过大降低检索精度

### 2. 检索数量
- **为什么选择 `retrieval_k=3`？**
  - 平衡上下文长度和生成质量
  - 避免上下文过长导致LLM混乱
  - 3个案例足够提供设计参考

### 3. 增量更新机制
- **为什么使用MD5哈希？**
  - 快速检测文件变更
  - 避免重复处理未修改的文件
  - 支持高效的大规模语料管理

### 4. JSON解析错误修复
- **为什么需要自定义解析器？**
  - LLM输出可能存在格式问题
  - 自动修复常见错误（前导零、特殊字符等）
  - 提高生成成功率

---

## 📈 性能指标

### 向量数据库
- **文档数量：** 25个文档块（测试环境）
- **检索速度：** <100ms（本地ChromaDB）
- **存储大小：** ~几MB（取决于文档数量）

### RAG生成
- **检索时间：** <200ms
- **LLM生成时间：** 5-15秒（取决于模型）
- **总耗时：** 约6-16秒

---

## 🔐 安全考虑

1. **API密钥管理**
   - 使用 `.env` 文件存储
   - 不提交到版本控制
   - 环境变量加载

2. **文件路径安全**
   - 文件名清理（移除特殊字符）
   - 防止路径遍历攻击
   - 文件大小限制

3. **错误处理**
   - 向量库未初始化时的降级
   - 检索失败时的备用方案
   - 异常捕获和日志记录

---

## 🐛 已知问题和限制

### 当前限制
1. **仅支持PDF格式**
   - 不支持Word、TXT等格式（可扩展）

2. **嵌入模型固定**
   - 目前只支持DashScope（可适配其他模型）

3. **中文为主**
   - 切分策略针对中文优化（可调整）

### 已知问题
1. **JSON解析**
   - 某些复杂JSON可能需要手动修复（已实现自动修复）

2. **大文件处理**
   - 超大PDF文件可能需要较长时间处理

---

## 🚀 扩展建议

### 支持的文档格式
- 扩展 `vector_store.py` 支持Word、TXT、Markdown等

### 多语言支持
- 调整切分器支持多语言分隔符
- 使用多语言嵌入模型

### 高级检索
- 实现混合检索（向量+关键词）
- 添加元数据过滤
- 支持重排序（reranking）

### 缓存机制
- 缓存检索结果
- 缓存生成的问卷

---

## 📚 参考文档

- **详细迁移指南：** `RAG_SYSTEM_MIGRATION_GUIDE.md`
- **Cursor指令：** `CURSOR_MIGRATION_INSTRUCTION.md`
- **测试报告：** `docs/RAG_TEST_REPORT.md`
- **语料库说明：** `rag_materials/README.md`

---

**最后更新：** 2025-01-XX  
**版本：** 1.0




