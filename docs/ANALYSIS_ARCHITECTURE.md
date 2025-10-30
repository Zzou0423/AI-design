# 问卷分析功能 - 完整架构与技术文档

## 📋 目录

1. [功能概述](#功能概述)
2. [系统架构](#系统架构)
3. [核心组件](#核心组件)
4. [数据流程](#数据流程)
5. [算法技术](#算法技术)
6. [API接口](#api接口)
7. [使用示例](#使用示例)
8. [扩展性设计](#扩展性设计)

---

## 功能概述

### 🎯 核心功能
当前系统实现了**基于大语言模型的开放题定性分析**功能，专注于从用户的自由文本回答中提取结构化的洞察。

### ✨ 主要能力
- **主题识别**：自动识别用户反馈中的核心主题
- **情感分析**：判断每个主题的情感倾向（积极/消极/中性）
- **引述提取**：提取最具代表性的用户原话
- **频次估算**：估算各主题被提及的相对频率
- **行动建议**：基于分析结果生成可操作的建议

### 🎓 分析方法论
采用**质性研究（Qualitative Research）**方法论：
- **主题编码（Thematic Coding）**：识别并归纳数据中的主题
- **内容分析（Content Analysis）**：系统化地分析文本内容
- **情感分析（Sentiment Analysis）**：判断情感倾向

---

## 系统架构

### 📐 三层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      前端展示层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  问卷详情页   │  │  分析页面    │  │  报告展示    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────┴──────────────────────────────────────┐
│                      API接口层                               │
│  POST /api/analyze/{survey_id}                              │
│  ↓                                                           │
│  FastAPI路由 → run_all.py#analyze_survey_results()         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    业务逻辑层                                │
│                                                              │
│  ┌───────────────────────────────────────────────┐         │
│  │       SurveyAnalysisEngine                    │         │
│  │       (分析引擎 - 编排者)                      │         │
│  │                                                │         │
│  │  1. 数据加载  _load_data()                     │         │
│  │  2. 数据提取  _extract_open_ended_responses() │         │
│  │  3. 执行分析  qualitative_analyzer.analyze()  │         │
│  │  4. 生成报告  generate_report()                │         │
│  │  5. 返回结果                                   │         │
│  └─────────────────┬─────────────────────────────┘         │
│                    │                                         │
│  ┌─────────────────┴─────────────────────────────┐         │
│  │       QualitativeAnalyzer                      │         │
│  │       (定性分析器 - 执行者)                     │         │
│  │                                                 │         │
│  │  • 数据预处理  _preprocess_responses()         │         │
│  │  • LLM分析    _perform_qualitative_analysis()  │         │
│  │  • 结果验证   Pydantic模型验证                  │         │
│  │  • 报告生成   generate_report()                │         │
│  └─────────────────┬─────────────────────────────┘         │
│                    │                                         │
│  ┌─────────────────┴─────────────────────────────┐         │
│  │           AnalysisToolkit                      │         │
│  │           (分析工具包 - 备用)                   │         │
│  │                                                 │         │
│  │  • 用户聚类   tool_cluster_users()             │         │
│  │  • 主题提取   tool_extract_themes()            │         │
│  │  • 情感分析   tool_analyze_sentiment()         │         │
│  │  • 关键词提取 tool_extract_keywords()          │         │
│  │  • 统计摘要   tool_statistics_summary()        │         │
│  └─────────────────────────────────────────────────┘         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    数据访问层                                │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ JSON文件读写  │  │ Pydantic模型 │  │ 数据验证     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    外部服务层                                │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │           DashScope LLM API                  │          │
│  │           (阿里云通义千问)                    │          │
│  │                                               │          │
│  │  • 模型：qwen-plus                            │          │
│  │  • Temperature: 0.7                          │          │
│  │  • 输入：用户反馈文本 + Prompt                │          │
│  │  • 输出：结构化JSON分析结果                   │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 🔄 设计模式

1. **分层架构模式**：职责清晰分离
   - 展示层：前端UI
   - 接口层：API路由
   - 业务层：分析逻辑
   - 数据层：文件存储

2. **策略模式**：可扩展的分析策略
   - 当前：LLM驱动的定性分析
   - 未来：可添加其他分析策略

3. **编排模式**：
   - `SurveyAnalysisEngine`作为编排者
   - 协调数据加载、分析、报告生成

---

## 核心组件

### 1. SurveyAnalysisEngine（分析引擎）

**位置**：`app/services/analysis_engine.py`

**职责**：统一的分析入口和流程编排

**核心方法**：
```python
def analyze(survey_id: str) -> Dict[str, Any]:
    """
    完整的分析流程：
    1. 加载问卷和回答数据
    2. 提取开放题回答
    3. 执行定性分析
    4. 生成Markdown报告
    5. 返回结构化结果
    """
```

**数据加载**：
```python
def _load_data(survey_id: str) -> Tuple[Dict, List[Dict]]:
    """
    - 从 data/surveys/ 加载问卷模板
    - 从 data/responses/{survey_title}_{survey_id}/ 加载所有回答
    - 支持多种文件名格式
    """
```

**数据提取**：
```python
def _extract_open_ended_responses(survey, responses) -> List[str]:
    """
    - 识别问卷中所有"开放式问题"类型的题目
    - 从所有回答中提取这些问题的答案
    - 处理多种答案格式（字典/字符串）
    - 返回纯文本列表
    """
```

**输出格式**：
```json
{
  "survey_id": "83f37184",
  "survey_title": "博美犬饲养习惯与偏好调查问卷",
  "total_responses": 102,
  "open_ended_responses_count": 510,
  "analysis_type": "定性分析",
  "status": "success",
  "report": {
    "summary": "总体摘要...",
    "themes": [...],
    "recommendation": "行动建议..."
  },
  "formatted_report": "# Markdown格式报告..."
}
```

### 2. QualitativeAnalyzer（定性分析器）

**位置**：`app/services/qualitative_analyzer.py`

**职责**：执行核心的定性分析逻辑

**初始化**：
```python
def __init__(llm_model="qwen-plus", temperature=0.7):
    """
    - 初始化DashScope LLM客户端
    - 配置模型参数
    """
    self.llm_client = ChatDashScope(
        model=llm_model,
        temperature=temperature
    )
```

**核心分析方法**：
```python
def analyze_open_ended_responses(responses: List[str]) -> SurveyAnalysisReport:
    """
    Pipeline:
    1. 预处理：_preprocess_responses()
       - 去除空白
       - 过滤短回答（<3字符）
       - 去重
    
    2. LLM分析：_perform_qualitative_analysis()
       - 构建分析Prompt
       - 调用LLM
       - 解析JSON响应
       - 验证数据模型
    
    3. 返回：SurveyAnalysisReport对象
    """
```

**Prompt工程**：
```python
prompt = f"""你是一名专业的定性分析专家...

【分析要求】
1. 主题编码：识别3-8个核心主题
2. 情感判断：positive/negative/neutral
3. 引述提取：找到代表性用户原话
4. 频次估算：1-10相对频次
5. 主题描述：简短说明

【用户反馈文本】（共 {total_count} 条）
{combined_text}

【输出要求】
严格JSON格式：
{{
    "summary": "总体摘要...",
    "themes": [
        {{
            "theme": "主题名称",
            "sentiment": "positive|negative|neutral",
            "quote": "代表性引述",
            "count": 5,
            "description": "主题描述"
        }}
    ],
    "recommendation": "行动建议..."
}}
"""
```

**报告生成**：
```python
def generate_report(report: SurveyAnalysisReport) -> str:
    """
    生成Markdown格式报告：
    # 问卷定性分析报告
    ## 总体摘要
    ## 核心主题分析
      ### ✅ 积极反馈主题
      ### ⚠️ 需要关注的主题
      ### 📋 中性反馈主题
    ## 💡 行动建议
    """
```

### 3. AnalysisToolkit（分析工具包）

**位置**：`app/utils/analysis_toolkit.py`

**职责**：提供各种分析工具（当前未使用，但保留用于扩展）

**可用工具**：

1. **用户聚类** `tool_cluster_users()`
   - 算法：KMeans
   - 输入：量表题数据
   - 输出：用户群体特征

2. **主题提取** `tool_extract_themes()`
   - 算法：LDA（潜在狄利克雷分配）
   - 输入：文本回答
   - 输出：主题关键词

3. **情感分析** `tool_analyze_sentiment()`
   - 算法：关键词匹配
   - 输入：文本回答
   - 输出：情感分布比例

4. **关键词提取** `tool_extract_keywords()`
   - 算法：TF-IDF + 词频统计
   - 输入：文本回答
   - 输出：高频关键词

5. **统计摘要** `tool_statistics_summary()`
   - 算法：描述性统计
   - 输入：问卷和回答
   - 输出：基础统计信息

### 4. 数据模型

**位置**：`app/models/analysis_models.py`

**Pydantic模型**：

```python
class Sentiment(str, Enum):
    """情感倾向枚举"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class Theme(BaseModel):
    """主题编码模型"""
    theme: str              # 主题名称
    sentiment: Sentiment    # 情感倾向
    quote: str             # 代表性引述
    count: int             # 提及频次
    description: Optional[str]  # 主题描述

class SurveyAnalysisReport(BaseModel):
    """问卷定性分析报告"""
    summary: str           # 总体摘要
    themes: List[Theme]    # 主题列表
    recommendation: str    # 行动建议
```

**作用**：
- ✅ 类型安全
- ✅ 数据验证
- ✅ 自动文档
- ✅ JSON序列化

---

## 数据流程

### 📊 完整数据流

```
┌─────────────┐
│  用户点击    │
│  "分析"按钮  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  前端发起请求                            │
│  POST /api/analyze/{survey_id}          │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  FastAPI路由处理                         │
│  run_all.py#analyze_survey_results()    │
│  - 接收survey_id                        │
│  - 创建SurveyAnalysisEngine              │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 1: 数据加载                        │
│  SurveyAnalysisEngine._load_data()      │
│  - 读取问卷模板JSON                      │
│  - 读取所有回答JSON                      │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 2: 数据提取                        │
│  _extract_open_ended_responses()        │
│  - 识别开放题ID                          │
│  - 从回答中提取文本                      │
│  - 返回纯文本列表                        │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 3: 数据预处理                      │
│  QualitativeAnalyzer._preprocess()      │
│  - 去除空白                             │
│  - 过滤短文本                           │
│  - 去重                                │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 4: 构建Prompt                     │
│  _perform_qualitative_analysis()        │
│  - 合并所有文本                         │
│  - 构建分析指令                         │
│  - 指定输出格式                         │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 5: 调用LLM                        │
│  ChatDashScope.invoke()                 │
│  - 发送到通义千问API                    │
│  - 等待响应（15-30秒）                  │
│  - 接收JSON响应                         │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 6: 解析响应                        │
│  - 清理Markdown标记                     │
│  - JSON解析                             │
│  - Pydantic模型验证                     │
│  - 创建SurveyAnalysisReport对象         │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 7: 生成报告                        │
│  generate_report()                      │
│  - 转换为Markdown格式                    │
│  - 按情感分组                           │
│  - 添加时间戳                           │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 8: 保存结果                        │
│  - 保存到data/analyses/                 │
│  - 文件名：analysis_{survey_id}.json    │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Step 9: 返回响应                        │
│  - JSON格式                             │
│  - 包含结构化数据和Markdown报告          │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  前端展示                                │
│  - 解析JSON                             │
│  - 渲染Markdown                         │
│  - 展示主题和建议                        │
└─────────────────────────────────────────┘
```

### 🔧 数据转换示例

**原始回答数据**：
```json
{
  "survey_id": "83f37184",
  "answers": {
    "1": "博美犬",
    "5": "它的性格很温顺，很喜欢和人互动，而且很聪明"
  }
}
```

**提取后的文本**：
```python
[
  "它的性格很温顺，很喜欢和人互动，而且很聪明",
  "博美犬很活泼，需要经常遛弯",
  "毛发需要定期打理，有点麻烦"
  # ... 更多文本
]
```

**LLM返回的JSON**：
```json
{
  "summary": "用户对博美犬整体评价积极，认为性格温顺、聪明活泼，但也提到了毛发打理和运动需求方面的挑战。",
  "themes": [
    {
      "theme": "性格温顺友好",
      "sentiment": "positive",
      "quote": "它的性格很温顺，很喜欢和人互动",
      "count": 8,
      "description": "用户普遍认为博美犬性格好，适合家庭饲养"
    },
    {
      "theme": "毛发打理麻烦",
      "sentiment": "negative",
      "quote": "毛发需要定期打理，有点麻烦",
      "count": 5,
      "description": "毛发护理是主要的饲养挑战"
    }
  ],
  "recommendation": "1. 强调博美犬性格优势进行推广\n2. 提供毛发护理指南和服务\n3. 建议准备充足的运动时间"
}
```

**最终输出**：
```json
{
  "survey_id": "83f37184",
  "survey_title": "博美犬饲养习惯与偏好调查问卷",
  "total_responses": 102,
  "open_ended_responses_count": 510,
  "status": "success",
  "report": {
    "summary": "...",
    "themes": [...],
    "recommendation": "..."
  },
  "formatted_report": "# Markdown报告..."
}
```

---

## 算法技术

### 1. 核心技术：大语言模型（LLM）

**使用的模型**：
- **提供商**：阿里云DashScope
- **模型**：qwen-plus（通义千问Plus）
- **参数**：
  - Temperature: 0.7（平衡创造性和准确性）
  - Max tokens: 自动（根据输入长度）

**选择理由**：
1. ✅ **中文理解能力强**：针对中文文本优化
2. ✅ **结构化输出**：可以按JSON格式输出
3. ✅ **上下文理解**：能理解复杂的分析任务
4. ✅ **成本效益**：比GPT-4更经济

**Prompt工程技巧**：
1. **角色设定**："你是一名专业的定性分析专家"
2. **任务分解**：明确列出5个子任务
3. **格式约束**：严格指定JSON格式
4. **示例引导**：提供输出格式示例
5. **验证要求**：强调数据准确性

### 2. 辅助技术栈（AnalysisToolkit中）

#### KMeans聚类
**算法**：K-Means Clustering
**库**：scikit-learn
**用途**：用户分群

```python
from sklearn.cluster import KMeans

# 对量表题数据进行聚类
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
cluster_labels = kmeans.fit_predict(data_matrix)
```

**应用场景**：
- 识别不同满意度群体
- 发现用户类型
- 分群统计分析

#### LDA主题建模
**算法**：Latent Dirichlet Allocation
**库**：scikit-learn
**用途**：无监督主题提取

```python
from sklearn.decomposition import LatentDirichletAllocation

# LDA主题建模
lda = LatentDirichletAllocation(n_components=5, random_state=42)
lda.fit(tfidf_matrix)
```

**应用场景**：
- 自动发现文本主题
- 主题分布分析
- 关键词提取

#### TF-IDF
**算法**：Term Frequency-Inverse Document Frequency
**库**：scikit-learn
**用途**：文本向量化

```python
from sklearn.feature_extraction.text import TfidfVectorizer

vectorizer = TfidfVectorizer(max_features=500, min_df=1)
tfidf_matrix = vectorizer.fit_transform(texts)
```

**应用场景**：
- 提取重要词汇
- 文本相似度计算
- 特征工程

#### 中文分词
**库**：jieba（结巴分词）
**用途**：中文文本预处理

```python
import jieba

words = jieba.lcut("这是一段中文文本")
# ['这是', '一段', '中文', '文本']
```

**应用场景**：
- 分词
- 关键词提取
- 停用词过滤

### 3. 数据验证技术

#### Pydantic
**库**：Pydantic v2
**用途**：数据模型和验证

```python
from pydantic import BaseModel, Field

class Theme(BaseModel):
    theme: str = Field(..., description="主题名称")
    sentiment: Sentiment = Field(..., description="情感倾向")
    count: int = Field(..., ge=0, description="提及频次")
```

**功能**：
- ✅ 类型检查
- ✅ 数据验证
- ✅ JSON序列化
- ✅ 自动文档

---

## API接口

### 1. 分析接口

**端点**：`POST /api/analyze/{survey_id}`

**请求**：
```http
POST /api/analyze/83f37184 HTTP/1.1
Host: localhost:8002
Content-Type: application/json
```

**响应**（成功）：
```json
{
  "success": true,
  "survey_id": "83f37184",
  "survey_title": "博美犬饲养习惯与偏好调查问卷",
  "total_responses": 102,
  "open_ended_responses_count": 510,
  "analysis_type": "定性分析",
  "status": "success",
  "report": {
    "summary": "用户对博美犬整体评价积极...",
    "themes": [
      {
        "theme": "性格温顺友好",
        "sentiment": "positive",
        "quote": "它的性格很温顺，很喜欢和人互动",
        "count": 8,
        "description": "用户普遍认为博美犬性格好"
      }
    ],
    "recommendation": "1. 强调博美犬性格优势..."
  },
  "formatted_report": "# 问卷定性分析报告\n\n## 📊 总体摘要\n..."
}
```

**响应**（无开放题）：
```json
{
  "success": true,
  "survey_id": "83f37184",
  "survey_title": "...",
  "total_responses": 50,
  "analysis_type": "定性分析",
  "status": "no_open_ended_questions",
  "message": "问卷中没有开放题，无法进行定性分析",
  "report": null
}
```

**响应**（错误）：
```json
{
  "success": false,
  "survey_id": "83f37184",
  "status": "error",
  "message": "找不到问卷 83f37184",
  "report": null
}
```

### 2. 分析页面

**端点**：`GET /survey/{survey_id}?action=analyze`

**功能**：
- 展示分析界面
- 提供"开始分析"按钮
- 实时显示分析进度
- 渲染分析结果

---

## 使用示例

### 示例1：完整分析流程

```python
# 1. 初始化分析引擎
from app.services.analysis_engine import SurveyAnalysisEngine

analyzer = SurveyAnalysisEngine(
    llm_model="qwen-plus",
    temperature=0.7
)

# 2. 执行分析
result = analyzer.analyze(survey_id="83f37184")

# 3. 检查状态
if result["status"] == "success":
    report = result["report"]
    print(f"识别主题数：{len(report['themes'])}")
    print(f"总体摘要：{report['summary']}")
    
    # 4. 按情感分组
    for theme in report["themes"]:
        print(f"{theme['theme']} - {theme['sentiment']}")
else:
    print(f"分析失败：{result['message']}")
```

### 示例2：直接使用定性分析器

```python
from app.services.qualitative_analyzer import QualitativeAnalyzer

# 1. 初始化
analyzer = QualitativeAnalyzer(llm_model="qwen-plus")

# 2. 准备数据
responses = [
    "产品质量很好，非常满意",
    "价格有点贵，但物有所值",
    "配送速度快，包装也很好"
]

# 3. 执行分析
report = analyzer.analyze_open_ended_responses(responses)

# 4. 生成Markdown报告
markdown_report = analyzer.generate_report(report)
print(markdown_report)
```

### 示例3：使用分析工具包

```python
from app.utils.analysis_toolkit import AnalysisToolkit

toolkit = AnalysisToolkit()

# 1. 关键词提取
keywords_result = toolkit.tool_extract_keywords(responses, top_k=10)
print(keywords_result["summary"])

# 2. 情感分析
sentiment_result = toolkit.tool_analyze_sentiment(responses)
print(f"积极: {sentiment_result['positive_percentage']}%")

# 3. 统计摘要
stats = toolkit.tool_statistics_summary(survey, responses)
print(stats["summary"])
```

---

## 扩展性设计

### 🔧 当前架构的扩展点

#### 1. 添加新的分析方法
```python
class QualitativeAnalyzer:
    def analyze_by_aspect(self, responses, aspects):
        """按预定义方面进行分析"""
        pass
    
    def compare_groups(self, group1, group2):
        """对比不同群体的回答"""
        pass
```

#### 2. 支持多种LLM
```python
class LLMFactory:
    @staticmethod
    def create_llm(provider, model):
        if provider == "dashscope":
            return ChatDashScope(model=model)
        elif provider == "openai":
            return ChatOpenAI(model=model)
        elif provider == "anthropic":
            return ChatAnthropic(model=model)
```

#### 3. 添加缓存机制
```python
class CachedAnalyzer:
    def __init__(self, cache_dir="data/analysis_cache"):
        self.cache_dir = cache_dir
    
    def analyze_with_cache(self, survey_id):
        # 检查缓存
        cache_file = f"{self.cache_dir}/{survey_id}.json"
        if os.path.exists(cache_file):
            return load_cache(cache_file)
        
        # 执行分析
        result = self.analyzer.analyze(survey_id)
        
        # 保存缓存
        save_cache(cache_file, result)
        return result
```

#### 4. 支持批量分析
```python
class BatchAnalyzer:
    def analyze_multiple(self, survey_ids):
        """批量分析多个问卷"""
        results = {}
        for survey_id in survey_ids:
            results[survey_id] = self.analyze(survey_id)
        return results
    
    def compare_surveys(self, survey_ids):
        """对比多个问卷的分析结果"""
        pass
```

#### 5. 实时分析
```python
async def analyze_streaming(survey_id):
    """流式返回分析结果"""
    async for chunk in llm.astream(prompt):
        yield {
            "type": "progress",
            "content": chunk
        }
```

### 🎯 未来改进方向

1. **性能优化**
   - 添加Redis缓存
   - 异步分析任务
   - 结果预计算

2. **功能增强**
   - 多维度分析
   - 时间序列分析
   - 对比分析

3. **可视化**
   - 词云图
   - 情感趋势图
   - 主题分布图

4. **导出功能**
   - PDF报告
   - Excel数据
   - PPT演示

---

## 总结

### ✅ 当前实现的核心优势

1. **LLM驱动**：利用大语言模型的强大理解能力
2. **结构化输出**：Pydantic模型确保数据质量
3. **模块化设计**：各组件职责清晰，易于维护
4. **可扩展架构**：预留了多种扩展点
5. **用户友好**：Markdown报告易读易懂

### 🎯 技术栈总览

- **核心**：LangChain + DashScope LLM
- **数据验证**：Pydantic
- **辅助分析**：scikit-learn, jieba
- **Web框架**：FastAPI
- **数据存储**：JSON文件

### 📊 分析能力

✅ **当前支持**：
- 开放题定性分析
- 主题识别
- 情感分析
- 行动建议生成

🔜 **未来计划**：
- 定量数据聚类
- 多维度对比分析
- 实时分析
- 可视化报表

---

**文档版本**：v1.0  
**更新日期**：2025-10-30  
**维护者**：AI Survey Assistant Team

