from langchain_core.messages import ToolMessage

def sanitize_messages_for_llm(messages):
    """
    Auxiliary function for removing file/resource blocks from ToolMessages before 
    sending them to OpenAI Chat Completions.

    This fixes the error "OpenAI Chat Completions does not support file URLs." that 
    occured passing the trvl tool's response to the LLM.

    The original messages remain unchanged in LangGraph state.
    """

    sanitized = []

    for message in messages:

        if isinstance(message, ToolMessage) and isinstance(message.content, list):

            text_blocks = []

            for block in message.content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "text"
                    and "text" in block
                ):
                    text_blocks.append(block["text"])

            if text_blocks:
                sanitized.append(
                    ToolMessage(
                        content="\n".join(text_blocks),
                        tool_call_id=message.tool_call_id,
                        name=message.name,
                    )
                )

            else:
                sanitized.append(message)

        else:
            sanitized.append(message)

    return sanitized