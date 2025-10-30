# 全量分析功能文档

## 📋 功能概述

全量分析是AI问卷助手的高级分析功能，能够综合分析问卷中的所有题型（单选题、多选题、量表题、开放题），提供深度的战略洞察和可落地的行动建议。

## 🎯 核心设计思路

### 从"描述统计"到"智能诊断"

**传统分析方式**：
- 生成N个饼图、柱状图
- 由人工去关联和解读各个图表
- 容易遗漏数据之间的关联关系

**全量分析方式**：
- 将所有数据（数字、选项、文本）一次性交给大模型
- 命令LLM："这是所有数据，请你作为一个分析师，给我写一份全面的诊断报告，要有关联、有对比、有深度的发现和建议。"
- 自动生成结构化的战略分析报告

## 🏗️ 技术架构

### 1. 数据模型层 (`app/models/analysis_models.py`)

```python
class QuestionResult(BaseModel):
    """每个问题的统计结果"""
    question_title: str
    question_type: str
    response_count: int
    result_summary: Dict[str, Any]

class FullAnalysisDataReport(BaseModel):
    """全量分析的数据输入结构"""
    survey_title: str
    total_respondents: int
    question_results: List[QuestionResult]

class FullAnalysisReport(BaseModel):
    """全量分析报告（Markdown格式）"""
    report_markdown: str
```

### 2. 数据统计层 (`app/services/full_analysis_service.py`)

为不同题型生成"统计摘要"：

#### 量表题
```python
{
    "average_score": 4.2,
    "score_distribution": {1: 2, 2: 5, 3: 10, 4: 20, 5: 13},
    "scale_range": "1-5",
    "tendency": "正面",
    "insight": "本题平均得分为4.20（1-5分），显示出正面的评价倾向。"
}
```

#### 单选题
```python
{
    "option_distribution": {"选项A": 30, "选项B": 15, "选项C": 5},
    "top_choice": "选项A",
    "top_percentage": 60.0,
    "insight": "大多数受访者（60.0%）选择了「选项A」。"
}
```

#### 多选题
```python
{
    "selection_frequency": {"选项A": 25, "选项B": 20, "选项C": 15},
    "most_selected": [
        {"option": "选项A", "count": 25},
        {"option": "选项B", "count": 20}
    ],
    "insight": "最常被选择的选项是「选项A」（25次）。"
}
```

#### 开放题
```python
{
    "main_themes": ["主题1", "主题2", "主题3"],
    "representative_quotes": ["引述1", "引述2"],
    "sentiment_summary": "整体偏积极",
    "insight": "用户反馈主要集中在..."
}
```

### 3. 分析引擎层

#### 核心Pipeline

```
1. 数据收集
   ↓
2. 题型分类统计
   ↓
3. 生成分析简报
   ↓
4. 构建LLM提示词
   ↓
5. LLM深度分析
   ↓
6. 生成Markdown报告
```

#### 提示词工程

提示词包含以下关键部分：

1. **数据背景**：调研概述、样本量、问题数
2. **详细数据**：每个问题的统计结果和洞察
3. **分析任务**：
   - 核心摘要
   - 关键发现
   - 深度交叉洞察
   - 关键少数派分析
   - 风险与机会识别
   - 战略建议与行动指南

### 4. API接口层 (`run_all.py`)

```python
@app.post("/api/analyze/{survey_id}")
async def analyze_survey_results(survey_id: str, request: FastAPIRequest):
    body = await request.json()
    analysis_type = body.get("analysis_type", "open_ended")
    
    if analysis_type == "full":
        # 执行全量分析
        full_analyzer = FullAnalysisService()
        full_report = full_analyzer.analyze_full_survey(survey, responses)
        return {"report_markdown": full_report.report_markdown}
    else:
        # 执行开放题分析
        ...
```

### 5. 前端交互层

- 用户选择分析类型（开放题 / 全量）
- 显示不同的加载提示
- 根据分析类型渲染结果

## 📊 分析报告结构

全量分析报告采用严格的Markdown格式，包含以下章节：

