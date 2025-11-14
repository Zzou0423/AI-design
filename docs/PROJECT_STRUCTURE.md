# AI问卷助手 - 项目结构文档

> 最后更新: 2025-10-30

## 📁 项目目录结构

```
ai_survey_assistant/
│
├── 📄 run_all.py                    # 主程序入口 - FastAPI应用
├── 📄 generate_responses.py         # 批量生成问卷答案脚本（支持倾向控制）
├── 📄 start.bat                     # Windows快速启动脚本
├── 📄 requirements.txt              # Python依赖包列表
├── 📄 README.md                     # 项目主文档
├── 📄 .gitignore                    # Git忽略文件配置
│
├── 📂 app/                          # 核心应用代码
│   ├── __init__.py
│   │
│   ├── 📂 chains/                   # LangChain链式调用
│   │   ├── __init__.py
│   │   └── survey_creation_chain.py  # RAG增强的问卷生成链
│   │
│   ├── 📂 core/                     # 核心功能模块
│   │   ├── __init__.py
│   │   └── vector_store.py           # ChromaDB向量数据库管理
│   │
│   ├── 📂 models/                   # 数据模型定义
│   │   ├── __init__.py
│   │   ├── analysis_models.py        # 分析相关模型（Theme, Sentiment, Report等）
│   │   └── user.py                   # 用户模型和用户存储
│   │
│   ├── 📂 services/                 # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── survey_service.py         # 问卷生成服务（RAG + LLM）
│   │   ├── analysis_engine.py        # 开放题分析引擎
│   │   ├── full_analysis_service.py  # 全量分析服务（量化+质化）
│   │   ├── qualitative_analyzer.py   # 定性分析器（主题编码）
│   │   └── visualization_service.py  # 数据可视化服务（图表生成）
│   │
│   └── 📂 utils/                    # 工具函数
│       ├── __init__.py
│       ├── analysis_toolkit.py       # 分析工具集
│       ├── response_saver.py         # 问卷回答保存
│       ├── session_manager.py        # 用户会话管理
│       └── user_survey_manager.py    # 用户问卷关联管理
│
├── 📂 static/                       # 前端静态文件
│   ├── login.html                    # 登录页面
│   ├── workspace.html                # 工作空间页面
│   ├── app.js                        # 问卷生成交互逻辑
│   ├── fill_survey.js                # 问卷填写交互逻辑
│   └── style.css                     # 全局样式表
│
├── 📂 data/                         # 数据存储目录
│   ├── 📂 surveys/                  # 问卷定义文件（JSON）
│   │   ├── .gitkeep
│   │   └── 在线问卷平台用户体验调研_a4a4125f.json  # 示例问卷
│   │
│   ├── 📂 responses/                # 问卷回答数据（按问卷分目录）
│   │   ├── .gitkeep
│   │   ├── 博美犬饲养习惯与偏好调查问卷_83f37184/
│   │   ├── 国产动漫观众偏好与观感调查问卷_eac47ac0/
│   │   └── 在线问卷平台用户体验调研_a4a4125f/
│   │
│   ├── 📂 analyses/                 # 分析结果文件
│   │   ├── .gitkeep
│   │   ├── analysis_{survey_id}_open_ended.json   # 开放题分析
│   │   └── analysis_{survey_id}_full.json         # 全量分析
│   │
│   ├── 📂 chroma_db/                # 向量数据库（RAG知识库）
│   │   ├── .gitkeep
│   │   └── [向量索引文件]
│   │
│   ├── users.json                   # 用户账号数据
│   ├── sessions.json                # 登录会话数据
│   └── user_surveys.json            # 用户-问卷关联关系
│
├── 📂 docs/                         # 项目文档
│   ├── PROJECT_STRUCTURE.md          # 本文档 - 项目结构说明
│   ├── ANALYSIS_ARCHITECTURE.md      # 分析架构设计文档
│   ├── CLEANUP_SUMMARY.md            # 项目清理总结
│   ├── FULL_ANALYSIS_FEATURE.md      # 全量分析功能文档
│   ├── IMPLEMENTATION_SUMMARY.md     # 功能实现总结
│   ├── PERFORMANCE_OPTIMIZATION.md   # 性能优化文档
│   ├── UI_UX_IMPROVEMENTS.md         # UI/UX改进文档
│   ├── VISUALIZATION_AND_TENDENCY_FEATURES.md  # 可视化与倾向控制
│   └── VISUALIZATION_ENHANCEMENT.md  # 可视化增强文档
│
└── 📂 venv/                         # Python虚拟环境（不纳入版本控制）

```

---

## 🏗️ 核心模块说明

