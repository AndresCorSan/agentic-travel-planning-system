"""Small message helpers shared by nodes and subagents (sanitize, date line)."""
from datetime import date

from langchain_core.messages import SystemMessage, ToolMessage

def sanitize_messages_for_llm(messages):
    """
    Auxiliary function for removing file/resource blocks from ToolMessages before 
    sending them to OpenAI Chat Completions.

    This fixes the "OpenAI Chat Completions does not support file URLs"
    error from passing the trvl tool's response to the LLM. Only text
    blocks are kept; the original messages remain unchanged in LangGraph
    state.

    Args:
        messages: the message list about to be sent to the LLM.

    Returns:
        A new list with multi-modal ToolMessages reduced to plain text.
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


def current_date_message() -> SystemMessage:
    today = date.today()
    return SystemMessage(
        content=f"Today is {today.strftime('%A, %B %d, %Y')} ({today.isoformat()})."
    )