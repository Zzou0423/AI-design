"""
定性分析引擎
核心分析模块：从原始文本数据到结构化洞察
"""

import json
import logging
from typing import List, Optional, Dict, Any
from langchain_dashscope import ChatDashScope
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.analysis_models import SurveyAnalysisReport, Theme, Sentiment

logger = logging.getLogger(__name__)


class QualitativeAnalyzer:
    """定性分析引擎 - 核心分析类"""
    
    def __init__(self, llm_model: str = "qwen-flash", temperature: float = 0.7):
        """
        初始化定性分析器
        
        Args:
            llm_model: LLM模型名称（默认 qwen-flash）
            temperature: 温度参数（控制输出的创造性）
        """
        self.llm_model = llm_model
        self.temperature = temperature
        
        # 初始化LLM客户端
        try:
            self.llm_client = ChatDashScope(
                model=llm_model,
                temperature=temperature
            )
            logger.info(f"定性分析器初始化成功，使用模型: {llm_model}")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            self.llm_client = None
            raise
    
    def analyze_open_ended_responses(self, responses: List[str]) -> SurveyAnalysisReport:
        """
        核心分析方法：对一批开放题答案进行定性分析
        
        Args:
            responses: 开放题答案列表
            
        Returns:
            SurveyAnalysisReport: 结构化的分析报告
        """
        if not self.llm_client:
            raise RuntimeError("LLM客户端未初始化，请检查API配置")
        
        if not responses:
            raise ValueError("回答列表为空，无法进行分析")
        
        logger.info(f"开始分析 {len(responses)} 条开放题回答")
        
        # 1. 数据预处理：清洗、去噪、合并
        cleaned_responses = self._preprocess_responses(responses)
        logger.info(f"预处理完成，有效回答: {len(cleaned_responses)} 条")
        
        # 2. 调用LLM进行主题编码与内容分析
        analysis_result = self._perform_qualitative_analysis(cleaned_responses)
        
        logger.info(f"分析完成，识别出 {len(analysis_result.themes)} 个主题")
        return analysis_result
    
    def _preprocess_responses(self, responses: List[str]) -> List[str]:
        """
        数据预处理：清洗、去噪、合并
        
        Args:
            responses: 原始回答列表
            
        Returns:
            清洗后的回答列表
        """
        cleaned = []
        
        for response in responses:
            if not response:
                continue
            
            # 去除空白字符
            cleaned_response = response.strip()
            
            # 过滤掉太短的回答（少于3个字符）
            if len(cleaned_response) < 3:
                continue
            
            # 过滤掉重复的回答（简单的去重）
            if cleaned_response not in cleaned:
                cleaned.append(cleaned_response)
        
        return cleaned
    
    def _perform_qualitative_analysis(self, responses: List[str]) -> SurveyAnalysisReport:
        """
        执行定性分析核心逻辑
        
        核心思路：设计强大的提示词，引导LLM一次性完成：
        - 主题编码：识别并归纳核心主题
        - 情感判断工作量：对每个主题进行情感倾向判断
        - 引述提取：找到代表性用户原话
        - 频次估算：估算主题提及的相对频次
        
        Args:
            responses: 清洗后的回答列表
            
        Returns:
            SurveyAnalysisReport: 分析结果
        """
        # 合并所有回答，形成分析文本
        combined_text = "\n".join([f"- {resp}" for resp in responses])
        total_count = len(responses)
        
        # 构建分析提示词
        prompt = f"""你是一名专业的定性分析专家，拥有超过10年的问卷设计和数据分析经验。请对以下用户反馈进行深入的主题分析和内容分析。

【分析要求】

1. **主题编码**：识别并归纳出反馈中出现的核心主题（3-8个），每个主题用简短的短语概括（如"工作时间过长"、"团队氛围良好"等）。

2. **情感判断**：对每个主题下的内容进行情感倾向判断，必须是以下之一：
   - "positive"：积极正面的反馈
   - "negative"：消极负面的反馈
   - "neutral"：中性或混合的反馈

3. **引述提取**：为每个主题找到1-2句最具代表性的用户原话作为引述，确保引述准确反映主题内容。

4. **频次估算**：基于讨论的强度和提及次数，估算每个主题被提及的相对频次（整数，1-10之间）。

5. **主题描述**：为每个主题提供简短的描述性说明。

【用户反馈文本】（共 {total_count} 条回答）

{combined_text}

【输出要求】

请严格按照以下JSON格式输出，不要有任何多余的解释或Markdown代码块标记：

{{
    "summary": "总体摘要（150-200字），概括所有反馈的核心内容和主要发现",
    "themes": [
        {{
            "theme": "主题名称",
            "sentiment": "positive|negative|neutral",
            "quote": "代表性用户原话引述",
            "count": 5,
            "description": "主题的简短描述"
        }}
    ],
    "recommendation": "具体的行动建议（200-300字），基于分析结果提出可操作的建议"
}}

重要提示：
- 确保JSON格式完全正确
- 主题数量控制在3-8个之间
- 引述必须是用户原话，不要修改
- 情感判断要客观准确
- 建议要具体、可操作
"""
        
        try:
            # 调用LLM进行分析
            messages = [
                SystemMessage(content="你是一位专业的定性分析专家，擅长从文本中提取主题、分析情感倾向并提供行动建议。你必须严格遵循JSON格式输出。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm_client.invoke(messages)
            content = response.content.strip()
            
            # 清理响应内容：移除可能的Markdown代码块标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # 尝试提取JSON部分
                parts = content.split("```")
                for part in parts:
                    if "{" in part and "themes" in part:
                        content = part.strip()
                        break
            
            # 解析JSON
            try:
                result_dict = json.loads(content)
                
                # 验证和转换数据
                themes = []
                for theme_data in result_dict.get("themes", []):
                    try:
                        theme = Theme(
                            theme=theme_data.get("theme", ""),
                            sentiment=Sentiment(theme_data.get("sentiment", "neutral")),
                            quote=theme_data.get("quote", ""),
                            count=theme_data.get("count", 0),
                            description=theme_data.get("description", "")
                        )
                        themes.append(theme)
                    except Exception as e:
                        logger.warning(f"主题数据解析失败: {e}, 数据: {theme_data}")
                        continue
                
                # 构建报告对象
                report = SurveyAnalysisReport(
                    summary=result_dict.get("summary", ""),
                    themes=themes,
                    recommendation=result_dict.get("recommendation", "")
                )
                
                return report
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"响应内容: {content[:500]}")
                raise ValueError(f"LLM返回的JSON格式不正确: {str(e)}")
                
        except Exception as e:
            logger.error(f"定性分析执行失败: {e}", exc_info=True)
            raise RuntimeError(f"定性分析失败: {str(e)}")
    
    def analyze_by_dimensions(
        self, 
        responses: List[str], 
        dimensions: List[str]
    ) -> Dict[str, SurveyAnalysisReport]:
        """
        按预设维度进行分析
        
        例如：按"产品功能"、"用户体验"、"价格"等维度分类分析
        
        Args:
            responses: 回答列表
            dimensions: 预设的分析维度列表
            
        Returns:
            每个维度对应的分析报告字典
        """
        if not dimensions:
            # 如果没有指定维度，直接进行全局分析
            return {"all": self.analyze_open_ended_responses(responses)}
        
        results = {}
        
        for dimension in dimensions:
            # 为每个维度构建专门的提示词
            dimension_prompt = f"""请特别关注"{dimension}"相关的反馈内容。"""
            
            # 这里可以扩展为更复杂的维度过滤逻辑
            # 目前简化实现：全局分析但在提示词中强调该维度
            # TODO: 可以实现基于关键词的预过滤
            
            try:
                report = self.analyze_open_ended_responses(responses)
                results[dimension] = report
            except Exception as e:
                logger.error(f"维度 {dimension} 分析失败: {e}")
                results[dimension] = None
        
        return results
    
    def generate_report(self, report: SurveyAnalysisReport) -> str:
        """
        将分析结果生成一份易读的Markdown报告
        
        Args:
            report: 分析报告对象
            
        Returns:
            Markdown格式的报告字符串
        """
        markdown = f"""# 问卷定性分析报告

## 📊 总体摘要

{report.summary}

---

## 🎯 核心主题分析

"""
        
        # 按情感倾向分组展示主题
        positive_themes = [t for t in report.themes if t.sentiment == Sentiment.POSITIVE]
        negative_themes = [t for t in report.themes if t.sentiment == Sentiment.NEGATIVE]
        neutral_themes = [t for t in report.themes if t.sentiment == Sentiment.NEUTRAL]
        
        # 积极主题
        if positive_themes:
            markdown += "### ✅ 积极反馈主题\n\n"
            for theme in positive_themes:
                markdown += f"""#### {theme.theme}

- **情感倾向**: 积极（Positive）
- **代表性引述**: 
  > "{theme.quote}"
- **提及频次**: {theme.count}
- **说明**: {theme.description or "无"}

"""
        
        # 消极主题
        if negative_themes:
            markdown += "### ⚠️ 需要关注的主题\n\n"
            for theme in negative_themes:
                markdown += f"""#### {theme.theme}

- **情感倾向**: 消极（Negative）
- **代表性引述**: 
  > "{theme.quote}"
- **提及频次**: {theme.count}
- **说明**: {theme.description or "无"}

"""
        
        # 中性主题
        if neutral_themes:
            markdown += "### 📋 中性反馈主题\n\n"
            for theme in neutral_themes:
                markdown += f"""#### {theme.theme}

- **情感倾向**: 中性（Neutral）
- **代表性引述**: 
  > "{theme.quote}"
- **提及频次**: {theme.count}
- **说明**: {theme.description or "无"}

"""
        
        markdown += f"""---

## 💡 行动建议

{report.recommendation}

---

**分析完成时间**: {self._get_current_time()}
"""
        
        return markdown
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

