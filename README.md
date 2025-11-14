# AI 问卷助手

基于 RAG（检索增强生成）和大语言模型的智能问卷生成与分析工具。

## 📖 快速导航

- **🚀 快速开始**: 👉 查看 [`docs/QUICKSTART.md`](docs/QUICKSTART.md) - **5分钟快速入门指南**
- **📚 完整文档**: 继续阅读本文档
- **🏗️ 项目结构**: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- **🛠️ 脚本工具**: [`scripts/generate_responses.py`](scripts/generate_responses.py) - 批量回答生成器
- **💡 故障排除**: [`docs/`](docs/) 目录 - 各类技术文档

---

## ✨ 核心功能

- 🤖 **AI 智能生成**: 根据需求自动生成专业问卷
- 📝 **多种题型支持**: 单选题、多选题、量表题、开放题
- ✏️ **问卷编辑功能**: 复制问卷创建新版本，支持全方面编辑
- 👤 **用户系统**: 注册、登录和个人问卷管理
- 🔗 **可分享链接**: 一键生成和复制问卷链接
- 📊 **数据存储**: 回答自动保存到本地
- 🤖 **批量回答生成**: AI 生成问卷测试回答，支持模拟多种身份
- 🧠 **智能分析**: AI 驱动的开放题分析，自动提取主题和洞察
- 🎨 **现代界面**: 美观友好的用户界面设计

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

创建 `.env` 文件：

