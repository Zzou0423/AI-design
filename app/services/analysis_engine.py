"""
问卷分析引擎
整合数据处理和分析流程，提供统一的分析接口
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path

from app.services.qualitative_analyzer import QualitativeAnalyzer
from app.services.visualization_service import VisualizationService
from app.models.analysis_models import SurveyAnalysisReport

logger = logging.getLogger(__name__)


class SurveyAnalysisEngine:
    """问卷分析引擎 - 统一的分析入口"""
    
    def __init__(self, llm_model: str = "qwen-flash", temperature: float = 0.7):
        """
        初始化分析引擎
        
        Args:
            llm_model: LLM模型名称
            temperature: 温度参数
        """
        self.qualitative_analyzer = QualitativeAnalyzer(llm_model, temperature)
        self.viz_service = VisualizationService()
        logger.info("问卷分析引擎初始化完成")
    
    def analyze(self, survey_id: str) -> Dict[str, Any]:
        """
        执行完整的问卷分析
        
        Pipeline流程：
        1. 加载问卷和回答数据
        2. 提取开放题回答
        3. 数据预处理
        4. 定性分析（主题编码、内容分析）
        5. 生成结构化报告
        
        Args:
            survey_id: 问卷ID
            
        Returns:
            完整的分析结果字典
        """
        try:
            logger.info(f"开始分析问卷: {survey_id}")
            
            # 1. 加载数据
            survey, responses = self._load_data(survey_id)
            if not responses:
                raise ValueError(f"问卷 {survey_id} 没有找到回答数据")
            
            logger.info(f"数据加载完成: {len(responses)} 份回答")
            
            # 2. 提取开放题回答
            open_ended_responses = self._extract_open_ended_responses(survey, responses)
            
            if not open_ended_responses:
                return {
                    "survey_id": survey_id,
                    "survey_title": survey.get("title", ""),
                    "total_responses": len(responses),
                    "analysis_type": "定性分析",
                    "status": "no_open_ended_questions",
                    "message": "问卷中没有开放题，无法进行定性分析",
                    "report": None
                }
            
            logger.info(f"提取到 {len(open_ended_responses)} 条开放题回答")
            
            # 3. 执行定性分析
            analysis_report = self.qualitative_analyzer.analyze_open_ended_responses(
                open_ended_responses
            )
            
            # 4. 生成Markdown报告
            markdown_report = self.qualitative_analyzer.generate_report(analysis_report)
            
            # 5. 生成可视化图表
            logger.info("生成可视化图表...")
            visualizations = self._generate_visualizations(
                open_ended_responses, 
                analysis_report,
                survey.get("title", "")
            )
            
            # 6. 整合结果
            result = {
                "survey_id": survey_id,
                "survey_title": survey.get("title", ""),
                "total_responses": len(responses),
                "open_ended_responses_count": len(open_ended_responses),
                "analysis_type": "定性分析",
                "status": "success",
                "report": {
                    "summary": analysis_report.summary,
                    "themes": [
                        {
                            "theme": t.theme,
                            "sentiment": t.sentiment.value,
                            "quote": t.quote,
                            "count": t.count,
                            "description": t.description
                        }
                        for t in analysis_report.themes
                    ],
                    "recommendation": analysis_report.recommendation
                },
                "formatted_report": markdown_report,
                "visualizations": visualizations  # 添加可视化数据
            }
            
            logger.info(f"分析完成，识别出 {len(analysis_report.themes)} 个主题")
            return result
            
        except Exception as e:
            logger.error(f"分析失败: {e}", exc_info=True)
            return {
                "survey_id": survey_id,
                "status": "error",
                "message": str(e),
                "report": None
            }
    
    def _load_data(self, survey_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """加载问卷和回答数据"""
        # 加载问卷
        surveys_dir = Path("data/surveys")
        survey = None
        
        # 查找问卷文件
        for file_path in surveys_dir.glob(f"*{survey_id}.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("id") == survey_id:
                        survey = data
                        break
            except Exception:
                continue
        
        # 如果没找到，遍历所有文件
        if not survey:
            for file_path in surveys_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get("id") == survey_id:
                            survey = data
                            break
                except Exception:
                    continue
        
        if not survey:
            raise FileNotFoundError(f"找不到问卷 {survey_id}")
        
        # 加载回答
        responses_dir = Path("data/responses")
        responses = []
        
        # 查找包含survey_id的目录
        found_dir = None
        for item in responses_dir.iterdir():
            if item.is_dir() and survey_id in item.name:
                found_dir = item
                break
        
        if found_dir:
            for response_file in found_dir.glob("*.json"):
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                        if response_data.get("survey_id") == survey_id:
                            responses.append(response_data)
                except Exception as e:
                    logger.warning(f"无法加载回答文件 {response_file}: {e}")
                    continue
        
        return survey, responses
    
    def _extract_open_ended_responses(
        self, 
        survey: Dict[str, Any], 
        responses: List[Dict[str, Any]]
    ) -> List[str]:
        """
        提取所有开放题的回答
        
        Args:
            survey: 问卷数据
            responses: 回答数据列表
            
        Returns:
            开放题回答文本列表
        """
        open_ended_responses = []
        
        # 识别开放题
        open_ended_question_ids = []
        for question in survey.get("questions", []):
            if question.get("type") == "开放式问题":
                open_ended_question_ids.append(str(question.get("id", "")))
        
        if not open_ended_question_ids:
            logger.warning("问卷中没有开放题")
            return []
        
        # 提取所有开放题的回答
        for response in responses:
            answers = response.get("answers", {})
            for q_id in open_ended_question_ids:
                if q_id in answers:
                    answer_data = answers[q_id]
                    # 处理不同的答案格式
                    if isinstance(answer_data, dict):
                        # 标准格式: {"type": "开放式问题", "value": "回答文本"}
                        value = answer_data.get("value", "")
                    elif isinstance(answer_data, str):
                        # 直接是字符串
                        value = answer_data
                    else:
                        # 其他格式，尝试转换为字符串
                        value = str(answer_data) if answer_data else ""
                    
                    if value and isinstance(value, str) and value.strip():
                        open_ended_responses.append(value.strip())
        
        return open_ended_responses
    
    def _generate_visualizations(
        self,
        open_ended_responses: List[str],
        analysis_report: SurveyAnalysisReport,
        survey_title: str
    ) -> Dict[str, str]:
        """
        生成可视化图表
        
        Args:
            open_ended_responses: 开放题回答列表
            analysis_report: 分析报告
            survey_title: 问卷标题
            
        Returns:
            可视化图表字典 (key: 图表类型, value: base64图片)
        """
        visualizations = {}
        
        try:
            # 检查可视化库是否可用
            viz_availability = self.viz_service.check_availability()
            if not viz_availability.get("wordcloud") and not viz_availability.get("charts"):
                logger.warning("可视化库不可用，跳过图表生成")
                return visualizations
            
            # 1. 生成词云图
            if viz_availability.get("wordcloud") and len(open_ended_responses) >= 3:
                logger.info(f"正在生成词云图，文本数量: {len(open_ended_responses)}")
                wordcloud = self.viz_service.generate_wordcloud(
                    open_ended_responses,
                    title=f"{survey_title} - 主题词云"
                )
                if wordcloud:
                    visualizations["wordcloud"] = wordcloud
                    logger.info("✓ 词云图生成成功")
                else:
                    logger.warning("✗ 词云图生成失败（返回空字符串）")
            else:
                logger.info(f"跳过词云图生成 (可用性:{viz_availability.get('wordcloud')}, 文本数:{len(open_ended_responses)})")
            
            # 2. 生成主题分布图
            if viz_availability.get("charts") and len(analysis_report.themes) > 0:
                themes_data = [
                    {
                        "theme": t.theme,
                        "count": t.count,
                        "sentiment": t.sentiment.value
                    }
                    for t in analysis_report.themes
                ]
                logger.info(f"正在生成主题分布图，主题数量: {len(themes_data)}")
                theme_chart = self.viz_service.generate_theme_distribution_chart(
                    themes_data,
                    title="主题提及频次分布"
                )
                if theme_chart:
                    visualizations["theme_distribution"] = theme_chart
                    logger.info("✓ 主题分布图生成成功")
                else:
                    logger.warning("✗ 主题分布图生成失败（返回空字符串）")
                
                # 3. 生成情感分布饼图
                logger.info("正在生成情感分布图...")
                sentiment_pie = self.viz_service.generate_sentiment_pie_chart(
                    themes_data,
                    title="主题情感分布"
                )
                if sentiment_pie:
                    visualizations["sentiment_distribution"] = sentiment_pie
                    logger.info("✓ 情感分布图生成成功")
                else:
                    logger.warning("✗ 情感分布图生成失败（返回空字符串）")
            else:
                logger.info(f"跳过主题图表生成 (可用性:{viz_availability.get('charts')}, 主题数:{len(analysis_report.themes)})")
            
            logger.info(f"可视化生成完成，成功生成 {len(visualizations)} 个图表")
            
        except Exception as e:
            logger.error(f"生成可视化图表时出错: {e}", exc_info=True)
        
        return visualizations

