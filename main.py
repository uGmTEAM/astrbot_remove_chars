"""
插件名称: RemoveChars
功能: 移除 bot 输出消息中的指定字符
版本: 1.0.0
"""

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain

@register("remove_chars", "YourName", "移除 bot 输出中的特定字符", "1.0.0")
class RemoveCharsPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        
        self.config = config or {}
        
        # 获取 chars_to_remove
        chars_raw = self.config.get("chars_to_remove", "*#@")
        if isinstance(chars_raw, str):
            if "," in chars_raw:
                self.chars_to_remove = [c.strip() for c in chars_raw.split(",") if c.strip()]
            else:
                self.chars_to_remove = list(chars_raw)
        elif isinstance(chars_raw, list):
            self.chars_to_remove = chars_raw
        else:
            self.chars_to_remove = ["*", "#", "@"]
        
        # 获取布尔值配置
        self.remove_spaces = self.config.get("remove_spaces", False)
        self.only_prefix = self.config.get("only_prefix", False)
        self.only_suffix = self.config.get("only_suffix", False)
        
        logger.info(f"RemoveChars 插件已加载")
        logger.info(f"  移除字符: {self.chars_to_remove}")
        logger.info(f"  移除空格: {self.remove_spaces}")
        logger.info(f"  仅前缀: {self.only_prefix}")
        logger.info(f"  仅后缀: {self.only_suffix}")

    def _extract_text_from_response(self, response) -> str:
        """从响应中提取文本内容"""
        if isinstance(response, str):
            return response
        
        # 尝试从 result_chain 中提取
        if hasattr(response, 'result_chain'):
            chain = response.result_chain
            if hasattr(chain, 'chain'):
                text_parts = []
                for item in chain.chain:
                    if hasattr(item, 'text'):
                        text_parts.append(item.text)
                return ''.join(text_parts)
        
        # 尝试直接获取属性
        if hasattr(response, 'text'):
            return response.text
        
        if hasattr(response, 'content'):
            return response.content
        
        return str(response)

    def _update_response_text(self, response, new_text: str) -> bool:
        """更新响应对象中的文本内容，保持对象结构完整"""
        try:
            # 方法1：更新 result_chain 中的文本
            if hasattr(response, 'result_chain') and hasattr(response.result_chain, 'chain'):
                chain_list = response.result_chain.chain
                # 找到所有 Plain 组件并更新它们的 text
                for item in chain_list:
                    if hasattr(item, 'text'):
                        item.text = new_text
                logger.info(f"已更新 result_chain 中的文本")
                return True
            
            # 方法2：直接设置 text 属性
            if hasattr(response, 'text'):
                response.text = new_text
                logger.info(f"已更新 text 属性")
                return True
            
            # 方法3：设置 content 属性
            if hasattr(response, 'content'):
                response.content = new_text
                logger.info(f"已更新 content 属性")
                return True
            
            return False
        except Exception as e:
            logger.error(f"更新响应文本失败: {e}")
            return False

    def _remove_chars_from_text(self, text: str) -> str:
        """从文本中移除指定字符"""
        if not text:
            return text
        
        modified = text
        
        # 移除空格
        if self.remove_spaces:
            if self.only_prefix:
                modified = modified.lstrip()
            elif self.only_suffix:
                modified = modified.rstrip()
            else:
                modified = modified.replace(" ", "")
        
        # 移除指定字符
        for char in self.chars_to_remove:
            if not char:
                continue
            if self.only_prefix:
                while modified.startswith(char):
                    modified = modified[len(char):]
            elif self.only_suffix:
                while modified.endswith(char):
                    modified = modified[:-len(char)]
            else:
                modified = modified.replace(char, "")
        
        return modified

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, response) -> MessageEventResult:
        """处理 LLM 响应，移除指定字符"""
        # 提取文本内容
        text_content = self._extract_text_from_response(response)
        
        if not text_content:
            return event.get_result()
        
        # 移除指定字符
        modified_text = self._remove_chars_from_text(text_content)
        
        # 如果内容有变化，直接修改 response 对象内部的文本（不替换对象）
        if modified_text != text_content:
            success = self._update_response_text(response, modified_text)
            if success:
                logger.info(f"已移除指定字符，原长度: {len(text_content)}，新长度: {len(modified_text)}")
            else:
                # 如果无法修改对象内部，尝试通过 event 设置（可能导致错误）
                logger.warning("无法修改 response 对象内部，尝试使用 event.set_result")
                # 不调用 event.set_result，避免破坏对象结构
        
        return event.get_result()