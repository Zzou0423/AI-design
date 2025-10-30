"""
用户问卷关联管理
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class UserSurveyManager:
    """用户问卷关联管理器"""
    
    def __init__(self, db_path: str = "./data/user_surveys.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {}
        self.load()
    
    def load(self):
        """加载数据"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"加载用户问卷数据失败: {e}")
                self._data = {}
        else:
            self._data = {}
    
    def save(self):
        """保存数据"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存用户问卷数据失败: {e}")
    
    def add_survey(self, username: str, survey_id: str, survey_title: str):
        """添加用户的问卷"""
        if username not in self._data:
            self._data[username] = []
        
        # 检查是否已存在
        existing = next((s for s in self._data[username] if s["survey_id"] == survey_id), None)
        if existing:
            return
        
        survey_info = {
            "survey_id": survey_id,
            "survey_title": survey_title,
            "created_at": datetime.now().isoformat(),
            "response_count": 0
        }
        
        self._data[username].append(survey_info)
        self.save()
    
    def get_user_surveys(self, username: str) -> List[Dict[str, Any]]:
        """获取用户的所有问卷"""
        if username not in self._data:
            return []
        
        surveys = self._data[username]
        
        # 更新每个问卷的回答数量
        for survey in surveys:
            survey_id = survey["survey_id"]
            survey["response_count"] = self._get_response_count(survey_id)
        
        return surveys
    
    def delete_survey(self, username: str, survey_id: str) -> bool:
        """删除用户的问卷"""
        if username not in self._data:
            return False
        
        original_length = len(self._data[username])
        self._data[username] = [
            s for s in self._data[username] 
            if s["survey_id"] != survey_id
        ]
        
        if len(self._data[username]) < original_length:
            self.save()
            return True
        return False
    
    def _get_response_count(self, survey_id: str) -> int:
        """获取问卷的回答数量"""
        responses_dir = Path("data/responses")
        if not responses_dir.exists():
            return 0
        
        # 查找包含该survey_id的目录
        for item in responses_dir.iterdir():
            if item.is_dir() and survey_id in item.name:
                json_files = list(item.glob("*.json"))
                return len(json_files)
        
        return 0
    
    def update_survey_title(self, username: str, survey_id: str, new_title: str):
        """更新问卷标题"""
        if username not in self._data:
            return
        
        for survey in self._data[username]:
            if survey["survey_id"] == survey_id:
                survey["survey_title"] = new_title
                break
        
        self.save()


# 全局实例
user_survey_manager = UserSurveyManager()