### 1. **主程序 (`run_all.py`)**

FastAPI应用的主入口，包含：

- **API路由定义**
  - `POST /api/generate` - 生成问卷
  - `POST /api/enhance_demand` - 增强需求描述
  - `POST /api/register` - 用户注册
  - `POST /api/login` - 用户登录
  - `POST /api/submit_response` - 提交问卷回答
  - `POST /api/analyze/{survey_id}` - 分析问卷结果
  - `GET /api/user_surveys` - 获取用户问卷列表

- **HTML页面生成**
  - 问卷预览页面
  - 问卷填写页面
  - 分析结果展示页面
  - 问卷详情页面

- **静态文件服务**
  - 挂载`/static`路径

---

### 2. **问卷生成模块 (`app/chains/`, `app/services/survey_service.py`)**

#### RAG增强流程

```
用户需求
  ↓
需求增强 (LLM扩写)
  ↓
向量检索 (ChromaDB搜索相似问卷案例)
  ↓
提示词构建 (需求 + 案例 + 结构化指令)
  ↓
LLM生成 (通义千问)
  ↓
结构化问卷JSON
```

#### 关键功能

- **需求理解增强**: 将简短需求扩写为详细的调研目标和背景
- **案例检索**: 从向量库中检索Top-K相似问卷作为参考
- **智能生成**: 基于用户需求和案例，生成包含多种题型的问卷
- **题型支持**: 单选题、多选题、量表题、开放式问题

---

### 3. **分析模块**

#### 3.1 开放题分析 (`app/services/analysis_engine.py`)

```
问卷回答数据
  ↓
提取开放题回答
  ↓
定性分析 (QualitativeAnalyzer)
  ├─ 主题编码
  ├─ 情感分析
  └─ 代表性引述提取
  ↓
可视化生成 (VisualizationService)
  ├─ 词云图
  ├─ 主题分布柱状图
  └─ 情感分布饼图
  ↓
Markdown报告 + 可视化图表
```

**特点**:
- 使用LLM进行主题识别和编码
- 自动提取每个主题的代表性引述
- 生成结构化的定性分析报告

#### 3.2 全量分析 (`app/services/full_analysis_service.py`)

```
问卷所有题型
  ↓
数据准备
  ├─ 量表题: 计算均值、分布
  ├─ 单选题: 统计选项占比
  ├─ 多选题: 统计选择频次
  └─ 开放题: 调用定性分析
  ↓
可视化生成
  ├─ 量表题分布图
  ├─ 选择题分布图
  ├─ 开放题词云
  └─ 整体主题词云
  ↓
LLM深度分析
  ├─ 交叉洞察
  ├─ 关键少数派分析
  ├─ 风险与机会识别
  └─ 战略建议
  ↓
Markdown报告 + 全面可视化
```

**特点**:
- **从描述统计到智能诊断**: 不仅展示数据，更提供战略洞察
- **全题型覆盖**: 为每种题型生成对应的可视化
- **关联分析**: 寻找不同问题之间的关联模式
- **可落地建议**: 基于数据提出具体行动方案

---

### 4. **可视化服务 (`app/services/visualization_service.py`)**

#### 支持的图表类型

| 图表类型 | 应用场景 | 技术实现 |
|---------|---------|---------|
| 词云图 | 开放题高频词展示 | `wordcloud` + `matplotlib` |
| 主题分布柱状图 | 主题提及频次对比 | `matplotlib` 横向柱状图 |
| 情感分布饼图 | 积极/中性/消极占比 | `matplotlib` 饼图 |
| 量表分布图 | 1-5分等评分分布 | `matplotlib` 柱状图 |
| 选择题分布图 | 单选/多选选项统计 | `matplotlib` 横向柱状图 |

#### 特性

- **Base64编码**: 图表直接嵌入HTML，无需额外文件
- **中文支持**: 自动使用系统中文字体
- **内存高效**: 图表生成后立即清理matplotlib对象

---

### 5. **用户管理模块 (`app/models/user.py`, `app/utils/`)**

#### 核心功能

- **用户认证**: 注册、登录、会话管理
- **权限控制**: 用户只能访问自己创建的问卷
- **关联管理**: 维护用户-问卷的所属关系

#### 数据持久化

- `data/users.json`: 用户账号信息
- `data/sessions.json`: 登录会话token
- `data/user_surveys.json`: 用户问卷关联表

---

### 6. **批量答案生成 (`generate_responses.py`)**

#### 功能特性

