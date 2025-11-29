from src.state import State

def output_node(state: State) -> dict:
    """
    Final node to format the output.
    """
    generated_playlist = state.get("generated_playlist", [])
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else "No output"
    
    # If we have a playlist link in the last message, we can format it nicely
    # Or if we have the list of songs in generated_playlist, we can show them.
    
    final_output = f"""
    # Playlist Generation Complete
    
    {last_msg}
    
    ## Tracks Added:
    """
    
    for track in generated_playlist:
        final_output += f"- {track['artist']} - {track['title']}\n"
        
    return {"messages": [final_output]}