```
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 启动系统

```bash
python run_all.py
```

或使用启动脚本：

```bash
start.bat
```

浏览器将自动打开 http://localhost:8002

### 4. 测试账号

为了便于开源测试，您可以使用以下测试账号：

- **用户名**: Zzou001
- **密码**: 124536

您也可以自行注册新账号使用系统。

## 🎨 核心功能详解

### ✨ 智能需求扩展
- AI 作为行业专家帮助完善需求
- 将简短描述扩展为专业、详细的调研需求

### 📊 可视化进度
- 实时显示生成步骤
- 进度条和状态动画
- 当前进度的清晰反馈

### ✏️ 完整编辑功能
- 编辑问卷基本信息
- 添加/删除/修改问题
- 调整选项和量表范围
- 更改问题类型

### 🔗 一键分享
- 发布问卷生成可分享链接
- 一键复制分享给他人
- 独立的填写页面

## 📖 使用指南

### 生成问卷

1. 注册/登录账号
2. 在首页输入问卷需求（例如："产品满意度调查"）
3. 点击"生成问卷"按钮
4. 等待 AI 生成问卷（约 15-30 秒）
5. 编辑问卷（可选）
6. 保存问卷

### 管理问卷

1. 进入"工作空间"查看所有问卷
2. 查看、分享、分析或删除问卷
3. 点击"分享"获取问卷链接
4. 将链接发送给他人填写

### 填写问卷

1. **单选题**：点击选项进行选择
2. **多选题**：勾选多个选项
3. **量表题**：点击 1-5 数字进行评分
4. **开放题**：在文本框中输入答案

### 查看回答

回答自动保存在 `data/responses/{survey_title}_{survey_id}/` 文件夹中，每个回答对应一个 JSON 文件。

### 批量生成问卷回答（AI 辅助）

如果需要生成批量测试数据用于分析和测试，可以使用 `generate_responses.py` 脚本。

#### 功能说明

该脚本使用大语言模型（LLM）自动生成真实的问卷回答：
- 🎯 **通用适配**：自动列出所有问卷，支持任意主题
- 🎭 **智能身份生成**：根据问卷主题自动生成受访者身份
- 📝 **高质量回答**：生成逻辑一致、自然流畅的回答
- 🔄 **批量生成**：支持批量生成，可自定义数量
- 💾 **自动保存**：回答自动保存到对应问卷目录

#### 使用方法

**交互式使用（推荐）**：

```bash
python generate_responses.py
```

脚本会自动：
1. 列出所有可用问卷
2. 显示每个问卷的现有回答数量
3. 允许您选择要生成回答的问卷
4. 输入要生成的回答数量（默认：30）
5. 自动生成并保存回答

#### 特性

- **智能身份生成**：脚本调用 LLM 根据问卷主题生成 15 种不同类型的受访者身份
- **倾向控制** ✨：可以指定回答的整体倾向（积极/消极/中性/混合/随机）
  - 用于验证分析结果准确性
  - 生成带标签的测试数据
  - 自动显示倾向分布统计和预期分析结果
- **并发生成** 🚀：支持多线程并发生成，显著提高速度
  - 默认：5 个并发线程（可调整 3-10）
  - 30 个回答：约 1-2 分钟（之前为 3-5 分钟）
  - 100 个回答：约 3-6 分钟（之前为 10-15 分钟）
- **实时进度显示**：显示批量进度、已用时间、预计剩余时间
- **容错机制**：单个回答生成失败不会中断整个过程

## 🔧 API 接口

### 用户相关
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `POST /api/logout` - 用户登出
- `GET /api/user/info` - 获取用户信息
- `GET /api/user/surveys` - 获取用户问卷列表
- `DELETE /api/user/surveys/{survey_id}` - 删除问卷

### 问卷相关
- `POST /api/generate` - 生成问卷（流式响应）
- `POST /api/save-survey` - 保存问卷
- `GET /api/survey/{survey_id}` - 获取问卷
- `GET /api/survey/{survey_id}/stats` - 获取统计信息

### 回答相关
- `POST /api/submit-response` - 提交问卷回答
- `GET /fill/{survey_id}` - 独立填写页面

### 分析相关
- `POST /api/analyze/{survey_id}` - 分析问卷结果
  - 请求体：`{"analysis_type": "open_ended"}` 或 `{"analysis_type": "full"}`
  - `open_ended`：仅分析开放题（默认）
  - `full`：分析所有题型
- `GET /survey/{survey_id}?action=analyze` - 分析页面

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代 Web 框架
- **LangChain** - AI 应用开发框架
- **ChromaDB** - 向量数据库
- **DashScope** - 阿里云通义千问大语言模型
- **Pydantic** - 数据验证和建模

### 前端
- **原生 JavaScript** - 前端交互逻辑
- **HTML/CSS** - 用户界面
- **Server-Sent Events** - 实时流式响应

### 数据处理
- **Pandas** - 数据处理
- **Matplotlib** - 图表绘制
- **WordCloud** - 词云生成
- **Pillow** - 图像处理

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

## 📁 项目结构

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
│   ├── 📂 responses/                # 问卷回答文件（JSON）
│   └── 📂 analyses/                 # 分析结果文件（JSON + 图表）
│
├── 📂 docs/                         # 项目文档
│   ├── QUICKSTART.md                # 快速开始指南
│   ├── PROJECT_STRUCTURE.md         # 项目结构文档
│   ├── ANALYSIS_ARCHITECTURE.md     # 分析功能架构
│   └── PERFORMANCE_OPTIMIZATION.md  # 性能优化文档
│
├── 📂 rag_materials/                 # RAG参考资料
│   ├── README.md                    # 资料说明
│   └── *.pdf                        # 参考文档
│
└── 📂 scripts/                      # 辅助脚本
    ├── generate_responses.py        # 批量生成回答脚本
    ├── backup.sh                    # 备份脚本
    └── check_deployment.py          # 部署检查脚本
```

## 📝 注意事项

1. **API 调用成本**：生成问卷和分析需要调用 LLM API，会产生费用
   - 生成一份问卷：约 0.1-0.3 元（取决于问卷长度）
   - 分析一份问卷：约 0.3-0.5 元（取决于回答数量）

2. **数据安全**：所有数据保存在本地 `data/` 目录，建议定期备份

3. **性能优化**：
   - 批量生成回答时，建议设置 3-5 个并发线程
   - 大型问卷分析可能需要较长时间，建议分批处理

4. **浏览器兼容性**：支持 Chrome、Firefox、Safari、Edge 等现代浏览器

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进项目！

