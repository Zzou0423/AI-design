"""
自动生成问卷并填充答案的脚本

功能：
1. 使用AI问卷生成功能自动创建20份不同主题的问卷
2. 主题随机覆盖各类有趣的问题
3. 生成的问卷保存到data/surveys目录
4. 自动调用答案生成脚本为每份问卷填充答案
5. 支持自定义生成数量和并发数
"""

import os
import json
import uuid
import time
import random
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 确保导入路径正确
sys_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.append(sys_path)

# 导入问卷生成服务
from app.services.survey_service import SurveyService


class AutoSurveyGenerator:
    """自动问卷生成器"""
    
    def __init__(self):
        """初始化自动问卷生成器"""
        # 创建问卷服务实例
        self.survey_service = SurveyService(
            llm_model="qwen-flash",  # 使用更快的模型
            temperature=0.8,         # 稍高温度增加多样性
            retrieval_k=3
        )
        
        # 问卷保存目录
        self.surveys_dir = Path("data/surveys")
        self.surveys_dir.mkdir(parents=True, exist_ok=True)
        
        # 答案生成脚本路径
        self.response_script_path = Path("scripts/generate_responses_random_scale.py")
        
        # 有趣的问卷主题列表
        self.interesting_topics = [
            # 生活方式
            "现代人的睡眠质量与影响因素调查",
            "年轻人的饮食习惯与健康认知调研",
            "社交媒体使用习惯与心理健康关系",
            "城市居民通勤方式选择与满意度",
            "周末休闲活动偏好与消费习惯",
            
            # 科技与数字化
            "人工智能对未来工作的影响认知",
            "数字支付方式使用习惯与安全性感知",
            "在线学习平台使用体验与效果评估",
            "智能家居产品使用现状与期望",
            "元宇宙概念认知与接受度调查",
            
            # 社会与文化
            "公众对气候变化的认知与行动意愿",
            "传统文化传承与创新认知调研",
            "志愿服务参与意愿与动机调查",
            "公众阅读习惯变化与偏好",
            "宠物饲养现状与情感需求",
            
            # 消费与经济
            "年轻人的消费观念与储蓄习惯",
            "可持续消费理念认知与实践",
            "旅游消费偏好与体验评价",
            "品牌忠诚度影响因素调查",
            "在线购物决策因素与满意度"
        ]
    
    def generate_survey(self, topic: str) -> dict:
        """
        生成单个问卷
        
        Args:
            topic: 问卷主题
            
        Returns:
            问卷数据字典
        """
        print(f"\n[INFO] 生成问卷: {topic}")
        
        try:
            # 生成问卷
            survey = self.survey_service.create_survey(
                user_input=topic,
                additional_context={
                    "target_audience": "普通消费者",
                    "survey_purpose": "了解用户需求和偏好",
                    "question_count": 5  # 减少问题数量，加快生成速度
                }
            )
            
            # 添加问卷ID和基本信息
            survey["id"] = str(uuid.uuid4())
            survey["title"] = topic
            survey["description"] = f"关于{topic}的调查问卷"
            survey["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            return survey
            
        except Exception as e:
            print(f"[ERROR] 生成问卷失败: {e}")
            # 如果AI生成失败，使用本地模板生成简单问卷
            return self._generate_fallback_survey(topic)
    
    def _generate_fallback_survey(self, topic: str) -> dict:
        """
        生成备用问卷（当AI生成失败时）
        
        Args:
            topic: 问卷主题
            
        Returns:
            简单问卷数据字典
        """
        print(f"[INFO] 使用本地模板生成备用问卷")
        
        # 简单问卷模板
        questions = [
            {
                "id": str(uuid.uuid4()),
                "questionText": f"您对{topic}的整体关注度如何？",
                "questionType": "scale",
                "options": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "required": True,
                "scale": {
                    "min": 1,
                    "max": 10,
                    "minLabel": "非常不关注",
                    "maxLabel": "非常关注"
                }
            },
            {
                "id": str(uuid.uuid4()),
                "questionText": f"您认为{topic}对您的生活影响程度如何？",
                "questionType": "scale",
                "options": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "required": True,
                "scale": {
                    "min": 1,
                    "max": 10,
                    "minLabel": "几乎没有影响",
                    "maxLabel": "影响很大"
                }
            },
            {
                "id": str(uuid.uuid4()),
                "questionText": f"您更倾向于通过哪些渠道了解{topic}？（多选）",
                "questionType": "checkbox",
                "options": [
                    "社交媒体",
                    "朋友推荐",
                    "专业网站",
                    "线下活动",
                    "其他"
                ],
                "required": False
            },
            {
                "id": str(uuid.uuid4()),
                "questionText": f"您对{topic}的满意程度是？",
                "questionType": "single",
                "options": [
                    "非常满意",
                    "比较满意",
                    "一般",
                    "不太满意",
                    "非常不满意"
                ],
                "required": True
            }
        ]
        
        # 构建问卷结构
        survey = {
            "id": str(uuid.uuid4()),
            "title": topic,
            "description": f"关于{topic}的调查问卷",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "questions": questions,
            "settings": {
                "isAnonymous": True,
                "canSkip": True
            }
        }
        
        return survey
    
    def save_survey(self, survey: dict) -> Path:
        """
        保存问卷到文件
        
        Args:
            survey: 问卷数据字典
            
        Returns:
            保存的文件路径
        """
        # 生成文件名
        filename = f"{survey['title'].replace(' ', '_')}_{survey['id'][:8]}.json"
        filepath = self.surveys_dir / filename
        
        # 保存问卷
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(survey, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] 问卷已保存: {filepath}")
        return filepath
    
    def generate_responses(self, survey_filepath: Path, num_responses: int = 20):
        """
        为问卷生成答案
        
        Args:
            survey_filepath: 问卷文件路径
            num_responses: 生成的答案数量
        """
        print(f"\n[INFO] 为问卷生成 {num_responses} 份答案: {survey_filepath.name}")
        
        try:
            # 调用答案生成脚本
            command = [
                "python",
                str(self.response_script_path),
                "--survey-file", str(survey_filepath),
                "--num-responses", str(num_responses),
                "--mode", "random",  # 使用纯随机模式，不需要API Key
                "--batch-size", "10"
            ]
            
            # 执行命令
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode == 0:
                print(f"[OK] 答案生成完成: {survey_filepath.name}")
                # 输出部分结果
                output_lines = result.stdout.strip().split('\n')
                if len(output_lines) > 5:
                    print("\n".join(output_lines[-5:]))
            else:
                print(f"[ERROR] 答案生成失败: {survey_filepath.name}")
                print(f"错误信息: {result.stderr}")
                
        except Exception as e:
            print(f"[ERROR] 调用答案生成脚本失败: {e}")
    
    def generate_surveys(self, num_surveys: int = 20, num_responses_per_survey: int = 20):
        """
        自动生成多个问卷并填充答案
        
        Args:
            num_surveys: 生成的问卷数量
            num_responses_per_survey: 每份问卷的答案数量
        """
        print("=" * 80)
        print("🤖 自动问卷生成与答案填充工具")
        print("=" * 80)
        print(f"\n设置: 生成 {num_surveys} 份问卷，每份问卷 {num_responses_per_survey} 份答案")
        
        # 选择主题（如果请求数量大于可用主题，则重复选择）
        if num_surveys <= len(self.interesting_topics):
            selected_topics = random.sample(self.interesting_topics, num_surveys)
        else:
            selected_topics = random.choices(self.interesting_topics, k=num_surveys)
        
        print(f"\n已选择 {len(selected_topics)} 个主题")
        
        # 生成问卷并填充答案
        successful_surveys = 0
        for i, topic in enumerate(selected_topics, 1):
            print(f"\n{'=' * 80}")
            print(f"[{i}/{num_surveys}] 处理主题: {topic}")
            print(f"{'=' * 80}")
            
            # 生成问卷
            survey = self.generate_survey(topic)
            if not survey:
                print(f"[SKIP] 跳过该主题")
                continue
            
            # 保存问卷
            survey_filepath = self.save_survey(survey)
            
            # 生成答案
            self.generate_responses(survey_filepath, num_responses_per_survey)
            
            successful_surveys += 1
            
            # 添加延迟，避免API限流（如果使用AI模式）
            time.sleep(2)
        
        # 总结
        print(f"\n{'=' * 80}")
        print("生成完成!")
        print(f"{'=' * 80}")
        print(f"✓ 成功生成 {successful_surveys}/{num_surveys} 份问卷")
        print(f"✓ 每份问卷已生成 {num_responses_per_survey} 份答案")
        print(f"✓ 问卷保存位置: {self.surveys_dir}")
        print(f"✓ 答案保存位置: data/responses/ 目录下对应问卷文件夹")
        print(f"{'=' * 80}")


if __name__ == "__main__":
    # 检查API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n" + "=" * 80)
        print("[WARNING] DASHSCOPE_API_KEY 未配置")
        print("问卷生成将使用基础模式")
        print("要使用更智能的AI生成，配置DASHSCOPE_API_KEY")
        print("=" * 80)
    
    generator = AutoSurveyGenerator()
    generator.generate_surveys(num_surveys=20, num_responses_per_survey=20)