### 一、核心摘要
- 2-3句话精华总结
- 最关键的发现

### 二、关键发现
- 3-5个核心结论
- 每个发现包含：
  - 标题
  - 重要性等级（高/中/低）
  - 数据支撑
  - 分析解读

### 三、深度交叉洞察

#### 3.1 关联模式
- 不同问题之间的关联
- 例如："在A问题上打分高的人，在B问题上更倾向于选择X"

#### 3.2 因果推断
- 用量化数据解释定性现象
- 用定性反馈解释量化趋势

#### 3.3 群体对比
- 不同回答群体的特征差异

### 四、关键少数派分析

#### 4.1 强烈不满群体
- 占比不大但情绪强烈的群体
- 他们的诉求和问题

#### 4.2 高价值群体
- 满意度最高/最忠诚的群体
- 他们看重的因素

### 五、风险与机会

#### 🚨 主要风险
- 当前存在的最大风险点
- 负面主题被广泛提及的情况

#### ✨ 核心机会
- 最值得把握的机会点
- 被广泛认可的优势

### 六、战略建议与行动指南

每条建议包含：
- **行动内容**：具体做什么
- **数据依据**：为什么要这么做
- **预期效果**：期待什么结果

建议按优先级排序（优先级1、2、3...）

### 七、结论
- 总结性陈述

## 🔍 分析维度对比

| 维度 | 开放题分析 | 全量分析 |
|------|-----------|---------|
| **分析范围** | 仅开放式问题 | 所有题型 |
| **数据类型** | 文本 | 文本+数值+选项 |
| **分析深度** | 主题识别+情感分析 | 交叉洞察+因果推断+战略建议 |
| **报告长度** | 简短（500-1000字） | 详细（1500-3000字） |
| **分析时间** | 30-60秒 | 1-2分钟 |
| **适用场景** | 快速了解文本反馈 | 战略决策+深度诊断 |
| **建议样本量** | 10-20份 | 30-50份 |

## 💡 使用建议

### 何时使用开放题分析
- ✅ 快速了解用户的文本反馈
- ✅ 问卷主要包含开放式问题
- ✅ 样本量较小（10-20份）
- ✅ 需要快速迭代

### 何时使用全量分析
- ✅ 需要制定战略决策
- ✅ 问卷包含多种题型
- ✅ 样本量充足（30份以上）
- ✅ 需要深度洞察和交叉分析
- ✅ 需要识别风险和机会
- ✅ 需要可落地的行动建议

## 🔧 配置参数

```python
FullAnalysisService(
    llm_model="qwen-plus",      # LLM模型
    temperature=0.3             # 温度参数（分析时用低温保证严谨）
)
```

## 📈 性能优化

1. **温度设置**：全量分析使用较低温度（0.3）保证分析的严谨性
2. **开放题复用**：开放题部分调用已有的定性分析器
3. **数据预处理**：先统计再分析，减少LLM处理原始数据的负担
4. **结构化输出**：明确要求Markdown格式，便于前端渲染

## 🚀 未来扩展方向

1. **可视化增强**：在Markdown报告中嵌入图表
2. **导出功能**：支持导出PDF、Word格式
3. **对比分析**：支持多次调研结果的对比分析
4. **自定义分析维度**：允许用户指定关注的分析维度
5. **分析模板**：针对不同行业提供预设的分析模板

## 📚 相关文件

- `app/models/analysis_models.py` - 数据模型定义
- `app/services/full_analysis_service.py` - 全量分析服务实现
- `app/services/qualitative_analyzer.py` - 定性分析器（复用）
- `run_all.py` - API接口实现
- `README.md` - 用户文档

## 🎓 技术要点

1. **数据抽象**：将原始数据转化为LLM友好的"分析简报"
2. **提示词工程**：精心设计的提示词是核心竞争力
3. **模块复用**：开放题分析复用已有的定性分析器
4. **温度控制**：不同场景使用不同的温度参数
5. **结构化输出**：明确的输出格式要求保证结果质量

---

**版本**：1.0  
**更新时间**：2025-10-30  
**作者**：AI Survey Assistant Team

