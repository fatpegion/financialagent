"""
DeepSeek V4 兼容的 ChatOpenAI 包装类

DeepSeek V4 模型启用了 thinking mode，返回的 response 中包含 ``reasoning_content`` 字段。
在多轮对话中（如 ReAct agent tool calling），该字段必须被回传给 API，否则会报错：
"reasoning_content in the thinking mode must be passed back to the API"

LangChain 的 ``_convert_dict_to_message`` 不会将 ``reasoning_content`` 保存到 AIMessage 中，
因此本模块在两个环节拦截：

1. **响应解析**：将 API 响应中的 ``reasoning_content`` 保存到 AIMessage.additional_kwargs
2. **请求构建**：将 AIMessage.additional_kwargs 中的 ``reasoning_content`` 回注到消息 dict
"""
import logging
from typing import Any, Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.outputs import ChatResult

logger = logging.getLogger(__name__)


class DeepSeekChatOpenAI(ChatOpenAI):
    """
    ChatOpenAI 子类，确保 DeepSeek V4 的 reasoning_content 在 ReAct 多轮对话中正确往返。
    """

    def _create_chat_result(
        self,
        response: Union[dict, Any],
        generation_info: Optional[dict] = None,
    ) -> ChatResult:
        """重写以将 API 响应中的 reasoning_content 保留到 AIMessage.additional_kwargs 中"""
        result = super()._create_chat_result(response, generation_info)

        response_dict = response if isinstance(response, dict) else response.model_dump()
        choices = response_dict.get("choices", [])

        for i, gen in enumerate(result.generations):
            if isinstance(gen.message, AIMessage) and i < len(choices):
                msg_data = choices[i].get("message", {})
                reasoning = msg_data.get("reasoning_content")
                if reasoning:
                    gen.message.additional_kwargs["reasoning_content"] = reasoning
                    logger.debug(f"Preserved reasoning_content len={len(reasoning)} in generation {i}")

        return result

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> dict:
        """重写以将 AIMessage.additional_kwargs 中的 reasoning_content 注入到请求的消息 dict 中"""
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        messages = self._convert_input(input_).to_messages()

        if "messages" in payload:
            payload_msgs = payload["messages"]
            for i in range(min(len(messages), len(payload_msgs))):
                msg = messages[i]
                pmsg = payload_msgs[i]

                if isinstance(msg, AIMessage):
                    reasoning = msg.additional_kwargs.get("reasoning_content")
                    if reasoning:
                        pmsg["reasoning_content"] = reasoning
                        logger.debug(f"Injected reasoning_content len={len(reasoning)} into message {i}")
                    elif pmsg.get("role") == "assistant":
                        if "reasoning_content" not in pmsg:
                            pmsg["reasoning_content"] = ""
                            logger.debug(f"Added empty reasoning_content to assistant message {i}")

        return payload
