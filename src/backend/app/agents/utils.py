from datetime import date

from langchain_core.messages import SystemMessage, ToolMessage

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


def current_date_message() -> SystemMessage:
    """SystemMessage stating today's date, built fresh on every invocation.

    Static context belongs in the prompt, not behind a tool call: this costs
    no round-trip and is always present for date-sensitive research.
    """
    today = date.today()
    return SystemMessage(
        content=f"Today is {today.strftime('%A, %B %d, %Y')} ({today.isoformat()})."
    )