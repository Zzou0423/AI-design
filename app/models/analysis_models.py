"""
问卷分析数据模型
使用 Pydantic 定义数据结构，确保类型安全和数据验证
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class Sentiment(str, Enum):
    """情感倾向枚举"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Theme(BaseModel):
    """主题编码模型"""
    theme: str = Field(..., description="主题名称，简短短语")
    sentiment: Sentiment = Field(..., description="情感倾向")
    quote: str = Field(..., description="代表性用户原话引述")
    count: int = Field(..., ge=0, description="提及频次（相对）")
    description: Optional[str] = Field(None, description="主题详细描述")


class SurveyAnalysisReport(BaseModel):
    """问卷定性分析报告（仅开放题）"""
    summary: str = Field(..., description="总体摘要，概括所有反馈的核心内容")
    themes: List[Theme] = Field(..., description="识别出的核心主题列表")
    recommendation: str = Field(..., description="基于分析结果的具体行动建议")
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "就业满意度调研显示，员工在团队氛围和培训机会方面较为满意，但在工作强度和薪酬待遇方面存在明显不满。",
                "themes": [
                    {
                        "theme": "工作时间过长",
                        "sentiment": "negative",
                        "quote": "工作时间太长了，经常需要加班到很晚",
                        "count": 8,
                        "description": "员工普遍反映工作时间过长，加班频繁"
                    },
                    {
                        "theme": "团队氛围良好",
                        "sentiment": "positive",
                        "quote": "团队氛围很好，同事之间互相帮助",
                        "count": 6,
                        "description": "员工对团队协作和同事关系评价积极"
                    }
                ],
                "recommendation": "建议：1) 优化工作流程，减少不必要的加班；2) 调整薪酬体系，提升竞争力；3) 继续保持良好的团队文化，同时加强管理层沟通培训。"
            }
        }


# ========== 全量分析模型 ==========

class QuestionResult(BaseModel):
    """每个问题的统计结果"""
    question_title: str = Field(..., description="问题标题")
    question_type: str = Field(..., description="问题类型：单选题/多选题/量表题/开放式问题")
    response_count: int = Field(..., description="回答数量")
    result_summary: Dict[str, Any] = Field(..., description="统计摘要（灵活字段）")


class FullAnalysisDataReport(BaseModel):
    """全量分析的数据输入结构"""
    survey_title: str = Field(..., description="问卷标题")
    survey_description: Optional[str] = Field(None, description="问卷描述")
    total_respondents: int = Field(..., description="总回答人数")
    question_results: List[QuestionResult] = Field(..., description="所有问题的统计结果")


class FullAnalysisReport(BaseModel):
    """全量分析报告（Markdown格式）"""
    report_markdown: str = Field(..., description="完整的Markdown格式分析报告")

