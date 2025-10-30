"""
全量分析服务
综合分析问卷的所有题型，生成深度诊断报告
"""

import json
import logging
from typing import Dict, Any, List
from collections import Counter
from langchain_dashscope import ChatDashScope
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.analysis_models import (
    QuestionResult, 
    FullAnalysisDataReport, 
    FullAnalysisReport
)
from app.services.qualitative_analyzer import QualitativeAnalyzer
from app.services.visualization_service import VisualizationService

logger = logging.getLogger(__name__)


class FullAnalysisService:
    """全量分析服务 - 从描述统计到智能诊断"""
    
    def __init__(self, llm_model: str = "qwen-plus", temperature: float = 0.3):
        """
        初始化全量分析服务
        
        Args:
            llm_model: LLM模型名称
            temperature: 温度参数（分析时用较低温度保证严谨性）
        """
        self.llm_model = llm_model
        self.temperature = temperature
        
        # 初始化LLM客户端 - 增加max_tokens以支持更长的报告输出
        self.llm_client = ChatDashScope(
            model=llm_model,
            temperature=temperature,
            model_kwargs={
                "max_tokens": 8000,  # 显著增加输出长度限制
                "result_format": "message"
            }
        )
        
        # 初始化定性分析器（用于处理开放题）
        self.qualitative_analyzer = QualitativeAnalyzer(llm_model, temperature=0.7)
        
        # 初始化可视化服务
        self.viz_service = VisualizationService()
        
        logger.info(f"全量分析服务初始化完成，模型: {llm_model}")
    
    def analyze_full_survey(
        self, 
        survey: Dict[str, Any], 
        responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行全量分析
        
        Pipeline:
        1. 准备数据报告（统计所有题型）
        2. 生成可视化图表（为所有题型）
        3. 生成分析提示词
        4. 调用LLM进行深度分析
        5. 返回Markdown报告 + 可视化数据
        
        Args:
            survey: 问卷数据
            responses: 所有回答数据
            
        Returns:
            包含report_markdown和visualizations的字典
        """
        logger.info(f"开始全量分析，问卷: {survey.get('title')}, 回答数: {len(responses)}")
        
        # 1. 准备数据报告
        data_report = self._prepare_data_report(survey, responses)
        
        # 2. 生成可视化图表
        logger.info("生成全量分析可视化图表...")
        visualizations = self._generate_full_visualizations(survey, responses, data_report)
        
        # 3. 生成分析提示词
        prompt = self._generate_analysis_prompt(data_report)
        
        # 4. 调用LLM
        logger.info("调用LLM进行全量分析...")
        try:
            messages = [
                SystemMessage(content="""你是一位资深的数据分析师与战略顾问，拥有10年以上的调研分析经验。
你擅长从数据中发现深层洞察，善于关联不同维度的信息，能够提出具有战略价值的建议。
你的分析报告必须使用严格的Markdown格式，结构清晰，论据充分，建议可落地。

重要提示：请务必生成完整的报告，不要截断内容。确保所有章节都完整输出。"""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm_client.invoke(messages)
            markdown_report = response.content.strip()
            
            # 清理可能的代码块标记
            if "```markdown" in markdown_report:
                markdown_report = markdown_report.split("```markdown")[1].split("```")[0].strip()
            elif "```" in markdown_report:
                parts = markdown_report.split("```")
                for part in parts:
                    if "#" in part and len(part) > 100:
                        markdown_report = part.strip()
                        break
            
            # 检查报告完整性
            is_complete = self._check_report_completeness(markdown_report)
            
            logger.info(f"全量分析完成，报告长度: {len(markdown_report)} 字符，完整性: {'✓' if is_complete else '✗ 可能不完整'}, 可视化图表数: {len(visualizations)}")
            
            if not is_complete:
                logger.warning("报告可能不完整，建议检查LLM输出")
                markdown_report += "\n\n---\n\n**⚠️ 注意**: 由于报告内容较多，部分内容可能未完整显示。完整分析结果请下载PDF报告查看。"
            
            return {
                "report_markdown": markdown_report,
                "visualizations": visualizations,
                "is_complete": is_complete
            }
            
        except Exception as e:
            logger.error(f"全量分析失败: {e}", exc_info=True)
            raise RuntimeError(f"全量分析失败: {str(e)}")
    
    def _prepare_data_report(
        self, 
        survey: Dict[str, Any], 
        responses: List[Dict[str, Any]]
    ) -> FullAnalysisDataReport:
        """
        准备数据报告：将所有问题的结果统计出来
        
        这是关键一步，要把原始数据变成LLM能理解的"故事梗概"
        """
        question_results = []
        
        for question in survey.get("questions", []):
            q_id = str(question.get("id", ""))
            q_type = question.get("type", "")
            q_text = question.get("text", "")
            
            # 收集该问题的所有答案
            answers = []
            for response in responses:
                answer_data = response.get("answers", {}).get(q_id)
                if answer_data is not None:
                    answers.append(answer_data)
            
            if not answers:
                continue
            
            # 根据题型生成统计摘要
            result_summary = self._generate_result_summary(question, answers)
            
            question_results.append(QuestionResult(
                question_title=q_text,
                question_type=q_type,
                response_count=len(answers),
                result_summary=result_summary
            ))
        
        return FullAnalysisDataReport(
            survey_title=survey.get("title", ""),
            survey_description=survey.get("description", ""),
            total_respondents=len(responses),
            question_results=question_results
        )
    
    def _generate_result_summary(
        self, 
        question: Dict[str, Any], 
        answers: List[Any]
    ) -> Dict[str, Any]:
        """
        为不同题型生成统计摘要
        
        将枯燥的原始数据变成LLM能轻松理解的"故事梗概"
        """
        q_type = question.get("type", "")
        summary = {}
        
        try:
            if q_type == "量表题":
                # 处理量表题：计算平均分、分布
                numeric_answers = []
                for ans in answers:
                    try:
                        if isinstance(ans, dict):
                            val = float(ans.get("value", 0))
                        else:
                            val = float(ans)
                        numeric_answers.append(val)
                    except (ValueError, TypeError):
                        continue
                
                if numeric_answers:
                    avg_score = sum(numeric_answers) / len(numeric_answers)
                    score_counts = Counter(numeric_answers)
                    
                    # 判断整体倾向
                    scale_min = question.get("scale_min", 1)
                    scale_max = question.get("scale_max", 5)
                    mid_point = (scale_min + scale_max) / 2
                    
                    if avg_score >= mid_point + 1:
                        tendency = "正面"
                    elif avg_score <= mid_point - 1:
                        tendency = "负面"
                    else:
                        tendency = "中性"
                    
                    summary = {
                        "average_score": round(avg_score, 2),
                        "score_distribution": dict(score_counts),
                        "scale_range": f"{scale_min}-{scale_max}",
                        "tendency": tendency,
                        "insight": f"本题平均得分为{avg_score:.2f}（{scale_min}-{scale_max}分），显示出{tendency}的评价倾向。"
                    }
            
            elif q_type == "单选题":
                # 处理单选题：统计选项分布
                text_answers = []
                for ans in answers:
                    if isinstance(ans, dict):
                        text_answers.append(ans.get("value", ""))
                    else:
                        text_answers.append(str(ans))
                
                option_counts = Counter(text_answers)
                total = len(text_answers)
                
                if option_counts:
                    top_option, top_count = option_counts.most_common(1)[0]
                    top_percentage = (top_count / total * 100) if total > 0 else 0
                    
                    summary = {
                        "option_distribution": dict(option_counts),
                        "top_choice": top_option,
                        "top_percentage": round(top_percentage, 1),
                        "insight": f"大多数受访者（{top_percentage:.1f}%）选择了「{top_option}」。"
                    }
            
            elif q_type == "多选题":
                # 处理多选题：展开所有选项计数
                all_choices = []
                for ans in answers:
                    if isinstance(ans, dict):
                        choices = ans.get("value", [])
                    else:
                        choices = ans if isinstance(ans, list) else [ans]
                    all_choices.extend(choices)
                
                option_counts = Counter(all_choices)
                if option_counts:
                    top_3 = option_counts.most_common(3)
                    summary = {
                        "selection_frequency": dict(option_counts),
                        "most_selected": [{"option": opt, "count": cnt} for opt, cnt in top_3],
                        "insight": f"最常被选择的选项是「{top_3[0][0]}」（{top_3[0][1]}次）。"
                    }
            
            elif q_type == "开放式问题":
                # 处理开放题：调用定性分析
                text_answers = []
                for ans in answers:
                    if isinstance(ans, dict):
                        text = ans.get("value", "")
                    else:
                        text = str(ans)
                    if text and text.strip():
                        text_answers.append(text.strip())
                
                if text_answers:
                    try:
                        # 调用定性分析引擎
                        qualitative_report = self.qualitative_analyzer.analyze_open_ended_responses(text_answers)
                        
                        summary = {
                            "main_themes": [t.theme for t in qualitative_report.themes[:5]],
                            "representative_quotes": [t.quote for t in qualitative_report.themes[:3]],
                            "sentiment_summary": self._summarize_sentiment(qualitative_report.themes),
                            "insight": qualitative_report.summary[:200] + "..." if len(qualitative_report.summary) > 200 else qualitative_report.summary
                        }
                    except Exception as e:
                        logger.warning(f"开放题分析失败: {e}")
                        summary = {
                            "insight": f"收集到{len(text_answers)}条文本回答。",
                            "sample_quote": text_answers[0] if text_answers else ""
                        }
        
        except Exception as e:
            logger.warning(f"生成统计摘要失败: {e}")
            summary = {"insight": f"该题共收到{len(answers)}个回答。"}
        
        return summary
    
    def _summarize_sentiment(self, themes) -> str:
        """总结主题的情感倾向"""
        sentiments = [t.sentiment.value for t in themes]
        sentiment_counts = Counter(sentiments)
        
        if sentiment_counts.get("positive", 0) > sentiment_counts.get("negative", 0):
            return "整体偏积极"
        elif sentiment_counts.get("negative", 0) > sentiment_counts.get("positive", 0):
            return "整体偏消极"
        else:
            return "褒贬参半"
    
    def _generate_analysis_prompt(self, data_report: FullAnalysisDataReport) -> str:
        """
        生成全量分析提示词
        
        这是整个模块的大脑，负责将"分析简报"转化为"战略洞察"
        """
        # 1. 构建数据背景部分
        prompt = f"""
【调研概述】
调研主题：{data_report.survey_title}
"""
        if data_report.survey_description:
            prompt += f"调研说明：{data_report.survey_description}\n"
        
        prompt += f"有效样本量：{data_report.total_respondents} 份\n"
        prompt += f"问题总数：{len(data_report.question_results)} 个\n"
        
        # 2. 详细列出每个问题的统计结果
        prompt += "\n【详细数据结果】\n"
        
        for i, q_result in enumerate(data_report.question_results, 1):
            prompt += f"\n{i}. {q_result.question_title}\n"
            prompt += f"   类型：{q_result.question_type}  |  回答数：{q_result.response_count}\n"
            
            summary = q_result.result_summary
            
            # 根据题型展示关键信息
            if "insight" in summary:
                prompt += f"   主要发现：{summary['insight']}\n"
            
            if q_result.question_type == "量表题" and "average_score" in summary:
                prompt += f"   平均分：{summary['average_score']} / {summary.get('scale_range', '')}\n"
                if "score_distribution" in summary:
                    dist = summary['score_distribution']
                    prompt += f"   分数分布：{dist}\n"
            
            elif q_result.question_type == "单选题" and "top_choice" in summary:
                prompt += f"   首选：{summary['top_choice']} ({summary.get('top_percentage', 0)}%)\n"
            
            elif q_result.question_type == "多选题" and "most_selected" in summary:
                top_items = summary['most_selected'][:3]
                prompt += f"   高频选项：{', '.join([f'{item['option']}({item['count']}次)' for item in top_items])}\n"
            
            elif q_result.question_type == "开放式问题":
                if "main_themes" in summary:
                    prompt += f"   核心主题：{', '.join(summary['main_themes'][:3])}\n"
                if "representative_quotes" in summary and summary["representative_quotes"]:
                    prompt += f"   典型引述：「{summary['representative_quotes'][0]}」\n"
                if "sentiment_summary" in summary:
                    prompt += f"   情感倾向：{summary['sentiment_summary']}\n"
        
        # 3. 定义分析任务和要求
        prompt += """

【你的分析任务】
基于以上数据，生成一份结构化的战略诊断报告。

【输出要求 - 极其重要】
1. 报告必须完整，包含所有六个核心章节
2. 每个章节内容要精炼，避免冗长叙述
3. 使用严格的Markdown格式
4. 务必输出到结论部分，不得中途截断

【输出格式模板】

```markdown
# 全量分析诊断报告

## 一、核心摘要
[2-3句话概括最关键发现]

## 二、关键发现
### 发现1：[标题]（重要性：高/中/低）
- **数据**：[具体数字]
- **解读**：[1-2句说明]

[继续列出3-5个发现，每个控制在3行以内]

## 三、交叉洞察
### 3.1 关联模式
[2-3个关键关联，每个1句话]

### 3.2 因果推断
[2-3个因果关系，每个1句话]

### 3.3 群体对比
[用表格或简短文字对比2-3个群体]

## 四、关键少数派
### 4.1 强烈不满群体
[特征+诉求，2-3句]

### 4.2 高价值群体
[特征+价值点，2-3句]

## 五、风险与机会
### 🚨 主要风险
1. [风险+数据]
2. [风险+数据]
3. [风险+数据]

### ✨ 核心机会
1. [机会+数据]
2. [机会+数据]
3. [机会+数据]

## 六、战略建议
### 建议1（优先级：高）
**行动**：[做什么]  
**依据**：[为什么]  
**效果**：[预期结果]

[继续2-4条建议，每条控制在3行]

## 七、结论
[1-2句总结全文]
```

【关键约束】
- 每个章节必须完整输出
- 优先保证结构完整性，而非细节丰富度
- 如果内容过长，优先精简描述文字，保留数据支撑
- 结论部分必须出现，标志报告完整
"""
        
        return prompt
    
    def _check_report_completeness(self, markdown_report: str) -> bool:
        """
        检查报告是否完整
        
        检查标准：
        1. 是否包含"结论"章节
        2. 报告长度是否合理
        3. 是否存在明显的截断特征
        
        Args:
            markdown_report: Markdown格式的报告内容
            
        Returns:
            True表示完整，False表示可能不完整
        """
        # 检查1: 是否包含结论部分
        if "## 七、结论" not in markdown_report and "## 结论" not in markdown_report:
            return False
        
        # 检查2: 报告长度是否过短（通常完整报告应该有一定长度）
        if len(markdown_report) < 1000:
            return False
        
        # 检查3: 是否存在明显的截断特征（以句子中间结束）
        last_100_chars = markdown_report[-100:].strip()
        # 如果最后不是以标点符号结束，可能被截断
        incomplete_endings = [char for char in last_100_chars[-1:] if char not in '。！？\n"\'\u3001\uff09\u3011\u300b']
        if incomplete_endings and not any(marker in last_100_chars for marker in ["## 七、结论", "## 结论"]):
            return False
        
        # 检查4: 是否包含关键章节
        required_sections = ["## 一、核心摘要", "## 二、关键发现", "## 五、风险与机会", "## 六、战略建议"]
        missing_sections = [section for section in required_sections if section not in markdown_report]
        
        if len(missing_sections) > 1:  # 允许少量章节缺失，但不能太多
            return False
        
        return True
    
    def _generate_full_visualizations(
        self,
        survey: Dict[str, Any],
        responses: List[Dict[str, Any]],
        data_report: FullAnalysisDataReport
    ) -> Dict[str, str]:
        """
        为全量分析生成综合可视化图表
        
        包含：
        1. 所有量表题的分布图
        2. 所有选择题的分布图
        3. 开放题的词云、主题分布、情感分布
        
        Args:
            survey: 问卷数据
            responses: 回答数据
            data_report: 数据报告
            
        Returns:
            可视化图表字典
        """
        visualizations = {}
        
        try:
            # 1. 处理每个问题，生成对应的可视化
            for i, q_result in enumerate(data_report.question_results):
                q_type = q_result.question_type
                summary = q_result.result_summary
                
                # 量表题：生成分布柱状图
                if q_type == "量表题" and "score_distribution" in summary:
                    chart = self.viz_service.generate_scale_distribution_chart(
                        data=summary["score_distribution"],
                        question_title=q_result.question_title[:30] + "...",  # 截短标题
                        scale_range=summary.get("scale_range", "1-5")
                    )
                    if chart:
                        visualizations[f"scale_q{i+1}"] = chart
                        logger.info(f"✓ 量表题 {i+1} 可视化生成成功")
                
                # 单选题：生成横向柱状图
                elif q_type == "单选题" and "option_distribution" in summary:
                    chart = self.viz_service.generate_choice_distribution_chart(
                        data=summary["option_distribution"],
                        question_title=q_result.question_title[:30] + "...",
                        max_items=10
                    )
                    if chart:
                        visualizations[f"single_choice_q{i+1}"] = chart
                        logger.info(f"✓ 单选题 {i+1} 可视化生成成功")
                
                # 多选题：生成横向柱状图
                elif q_type == "多选题" and "selection_frequency" in summary:
                    chart = self.viz_service.generate_choice_distribution_chart(
                        data=summary["selection_frequency"],
                        question_title=q_result.question_title[:30] + "...",
                        max_items=10
                    )
                    if chart:
                        visualizations[f"multiple_choice_q{i+1}"] = chart
                        logger.info(f"✓ 多选题 {i+1} 可视化生成成功")
                
                # 开放题：生成词云和主题分布
                elif q_type == "开放式问题":
                    # 收集该题的所有文本答案
                    question_id = None
                    for q in survey.get("questions", []):
                        if q.get("text") == q_result.question_title or q.get("text", "")[:30] == q_result.question_title[:30]:
                            question_id = str(q.get("id", ""))
                            break
                    
                    if question_id:
                        text_answers = []
                        for response in responses:
                            answer_data = response.get("answers", {}).get(question_id)
                            if answer_data:
                                if isinstance(answer_data, dict):
                                    text = answer_data.get("value", "")
                                else:
                                    text = str(answer_data)
                                if text and text.strip():
                                    text_answers.append(text.strip())
                        
                        if text_answers and len(text_answers) >= 5:
                            # 生成词云
                            wordcloud = self.viz_service.generate_wordcloud(
                                text_answers,
                                title=f"Q{i+1}: {q_result.question_title[:20]}..."
                            )
                            if wordcloud:
                                visualizations[f"wordcloud_q{i+1}"] = wordcloud
                                logger.info(f"✓ 开放题 {i+1} 词云生成成功")
                            
                            # 如果已经有主题分析结果，生成主题分布图
                            if "main_themes" in summary and summary["main_themes"]:
                                # 为主题添加计数信息（简单估算）
                                themes_with_count = [
                                    {"theme": theme, "count": len(text_answers) // len(summary["main_themes"])}
                                    for theme in summary["main_themes"][:5]
                                ]
                                theme_chart = self.viz_service.generate_theme_distribution_chart(
                                    themes_with_count,
                                    title=f"Q{i+1} 主题分布"
                                )
                                if theme_chart:
                                    visualizations[f"themes_q{i+1}"] = theme_chart
                                    logger.info(f"✓ 开放题 {i+1} 主题分布图生成成功")
            
            # 2. 生成全局汇总图表
            # 统计所有开放题的文本用于生成总体词云
            all_open_texts = []
            for q_result in data_report.question_results:
                if q_result.question_type == "开放式问题":
                    summary = q_result.result_summary
                    if "representative_quotes" in summary:
                        all_open_texts.extend(summary["representative_quotes"])
            
            if all_open_texts:
                overall_wordcloud = self.viz_service.generate_wordcloud(
                    all_open_texts,
                    title=f"{data_report.survey_title} - 整体主题词云"
                )
                if overall_wordcloud:
                    visualizations["overall_wordcloud"] = overall_wordcloud
                    logger.info("✓ 整体词云生成成功")
            
            logger.info(f"全量分析可视化完成，共生成 {len(visualizations)} 个图表")
            
        except Exception as e:
            logger.warning(f"生成全量分析可视化时出错: {e}", exc_info=True)
        
        return visualizations


