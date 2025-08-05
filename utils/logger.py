import logging
import os
import sys
import json
import platform
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from typing import Dict, Any, Optional

# 检查操作系统类型，为Windows设置彩色支持
is_windows = platform.system() == "Windows"
if is_windows:
    try:
        # 在Windows上启用ANSI颜色支持
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        ENABLE_COLORS = True
    except:
        ENABLE_COLORS = False
else:
    ENABLE_COLORS = True  # 在非Windows系统上默认启用

# 终端颜色代码
COLORS = {
    'RESET': '\033[0m',
    'BLACK': '\033[30m',
    'RED': '\033[31m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'BLUE': '\033[34m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
    'BOLD': '\033[1m',
    'UNDERLINE': '\033[4m',
    'BG_RED': '\033[41m',
    'BG_GREEN': '\033[42m',
    'BG_YELLOW': '\033[43m',
    'BG_BLUE': '\033[44m'
}

# 日志级别对应的颜色
LEVEL_COLORS = {
    'DEBUG': COLORS['BLUE'],
    'INFO': COLORS['GREEN'],
    'WARNING': COLORS['YELLOW'] + COLORS['BOLD'],
    'ERROR': COLORS['RED'],
    'CRITICAL': COLORS['BG_RED'] + COLORS['WHITE'] + COLORS['BOLD']
}

class CustomJsonFormatter(logging.Formatter):
    """结构化JSON格式日志记录器"""
    
    def __init__(self):
        super(CustomJsonFormatter, self).__init__()
    
    def format(self, record) -> str:
        """将日志记录格式化为JSON"""
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加异常信息
        if record.exc_info:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        # 添加自定义属性
        if hasattr(record, "extra_data"):
            log_obj["extra_data"] = record.extra_data
        
        return json.dumps(log_obj, ensure_ascii=False)

class ColoredTextFormatter(logging.Formatter):
    """增强版彩色文本格式化器"""
    
    def __init__(self, colored=True):
        """
        初始化格式化器
        
        Args:
            colored: 是否使用颜色（终端输出时使用）
        """
        super(ColoredTextFormatter, self).__init__(
            fmt="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.colored = colored and ENABLE_COLORS
    
    def format(self, record) -> str:
        """格式化日志记录"""
        # 保存原始的levelname
        original_levelname = record.levelname
        
        # 应用颜色
        if self.colored and record.levelname in LEVEL_COLORS:
            record.levelname = f"{LEVEL_COLORS[record.levelname]}{record.levelname.ljust(8)}{COLORS['RESET']}"
        else:
            record.levelname = record.levelname.ljust(8)
        
        # 格式化记录
        message = super(ColoredTextFormatter, self).format(record)
        
        # 恢复原始levelname
        record.levelname = original_levelname
        
        # 添加调用信息
        if record.levelno >= logging.WARNING:
            source_info = f" [{record.module}:{record.lineno}]"
            message = f"{message}{source_info}"
        
        # 添加异常信息
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            if self.colored:
                exception_text = f"{COLORS['RED']}{exception_text}{COLORS['RESET']}"
            message = f"{message}\n{exception_text}"
        
        return message

def setup_logger(
    name: str, 
    log_dir: str = "logs", 
    level: int = logging.INFO, 
    log_to_console: bool = True,
    max_bytes: int = 10*1024*1024,  # 10MB
    backup_count: int = 10,
    log_format: str = "text"  # 可选 'text' 或 'json'
) -> logging.Logger:
    """
    设置高级日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志存储目录
        level: 日志级别
        log_to_console: 是否输出到控制台
        max_bytes: 单个日志文件最大大小
        backup_count: 保留的备份文件数量
        log_format: 日志格式，支持'text'或'json'
        
    Returns:
        配置好的日志记录器实例
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 防止重复添加处理器
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    # 创建一个按大小滚动的文件处理器
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, f"{name}.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    
    # 创建日期滚动的处理器，按天滚动
    daily_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, f"{name}_daily.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    
    # 选择格式化器 - 文件使用无颜色格式
    if log_format.lower() == "json":
        file_formatter = CustomJsonFormatter()
    else:
        file_formatter = ColoredTextFormatter(colored=False)
    
    # 设置格式化器
    file_handler.setFormatter(file_formatter)
    daily_handler.setFormatter(file_formatter)
    
    # 添加文件处理器
    logger.addHandler(file_handler)
    logger.addHandler(daily_handler)
    
    # 创建控制台处理器 - 控制台使用彩色格式
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredTextFormatter(colored=True))
        logger.addHandler(console_handler)
    
    return logger

# 从环境变量读取日志级别
import os
env_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if env_log_level == "DEBUG":
    default_level = logging.DEBUG
elif env_log_level == "INFO":
    default_level = logging.INFO
elif env_log_level == "WARNING":
    default_level = logging.WARNING
elif env_log_level == "ERROR":
    default_level = logging.ERROR
elif env_log_level == "CRITICAL":
    default_level = logging.CRITICAL
else:
    default_level = logging.INFO

# 创建应用日志记录器
app_logger = setup_logger("dingtalk_dify_adapter", level=default_level)

# 创建钉钉API日志记录器
dingtalk_logger = setup_logger("dingtalk_api", level=default_level)

# 创建Dify API日志记录器
dify_logger = setup_logger("dify_api", level=default_level)

def log_request(logger: logging.Logger, method: str, url: str, 
                headers: Optional[Dict[str, Any]] = None, 
                data: Optional[Dict[str, Any]] = None, 
                params: Optional[Dict[str, Any]] = None) -> None:
    """
    记录API请求信息
    
    Args:
        logger: 日志记录器
        method: HTTP方法
        url: 请求URL
        headers: 请求头
        data: 请求数据
        params: 查询参数
    """
    extra = {
        "method": method,
        "url": url,
    }
    
    if headers:
        # 移除敏感信息
        safe_headers = headers.copy()
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = "Bearer ***"
        extra["headers"] = safe_headers
        
    if data:
        extra["data"] = data
        
    if params:
        extra["params"] = params
    
    logger.debug(f"API请求: {method} {url}", extra={"extra_data": extra})

def log_response(logger: logging.Logger, response, elapsed_time: Optional[float] = None) -> None:
    """
    记录API响应信息
    
    Args:
        logger: 日志记录器
        response: HTTP响应对象
        elapsed_time: 请求耗时(秒)
    """
    status_code = response.status_code
    extra = {
        "status_code": status_code,
    }
    
    # 根据状态码决定日志级别
    log_level = logging.DEBUG
    if status_code >= 400 and status_code < 500:
        log_level = logging.WARNING
    elif status_code >= 500:
        log_level = logging.ERROR
    
    if elapsed_time:
        extra["elapsed_time"] = f"{elapsed_time:.3f}s"
        msg_suffix = f" ({elapsed_time:.3f}s)"
    else:
        msg_suffix = ""
    
    try:
        if response.headers.get("Content-Type", "").startswith("application/json"):
            resp_json = response.json()
            extra["response"] = resp_json
            # 检查API错误
            if "code" in resp_json and "message" in resp_json and status_code != 200:
                logger.log(log_level, f"API错误: [{status_code}] {resp_json.get('message')}{msg_suffix}", 
                        extra={"extra_data": extra})
                return
        else:
            extra["response_length"] = len(response.text)
    except Exception:
        extra["response_text"] = response.text[:200] + "..." if len(response.text) > 200 else response.text
    
    # 正常响应使用DEBUG级别，错误响应使用WARNING或ERROR级别
    logger.log(log_level, f"API响应: {status_code}{msg_suffix}", extra={"extra_data": extra}) 