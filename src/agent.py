from __future__ import annotations
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
from src.state import State
from src.nodes.input_handler import input_handler
from src.nodes.online_search import online_search
from src.nodes.playlist_generation import playlist_generation
from src.nodes.output import output_node

load_dotenv()

# =========================
# AGENT CACHING (OTTIMIZZAZIONE)
# =========================
_cached_graph = None
_cached_memory = None

def _build_graph():
    """Costruisce il grafo LangGraph (chiamato una sola volta)"""
    graph = StateGraph(State)

    # Nodes
    graph.add_node("input_handler", input_handler)
    graph.add_node("online_search", online_search)
    graph.add_node("playlist_generation", playlist_generation)
    graph.add_node("output", output_node)

    # Edges
    graph.add_edge(START, "input_handler")
    graph.add_edge("input_handler", "online_search")
    graph.add_edge("online_search", "playlist_generation")
    graph.add_edge("playlist_generation", "output")
    graph.add_edge("output", END)
    
    return graph

def get_cached_agent():
    """
    Restituisce un agent compilato cached.
    Il grafo viene costruito una sola volta e riutilizzato.
    Ogni chiamata usa un nuovo checkpointer per isolamento.
    """
    global _cached_graph
    
    # Costruisci il grafo solo la prima volta
    if _cached_graph is None:
        print("[Agent] Building graph for the first time...")
        _cached_graph = _build_graph()
    
    # Ogni invocazione usa un nuovo InMemorySaver per isolamento
    memory = InMemorySaver()
    return _cached_graph.compile(checkpointer=memory)

def build_agent():
    """
    Legacy function per compatibilità.
    Usa get_cached_agent() per performance migliori.
    """
    return get_cached_agent()