## 📄 许可证

MIT License

---

# AI Survey Assistant

An intelligent survey generation and analysis tool based on RAG (Retrieval-Augmented Generation) and large language models.

## 📖 Quick Navigation

- **🚀 Getting Started**: 👉 Check [`docs/QUICKSTART.md`](docs/QUICKSTART.md) - **5-minute Quick Start Guide**
- **📚 Complete Documentation**: Continue reading this document
- **🏗️ Project Structure**: [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
- **🛠️ Script Tools**: [`scripts/generate_responses.py`](scripts/generate_responses.py) - Batch Answer Generator
- **💡 Troubleshooting**: [`docs/`](docs/) directory - Various technical documents

---

## ✨ Core Features

- 🤖 **AI-Powered Generation**: Automatically generate professional surveys based on requirements
- 📝 **Multiple Question Types**: Single choice, multiple choice, Likert scale, open-ended questions
- ✏️ **Survey Editing**: Copy surveys to create new versions with full editing capabilities
- 👤 **User System**: Registration, login, and personal survey management
- 🔗 **Shareable Links**: One-click generation and copying of survey links
- 📊 **Data Storage**: Answers automatically saved locally
- 🤖 **Batch Answer Generation**: AI-generated test answers for surveys, supporting multiple identity simulations
- 🧠 **Intelligent Analysis**: AI-driven open-ended question analysis with automatic theme extraction and insights
- 🎨 **Modern Interface**: Beautiful and user-friendly design

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. Start the System

```bash
python run_all.py
```

Or use the startup script:

```bash
start.bat
```

Your browser will automatically open to http://localhost:8002

## 🎨 Core Features Details

### ✨ Intelligent Requirement Expansion
- AI acts as an industry expert to help refine your requirements
- Expands brief descriptions into professional, detailed survey requirements

### 📊 Visual Progress
- Real-time display of generation steps
- Progress bars and status animations
- Clear feedback on current progress

### ✏️ Full Editing Capabilities
- Edit basic survey information
- Add/delete/modify questions
- Adjust options and scale ranges
- Change question types

### 🔗 One-Click Sharing
- Publish surveys to generate shareable links
- One-click copying to share with others
- Independent filling pages

## 📖 Usage Guide

### Generate a Survey

1. Register/login to your account
2. Enter survey requirements on the homepage (e.g., "Product Satisfaction Survey")
3. Click the "Generate Survey" button
4. Wait for AI to generate the survey (approximately 15-30 seconds)
5. Edit the survey (optional)
6. Save the survey

### Manage Surveys

1. Enter "Workspace" to view all surveys
2. View, share, analyze, or delete surveys
3. Click "Share" to get the survey link
4. Send the link to others to fill out

### Fill Out a Survey

1. **Single Choice**: Click an option to select
2. **Multiple Choice**: Check multiple options
3. **Likert Scale**: Click a number from 1-5 to rate
4. **Open-ended Questions**: Enter your answer in the text box

### View Responses

Responses are automatically saved in the `data/responses/{survey_title}_{survey_id}/` folder, with one JSON file per response.

### Batch Generate Survey Responses (AI-Assisted)

If you need to generate batch test data for analysis and testing, you can use the `generate_responses.py` script.

#### Feature Description

This script uses large language models (LLM) to automatically generate realistic survey answers:
- 🎯 **Universal Adaptation**: Automatically lists all surveys, supporting any topic
- 🎭 **Smart Identity Generation**: Automatically generates respondent identities based on survey topics
- 📝 **High-Quality Answers**: Generates logically consistent, natural-sounding answers
- 🔄 **Batch Generation**: Supports batch generation with customizable quantity
- 💾 **Automatic Saving**: Answers automatically saved to the corresponding survey directory

#### Usage

**Interactive Usage (Recommended)**: 

```bash
python generate_responses.py
```

The script will automatically:
1. List all available surveys
2. Show the number of existing answers for each survey
3. Allow you to select the survey for answer generation
4. Enter the number of answers to generate (default: 30)
5. Automatically generate and save answers

#### Features

- **Smart Identity Generation**: The script calls LLM to generate 15 different types of respondent identities based on the survey topic
- **Tendency Control** ✨: Can specify the overall tendency of answers (positive/negative/neutral/mixed/random)
  - For verifying analysis result accuracy
  - Generating labeled test data
  - Automatically displays tendency distribution statistics and expected analysis results
- **Concurrent Generation** 🚀: Supports multi-threaded concurrent generation for significantly improved speed
  - Default: 5 concurrent threads (adjustable 3-10)
  - 30 answers: ~1-2 minutes (previously 3-5 minutes)
  - 100 answers: ~3-6 minutes (previously 10-15 minutes)
- **Real-time Progress Display**: Shows batch progress, elapsed time, estimated remaining time
- **Error Tolerance**: Failed generation of a single answer won't interrupt the entire process

## 🔧 API Interface

### User-related
- `POST /api/register` - User Registration
- `POST /api/login` - User Login
- `POST /api/logout` - User Logout
- `GET /api/user/info` - Get User Information
- `GET /api/user/surveys` - Get User Survey List
- `DELETE /api/user/surveys/{survey_id}` - Delete Survey

### Survey-related
- `POST /api/generate` - Generate Survey (Streaming Response)
- `POST /api/save-survey` - Save Survey
- `GET /api/survey/{survey_id}` - Get Survey
- `GET /api/survey/{survey_id}/stats` - Get Statistics

### Response-related
- `POST /api/submit-response` - Submit Survey Answer
- `GET /fill/{survey_id}` - Independent Filling Page

### Analysis-related
- `POST /api/analyze/{survey_id}` - Analyze Survey Results
  - Request Body: `{"analysis_type": "open_ended"}` or `{"analysis_type": "full"}`
  - `open_ended`: Analyze only open-ended questions (default)
  - `full`: Full analysis of all question types
- `GET /survey/{survey_id}?action=analyze` - Analysis Page

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Web Framework
- **LangChain** - AI Application Development Framework
- **ChromaDB** - Vector Database
- **DashScope** - Alibaba Cloud Tongyi Qianwen Large Language Model
- **Pydantic** - Data Validation and Modeling

### Frontend
- **Native JavaScript** - Frontend Interaction Logic
- **HTML/CSS** - User Interface
- **Server-Sent Events** - Real-time Streaming Responses

### Data Processing
- **Pandas** - Data Processing
- **Matplotlib** - Chart Drawing
- **WordCloud** - Word Cloud Generation
- **Pillow** - Image Processing

## 📊 Data Flow

### 1. Survey Generation Process

```
User Input → Frontend(app.js) → API(/api/generate)
                                      ↓
                              SurveyService.generate_survey()
                                      ↓
                              RAG Retrieval + LLM Generation
                                      ↓
                              Save to data/surveys/
                                      ↓
                              Return JSON → Frontend Display
```

### 2. Survey Filling Process

```
User Access Survey Link → Load HTML(fill_survey.js)
                        ↓
                   User Fills and Submits
                        ↓
                   API(/api/submit_response)
                        ↓
                   ResponseSaver.save_response()
                        ↓
                   Save to data/responses/{survey_id}/
```

### 3. Analysis Process

```
User Clicks Analyze → API(/api/analyze/{survey_id})
                        ↓
            Select Analysis Type (open_ended / full)
                        ↓
          ┌─────────────┴─────────────┐
          ↓                           ↓
    SurveyAnalysisEngine      FullAnalysisService
          ↓                           ↓
    Open-ended Analysis              Full Analysis
          ↓                           ↓
    Generate Visualization           Generate Visualization
          ↓                           ↓
    Return Report + Charts ← ──────────── Return Report + Charts
                        ↓
                   Frontend Display
```

## 📁 Project Structure

```
ai_survey_assistant/
│
├── 📄 run_all.py                    # Main Entry - FastAPI Application
├── 📄 generate_responses.py         # Batch Survey Answer Generation Script (with tendency control)
├── 📄 start.bat                     # Windows Quick Start Script
├── 📄 requirements.txt              # Python Dependencies
├── 📄 README.md                     # Project Main Documentation
├── 📄 .gitignore                    # Git Ignore Configuration
│
├── 📂 app/                          # Core Application Code
│   ├── __init__.py
│   │
│   ├── 📂 chains/                   # LangChain Chains
│   │   ├── __init__.py
│   │   └── survey_creation_chain.py  # RAG-Enhanced Survey Generation Chain
│   │
│   ├── 📂 core/                     # Core Functionality
│   │   ├── __init__.py
│   │   └── vector_store.py           # ChromaDB Vector Database Management
│   │
│   ├── 📂 models/                   # Data Models
│   │   ├── __init__.py
│   │   ├── analysis_models.py        # Analysis Models (Theme, Sentiment, Report, etc.)
│   │   └── user.py                   # User Model and Storage
│   │
│   ├── 📂 services/                 # Business Logic Services
│   │   ├── __init__.py
│   │   ├── survey_service.py         # Survey Generation Service (RAG + LLM)
│   │   ├── analysis_engine.py        # Open-ended Question Analysis Engine
│   │   ├── full_analysis_service.py  # Full Analysis Service (Quantitative + Qualitative)
│   │   ├── qualitative_analyzer.py   # Qualitative Analyzer (Thematic Coding)
│   │   └── visualization_service.py  # Data Visualization Service (Chart Generation)
│   │
│   └── 📂 utils/                    # Utility Functions
│       ├── __init__.py
│       ├── analysis_toolkit.py       # Analysis Toolkit
│       ├── response_saver.py         # Survey Response Saving
│       ├── session_manager.py        # User Session Management
│       └── user_survey_manager.py    # User-Survey Association Management
│
├── 📂 static/                       # Frontend Static Files
│   ├── login.html                    # Login Page
│   ├── workspace.html                # Workspace Page
│   ├── app.js                        # Survey Generation Interaction Logic
│   ├── fill_survey.js                # Survey Filling Interaction Logic
│   └── style.css                     # Global Styles
│
├── 📂 data/                         # Data Storage Directory
│   ├── 📂 surveys/                  # Survey Definition Files (JSON)
│   ├── 📂 responses/                # Survey Response Files (JSON)
│   └── 📂 analyses/                 # Analysis Result Files (JSON + Charts)
│
├── 📂 docs/                         # Project Documentation
│   ├── QUICKSTART.md                # Quick Start Guide
│   ├── PROJECT_STRUCTURE.md         # Project Structure Documentation
│   ├── ANALYSIS_ARCHITECTURE.md     # Analysis Function Architecture
│   └── PERFORMANCE_OPTIMIZATION.md  # Performance Optimization Documentation
│
├── 📂 rag_materials/                 # RAG Reference Materials
│   ├── README.md                    # Materials Description
│   └── *.pdf                        # Reference Documents
│
└── 📂 scripts/                      # Auxiliary Scripts
    ├── generate_responses.py        # Batch Answer Generation Script
    ├── backup.sh                    # Backup Script
    └── check_deployment.py          # Deployment Check Script
```

## 📝 Notes

1. **API Call Costs**: Generating surveys and analysis requires calling LLM APIs, which incur costs
   - Generating a survey: ~0.1-0.3 yuan (depending on survey length)
   - Analyzing a survey: ~0.3-0.5 yuan (depending on the number of responses)

2. **Data Security**: All data is saved in the local `data/` directory, regular backups are recommended

3. **Performance Optimization**:
   - When generating answers in batches, it is recommended to set 3-5 concurrent threads
   - Large survey analysis may take longer, it is recommended to process in batches

4. **Browser Compatibility**: Supports Chrome, Firefox, Safari, Edge and other modern browsers

## 🤝 Contribution

Welcome to submit Issues and Pull Requests to help improve the project!

## 📄 License

MIT License
