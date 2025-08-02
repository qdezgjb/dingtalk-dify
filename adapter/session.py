import time
import uuid
from typing import Dict, Any, Optional
from utils.logger import app_logger

class Session:
    def __init__(self, user_id: str, conversation_id: Optional[str] = None):
        self.user_id = user_id
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.last_activity = int(time.time())
        self.card_instance_id = None
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = int(time.time())
    
    def set_card_instance_id(self, card_instance_id: str):
        """设置卡片实例ID"""
        self.card_instance_id = card_instance_id
    
    def to_dict(self) -> Dict[str, Any]:
        """将会话转换为字典"""
        return {
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "last_activity": self.last_activity,
            "card_instance_id": self.card_instance_id
        }

class SessionManager:
    def __init__(self, session_timeout: int = 1800):  # 默认30分钟超时
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = session_timeout
        app_logger.info(f"会话管理器初始化，超时时间: {session_timeout}秒")
    
    def get_session(self, user_id: str) -> Session:
        """获取用户会话，如果不存在或已过期则创建新会话"""
        current_time = int(time.time())
        
        if user_id in self.sessions:
            session = self.sessions[user_id]
            if current_time - session.last_activity <= self.session_timeout:
                app_logger.debug(f"用户 {user_id} 使用现有会话 {session.conversation_id}")
                session.update_activity()
                return session
            else:
                app_logger.info(f"用户 {user_id} 的会话已过期，创建新会话")
        else:
            app_logger.info(f"用户 {user_id} 的会话不存在，创建新会话")
        
        # 创建新会话
        session = Session(user_id)
        self.sessions[user_id] = session
        app_logger.debug(f"为用户 {user_id} 创建新会话 {session.conversation_id}")
        return session
    
    def clear_expired_sessions(self):
        """清理过期会话"""
        current_time = int(time.time())
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if current_time - session.last_activity > self.session_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            app_logger.info(f"清理用户 {user_id} 的过期会话 {self.sessions[user_id].conversation_id}")
            del self.sessions[user_id]
        
        app_logger.debug(f"清理了 {len(expired_users)} 个过期会话，当前会话数量: {len(self.sessions)}")
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话信息"""
        return {
            user_id: session.to_dict() 
            for user_id, session in self.sessions.items()
        } 