"""
用户数据模型
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class User:
    """用户模型"""
    
    def __init__(self, username: str, password_hash: str, email: Optional[str] = None):
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.created_at = datetime.now().isoformat()
        self.last_login = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "username": self.username,
            "password_hash": self.password_hash,
            "email": self.email,
            "created_at": self.created_at,
            "last_login": self.last_login
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'User':
        """从字典创建用户"""
        user = User(
            username=data["username"],
            password_hash=data["password_hash"],
            email=data.get("email")
        )
        user.created_at = data.get("created_at", datetime.now().isoformat())
        user.last_login = data.get("last_login")
        return user
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return self.password_hash == User.hash_password(password)


class UserStore:
    """用户存储管理"""
    
    def __init__(self, db_path: str = "./data/users.json"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._users = {}
        self.load()
    
    def load(self):
        """从文件加载用户数据"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    for username, data in users_data.items():
                        self._users[username] = User.from_dict(data)
            except Exception as e:
                print(f"加载用户数据失败: {e}")
                self._users = {}
        else:
            self._users = {}
    
    def save(self):
        """保存用户数据到文件"""
        try:
            users_data = {
                username: user.to_dict() 
                for username, user in self._users.items()
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存用户数据失败: {e}")
    
    def register(self, username: str, password: str, email: Optional[str] = None) -> bool:
        """注册用户"""
        if username in self._users:
            return False
        
        password_hash = User.hash_password(password)
        user = User(username, password_hash, email)
        self._users[username] = user
        self.save()
        return True
    
    def login(self, username: str, password: str) -> Optional[User]:
        """用户登录"""
        if username not in self._users:
            return None
        
        user = self._users[username]
        if user.verify_password(password):
            user.last_login = datetime.now().isoformat()
            self.save()
            return user
        
        return None
    
    def get_user(self, username: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(username)
    
    def user_exists(self, username: str) -> bool:
        """检查用户是否存在"""
        return username in self._users


# 全局用户存储实例
user_store = UserStore()

