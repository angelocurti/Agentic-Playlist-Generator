from langchain_core.messages import SystemMessage, HumanMessage
from src.state import State
from src.models import llm_search
from src.prompt import FIRST_SEARCH_PROMPT

def input_handler(state: State) -> dict:
    """Gestisce l'input e fa una prima ricerca online"""
    last_msg = state.get("messages", [])[-1]

    if not last_msg:
        return {"messages": [], "error": "No message"}
    else:        
        user_msg_content = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)

        messages = [
            SystemMessage(content=FIRST_SEARCH_PROMPT),
            HumanMessage(content=user_msg_content)
        ]

        first_search = llm_search.invoke(messages)
        result = first_search.content
        print(f"Search Result: {result}")
        # If messages is List[AnyMessage], returning a string 'result' might be handled by 'add_messages' reducer if it accepts strings (it usually converts to AIMessage).
        return {"messages": [result], "playlist_context": result}