- **交互式选择**: 列出所有问卷供用户选择
- **智能身份生成**: 基于问卷主题生成多样化的用户画像
- **倾向控制**: 支持指定答案倾向（积极/消极/中性/混合/随机）
- **并发生成**: 使用线程池加速批量生成
- **统计报告**: 输出倾向分布和预期分析结果

#### 使用方式

```bash
python generate_responses.py
```

交互流程:
1. 选择问卷
2. 设置生成数量
3. 选择倾向模式
4. 设置并发线程数
5. 开始生成

---

## 🔧 技术栈

### 后端核心

| 技术 | 版本 | 用途 |
|-----|------|-----|
| Python | 3.9+ | 主要编程语言 |
| FastAPI | - | Web框架 |
| LangChain | - | LLM应用框架 |
| DashScope | - | 阿里云通义千问API |
| ChromaDB | - | 向量数据库 |
| Pydantic | - | 数据验证 |

### 数据分析与可视化

| 技术 | 版本 | 用途 |
|-----|------|-----|
| matplotlib | >=3.7.0 | 图表绘制 |
| wordcloud | >=1.9.0 | 词云生成 |
| pillow | >=10.0.0 | 图像处理 |

### 前端

| 技术 | 用途 |
|-----|-----|
| HTML5 | 页面结构 |
| CSS3 | 样式设计 |
| JavaScript (原生) | 交互逻辑 |

---

## 📊 数据流转

### 1. 问卷生成流程

```
用户输入需求 → 前端(app.js) → API(/api/generate)
                                      ↓
                              SurveyService.generate_survey()
                                      ↓
                              RAG检索 + LLM生成
                                      ↓
                              保存到 data/surveys/
                                      ↓
                              返回JSON → 前端展示
```

### 2. 问卷填写流程

```
用户访问问卷链接 → 加载HTML(fill_survey.js)
                        ↓
                   用户填写并提交
                        ↓
                   API(/api/submit_response)
                        ↓
                   ResponseSaver.save_response()
                        ↓
                   保存到 data/responses/{survey_id}/
```

### 3. 分析流程

```
用户点击分析按钮 → API(/api/analyze/{survey_id})
                        ↓
            选择分析类型 (open_ended / full)
                        ↓
          ┌─────────────┴─────────────┐
          ↓                           ↓
    SurveyAnalysisEngine      FullAnalysisService
          ↓                           ↓
    开放题分析                    全量分析
          ↓                           ↓
    生成可视化                    生成可视化
          ↓                           ↓
    返回报告+图表 ← ──────────── 返回报告+图表
                        ↓
                   前端展示
```

---

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件并设置:

```bash
DASHSCOPE_API_KEY=your_api_key_here
```

### 启动系统

**方式一**: 使用批处理脚本（Windows）
```bash
start.bat
```

**方式二**: 直接运行Python
```bash
python run_all.py
```

### 访问系统

浏览器打开: http://localhost:8000

---

## 📝 开发建议

### 添加新题型

1. 在 `app/services/survey_service.py` 的提示词中添加题型说明
2. 在 `app/services/full_analysis_service.py` 中添加统计逻辑
3. 在 `app/services/visualization_service.py` 中添加对应图表方法

### 扩展分析维度

1. 修改 `app/services/full_analysis_service.py` 的 `_generate_analysis_prompt`
2. 在提示词中增加新的分析维度要求
3. 调整前端展示逻辑以适配新的报告结构

### 优化向量检索

1. 更新 `data/exemplary_surveys.pdf.pdf`（优质问卷案例集）
2. 运行向量化导入脚本重建ChromaDB索引
3. 调整 `app/core/vector_store.py` 中的检索参数（Top-K, 相似度阈值）

---

## 🔐 安全注意事项

1. **API密钥**: 务必通过环境变量配置，不要硬编码在代码中
2. **用户密码**: 生产环境应使用加密存储（如bcrypt），当前为明文存储
3. **会话管理**: 建议引入Redis等缓存中间件提升性能
4. **数据备份**: 定期备份 `data/` 目录下的关键文件

---

## 📈 性能优化建议

### 短期优化

- [ ] 使用异步I/O处理文件读写
- [ ] 对LLM调用结果进行缓存
- [ ] 优化向量检索的Batch处理

### 长期规划

- [ ] 引入任务队列（如Celery）处理耗时分析
- [ ] 使用PostgreSQL等关系型数据库替代JSON文件存储
- [ ] 前后端分离，使用React/Vue重构前端

---

## 📞 维护和支持

- **Bug反馈**: 通过Issues提交问题
- **功能建议**: 欢迎提交Pull Request
- **文档更新**: 保持与代码同步

---

*本文档会随项目更新持续维护，请关注版本变更记录。*

