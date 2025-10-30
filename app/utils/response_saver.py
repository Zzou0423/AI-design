"""
问卷答案存储模块
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

def sanitize_filename(name: str, max_length: int = 50) -> str:
    """
    清理文件名，去掉特殊字符，使其适用于文件系统
    
    Args:
        name: 原始文件名
        max_length: 最大长度
        
    Returns:
        清理后的文件名
    """
    # 替换危险字符为下划线
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 去掉首尾空格和点
    sanitized = sanitized.strip('. ')
    # 限制长度
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized


class ResponseSaver:
    """问卷答案存储类"""
    
    def __init__(self, base_dir: str = "data/responses"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_response(self, survey_id: str, response_data: Dict[str, Any], user_id: str = None, survey_name: str = None) -> str:
        """
        保存问卷答案
        
        Args:
            survey_id: 问卷ID
            response_data: 答案数据
            user_id: 用户ID（可选，不提供则自动生成）
            survey_name: 问卷名称（用于文件夹命名）
            
        Returns:
            保存的文件路径
        """
        import uuid
        
        # 如果没有提供用户ID，生成一个UUID
        if user_id is None:
            user_id = str(uuid.uuid4())[:8]
        
        # 将用户ID添加到答案数据中
        response_data['user_id'] = user_id
        
        # 使用问卷名称创建文件夹（如果提供了）
        if survey_name:
            folder_name = sanitize_filename(survey_name)
            # 保留survey_id用于唯一性
            survey_dir = self.base_dir / f"{folder_name}_{survey_id}"
        else:
            survey_dir = self.base_dir / survey_id
        
        survey_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建文件名（时间戳 + 用户ID + 问卷ID）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 添加毫秒以区分同一秒内的多次提交
        filename = f"{timestamp}_{user_id}_{survey_id}.json"
        
        # 保存文件
        file_path = survey_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)
        
        return str(file_path)
    
    def get_responses(self, survey_id: str, survey_name: str = None) -> list:
        """
        获取某个问卷的所有答案
        
        Args:
            survey_id: 问卷ID
            survey_name: 问卷名称
            
        Returns:
            答案列表
        """
        # 尝试找到对应的文件夹
        if survey_name:
            folder_name = sanitize_filename(survey_name)
            survey_dir = self.base_dir / f"{folder_name}_{survey_id}"
        else:
            survey_dir = self.base_dir / survey_id
        
        if not survey_dir.exists():
            return []
        
        responses = []
        for file_path in survey_dir.glob("*.json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                responses.append(json.load(f))
        
        return responses
    
    def get_statistics(self, survey_id: str) -> Dict[str, Any]:
        """
        获取问卷统计数据
        
        Args:
            survey_id: 问卷ID
            
        Returns:
            统计数据
        """
        responses = self.get_responses(survey_id)
        
        if not responses:
            return {
                "total_responses": 0,
                "question_stats": {}
            }
        
        # 统计每个问题的答案
        question_stats = {}
        
        for response in responses:
            for question_id, answer in response.get("answers", {}).items():
                if question_id not in question_stats:
                    question_stats[question_id] = {
                        "type": answer.get("type"),
                        "answers": []
                    }
                question_stats[question_id]["answers"].append(answer.get("value"))
        
        # 计算统计数据
        stats = {}
        for qid, data in question_stats.items():
            answer_type = data.get("type")
            answers = data.get("answers", [])
            
            if answer_type in ["单选题", "多选题"]:
                # 统计选项选择次数
                counts = {}
                for ans in answers:
                    counts[ans] = counts.get(ans, 0) + 1
                stats[qid] = {"type": answer_type, "counts": counts}
            elif answer_type == "量表题":
                # 计算平均值和分布
                numeric_answers = [int(a) for a in answers if str(a).isdigit()]
                if numeric_answers:
                    stats[qid] = {
                        "type": answer_type,
                        "average": sum(numeric_answers) / len(numeric_answers),
                        "min": min(numeric_answers),
                        "max": max(numeric_answers),
                        "distribution": {str(i): numeric_answers.count(i) for i in range(1, 6)}
                    }
            elif answer_type == "开放式问题":
                # 返回所有答案
                stats[qid] = {"type": answer_type, "answers": answers}
        
        return {
            "total_responses": len(responses),
            "question_stats": stats
        }

