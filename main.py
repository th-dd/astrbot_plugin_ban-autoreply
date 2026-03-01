from astrbot.api import star
from astrbot.api.event import filter, AstrMessageEvent
import logging

class BanAutoReplyPlugin(star.Star):
    """
    屏蔽自动回复插件
    
    功能：
    - 监听所有私聊及临时会话消息
    - 当消息内容以"[自动回复]"六个字开头时，静默终止事件传播
    - 防止LLM和其他插件对这类消息进行响应处理
    - 仅在满足条件时调用 event.stop_event()，不发送任何回复
    
    设计说明：
    本插件通过监听 PRIVATE_MESSAGE 类型事件覆盖私聊和临时会话场景。
    根据OneBot v11协议，临时会话属于私聊的一种子类型（sub_type=temp），
    因此使用私聊监听器即可捕获。结合 raw_message 中的 sub_type 字段可进一步确认。
    """
    
    def __init__(self, context: star.Context) -> None:
        """
        插件初始化方法
        
        Args:
            context (star.Context): AstrBot运行时上下文，提供配置、管理器等核心组件访问能力
        """
        self.context = context
        # 获取日志记录器，用于输出调试信息
        self.logger = logging.getLogger(__name__)
        
    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE, priority=10)
    async def on_private_message(self, event: AstrMessageEvent):
        """
        私聊消息处理器
        
        此方法监听所有私聊类型的消息事件（包括临时会话），检查消息内容是否以
        "[自动回复]"开头，若是则立即终止事件传播，防止后续处理。
        
        Args:
            event (AstrMessageEvent): 消息事件对象，包含完整的上下文信息
            
        Event Flow:
            1. 接收私聊消息事件
            2. 提取纯文本内容并判断是否以"[自动回复]"开头
            3. 若匹配成功且为私聊/临时会话，则调用 stop_event()
            4. 终止后其他插件和LLM将不会收到该事件
        """
        try:
            # 获取消息的纯文本内容（所有文本段拼接）
            message_text = event.message_str.strip()
            
            # 判断是否为空消息
            if not message_text:
                return
                
            # 检查消息是否以"[自动回复]"开头
            if message_text.startswith("[自动回复]"):
                # 可选：添加临时会话的精确判断（基于OneBot原始数据）
                is_temp_session = False
                if hasattr(event, 'raw_message') and event.raw_message:
                    # OneBot v11 协议中，私聊消息的 sub_type="temp" 表示临时会话
                    sub_type = event.raw_message.get('sub_type')
                    if sub_type == 'temp':
                        is_temp_session = True
                
                # 记录拦截日志（调试用途）
                session_desc = "临时会话" if is_temp_session else "私聊"
                self.logger.info(
                    f"已拦截来自用户 {event.get_sender_id()} 的{session_desc}消息: {message_text}"
                )
                
                # 终止事件传播 —— 这是关键操作
                # 调用后，后续的所有插件、LLM处理器、默认回复逻辑都不会被执行
                event.stop_event()
                
        except Exception as e:
            # 安全的错误处理，避免插件异常导致整个系统中断
            self.logger.error(f"处理私聊消息时发生异常: {str(e)}", exc_info=True)
