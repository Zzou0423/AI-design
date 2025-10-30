"""
会话管理工具
"""

import secrets
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path


class SessionManager:
    """会话管理器"""
    
    def __init__(self, expire_hours: int = 24 * 7):  # 默认7天过期
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.expire_hours = expire_hours
        self.sessions_file = Path("data/sessions.json")
        self.sessions_file.parent.mkdir(exist_ok=True)
        
        # 启动时加载持久化的会话
        self._load_sessions()
    
    def _load_sessions(self):
        """从文件加载会话"""
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 转换时间字符串为datetime对象
                    for session_id, session_data in data.items():
                        session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                        session_data['last_access'] = datetime.fromisoformat(session_data['last_access'])
                        self.sessions[session_id] = session_data
                print(f"加载了 {len(self.sessions)} 个持久化会话")
            except Exception as e:
                print(f"加载会话文件失败: {e}")
                self.sessions = {}
    
    def _save_sessions(self):
        """保存会话到文件"""
        try:
            # 转换datetime对象为字符串
            data = {}
            for session_id, session_data in self.sessions.items():
                data[session_id] = {
                    'username': session_data['username'],
                    'created_at': session_data['created_at'].isoformat(),
                    'last_access': session_data['last_access'].isoformat()
                }
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存会话文件失败: {e}")
    
    def create_session(self, username: str) -> str:
        """创建会话"""
        session_id = secrets.token_urlsafe(32)
        
        self.sessions[session_id] = {
            "username": username,
            "created_at": datetime.now(),
            "last_access": datetime.now()
        }
        
        # 保存到文件
        self._save_sessions()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # 检查是否过期
        if datetime.now() - session["last_access"] > timedelta(hours=self.expire_hours):
            del self.sessions[session_id]
            return None
        
        # 更新最后访问时间
        session["last_access"] = datetime.now()
        
        # 定期保存（每10次访问保存一次，避免频繁IO）
        if not hasattr(self, '_access_count'):
            self._access_count = 0
        self._access_count += 1
        if self._access_count % 10 == 0:
            self._save_sessions()
        
        return session
    
    def delete_session(self, session_id: str):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            # 保存到文件
            self._save_sessions()
    
    def get_username(self, session_id: str) -> Optional[str]:
        """获取会话对应的用户名"""
        session = self.get_session(session_id)
        if session:
            return session["username"]
        return None
    
    def cleanup_expired(self):
        """清理过期会话"""
        now = datetime.now()
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if now - session["last_access"] > timedelta(hours=self.expire_hours)
        ]
        for sid in expired_sessions:
            del self.sessions[sid]
        
        # 如果有过期会话被删除，保存到文件
        if expired_sessions:
            self._save_sessions()


# 全局会话管理器实例
session_manager = SessionManager()

