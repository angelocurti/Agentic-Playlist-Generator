from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
from langgraph.graph.message import AnyMessage

class State(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    user_request: Optional[str]
    generated_playlist: List[Dict[str,str]]
    error : Optional[str]
    playlist_context: str
    spotify_token: Optional[str]
