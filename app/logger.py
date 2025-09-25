import logging
from typing import Optional


class BotLogger:
    def __init__(self, name: str = "TelegramBot"):
        self.logger = logging.getLogger(name)

    def user_action(self, user_id: int, action: str, details: str = ""):
        """Log user actions"""
        self.logger.info(f"👤 USER {user_id} - {action} - {details}")

    def job_scheduled(self, user_id: int, job_name: str, execution_time: str, details: str = ""):
        """Log job scheduling"""
        self.logger.info(f"⏰ JOB SCHEDULED - User {user_id} - {job_name} at {execution_time} - {details}")

    def job_executed(self, user_id: int, job_name: str, status: str = "completed"):
        """Log job execution"""
        self.logger.info(f"⚡ JOB {status.upper()} - User {user_id} - {job_name}")

    def message_sent(self, user_id: int, message_type: str, details: str = ""):
        """Log message sending"""
        self.logger.info(f"📨 MESSAGE SENT - User {user_id} - {message_type} - {details}")

    def error(self, user_id: Optional[int], context: str, error: Exception):
        """Log errors"""
        user_info = f"User {user_id} - " if user_id else ""
        self.logger.error(f"❌ ERROR - {user_info}{context}: {error}")

    def warning(self, user_id: Optional[int], context: str, details: str = ""):
        """Log warnings"""
        user_info = f"User {user_id} - " if user_id else ""
        self.logger.warning(f"⚠️ WARNING - {user_info}{context} - {details}")

    def debug(self, message: str):
        """Debug messages"""
        self.logger.debug(f"🔍 DEBUG - {message}")

    def info(self, user_id: Optional[int], context: str, details: str = ""):
        """Generic info logging"""
        user_info = f"User {user_id} - " if user_id else ""
        self.logger.info(f"📣 INFO - {user_info}{context} - {details}")

    def database_operation(self, user_id: int, operation: str, details: str = ""):
        """Log database operations"""
        self.logger.info(f"💾 DATABASE - User {user_id} - {operation} - {details}")

    def info(self, info : str):
        self.logger.info(info)

bot_logger = BotLogger()
