import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.state import State
from src.models import llm_orch
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any

# --- CONFIGURATION ---
MAX_ITERATIONS = 10 # Increased for deeper research
MIN_SONGS_FOR_EARLY_STOP = 25 # Higher threshold for quality

async def _run_agentic_search(playlist_context: str, user_request: str):
    """
    Executes a DEEP AGENTIC SEARCH where the LLM autonomously decides which MCP tools to call.
    OPTIMIZED FOR QUALITY: Prioritizes deep understanding and curation over speed.
    """
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.servers.online_searcher"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            mcp_tools = await session.list_tools()
            print(f"[MCP Client] Available Tools: {[t.name for t in mcp_tools.tools]}")
            
            tools_description = []
            for t in mcp_tools.tools:
                tool_info = {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
                tools_description.append(tool_info)
            
            # HIGH QUALITY SYSTEM PROMPT
            agent_prompt = f"""
You are an Elite Music Curator and Researcher. You have access to advanced MCP tools:

{json.dumps(tools_description, indent=2)}

YOUR GOAL: Create a "Perfect Playlist" based on:
- Context: {playlist_context}
- User Request: {user_request}

ISTRUZIONI IMPORTANTI:
1. **CHIAMATE PARALLELE**: Puoi chiamare MULTIPLI tool nella stessa iterazione per efficienza
2. Decidi autonomamente QUALI tool chiamare e in CHE ORDINE
3. Puoi chiamare lo stesso tool più volte con parametri diversi se necessario
4. Quando hai raccolto abbastanza informazioni (15-20 canzoni varie), termina

FORMATI DI RISPOSTA:

Per chiamare UN SOLO tool:
{{"action": "call_tool", "tool": "nome_tool", "arguments": {{"param": "valore"}}}}

Per chiamare MULTIPLI tool in PARALLELO (CONSIGLIATO):
{{"action": "call_tools", "calls": [
  {{"tool": "tool_name", "arguments": {{"arg": "value"}}}},
  ...
]}}

To finish:
{{"action": "finish", "final_songs": "List of songs with Title - Artist"}}

Start by ANALYZING the vibe deeply.
"""
            
            messages = [
                SystemMessage(content=agent_prompt),
                HumanMessage(content="Start the deep research process. Analyze the vibe first.")
            ]
            collected_data = []
            songs_count = 0
            
            for iteration in range(MAX_ITERATIONS):
                print(f"\n[Agent] Iteration {iteration + 1}/{MAX_ITERATIONS}")
                
                response = llm_orch.invoke(messages)
                messages.append(AIMessage(content=response.content))
                
                print(f"[Agent] Thought: {response.content[:200]}...")
                
                try:
                    content = response.content.strip()
                    
                    if "{" in content:
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        decision = json.loads(content[json_start:json_end])
                    else:
                        # Fallback if no JSON found, assume finish or continue conversation
                        if "final_songs" in content:
                             decision = {"action": "finish", "final_songs": content}
                        else:
                             decision = {"action": "continue", "message": content}

                    if decision.get("action") == "finish":
                        print("[Agent] ✓ Decision: FINISH - Returning results")
                        return decision.get("final_songs", "\n".join(collected_data))
                    
                    elif decision.get("action") == "call_tools":
                        calls = decision.get("calls", [])
                        print(f"[Agent] ✓ Calling {len(calls)} tools in PARALLEL")
                        
                        async def call_tool_async(call):
                            tool_name = call.get("tool")
                            arguments = call.get("arguments", {})
                            try:
                                result = await session.call_tool(tool_name, arguments=arguments)
                                tool_output = result.content[0].text
                                return {"success": True, "tool": tool_name, "output": tool_output}
                            except Exception as e:
                                return {"success": False, "tool": tool_name, "error": str(e)}
                        
                        tasks = [call_tool_async(call) for call in calls]
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        all_results = []
                        for result in results:
                            if isinstance(result, Exception):
                                all_results.append(f"ERROR: {str(result)}")
                            elif result.get("success"):
                                tool_name = result["tool"]
                                tool_output = result["output"]
                                collected_data.append(f"[{tool_name}]: {tool_output}")
                                songs_count += tool_output.count("-")
                                all_results.append(f"[{tool_name} Output]:\n{tool_output}")
                                print(f"[Agent]   ✓ {tool_name} completed")
                            else:
                                error_msg = f"ERROR in {result['tool']}: {result.get('error', 'Unknown')}"
                                all_results.append(error_msg)
                        
                        messages.append(HumanMessage(
                            content=f"Tool Results:\n" + "\n\n".join(all_results) + 
                                   f"\n\nCurrent Song Count: ~{songs_count}. Continue researching until you have a PERFECT list."
                        ))
                    
                    elif decision.get("action") == "call_tool":
                        # Handle single tool call
                        tool_name = decision.get("tool")
                        arguments = decision.get("arguments", {})
                        print(f"[Agent] ✓ Calling single tool: {tool_name}")
                        
                        try:
                            result = await session.call_tool(tool_name, arguments=arguments)
                            tool_output = result.content[0].text
                            collected_data.append(f"[{tool_name}]: {tool_output}")
                            songs_count += tool_output.count("-")
                            print(f"[Agent]   ✓ {tool_name} completed")
                            
                            messages.append(HumanMessage(
                                content=f"[{tool_name} Output]:\n{tool_output}\n\nCurrent Song Count: ~{songs_count}. Continue researching until you have a PERFECT list."
                            ))
                        except Exception as e:
                            error_msg = f"ERROR in {tool_name}: {str(e)}"
                            print(f"[Agent]   ✗ {error_msg}")
                            messages.append(HumanMessage(content=error_msg))
                    
                    else:
                        # Handle other actions or early stop
                        if collected_data and songs_count > MIN_SONGS_FOR_EARLY_STOP:
                             return "\n\n".join(collected_data)
                        # No valid action, prompt the LLM to respond correctly
                        messages.append(HumanMessage(
                            content="Please respond with a valid action: call_tool, call_tools, or finish."
                        ))
                        
                except json.JSONDecodeError:
                    print("[Agent] ⚠ Invalid JSON response")
                    messages.append(HumanMessage(
                        content="Please respond with valid JSON format."
                    ))
                except Exception as e:
                    print(f"[Agent] Error: {e}")
                    if collected_data:
                        return "\n\n".join(collected_data)
                    break
            
            print(f"[Agent] ⚠ Max iterations reached ({songs_count} songs)")
            return "\n\n".join(collected_data)

def online_search(state: State) -> dict:
    """
    Agentic Node that connects to the MCP Server.
    """
    context = state.get("playlist_context", "")
    messages = state.get("messages", [])
    user_request = messages[0].content if messages else ""
    
    if not context:
        return {"error": "No playlist context found"}
    
    print(f"\n{'='*60}")
    print(f"[ONLINE SEARCH NODE] Starting DEEP Agentic Research")
    print(f"{'='*60}\n")
    
    try:
        final_results = asyncio.run(_run_agentic_search(context, user_request))
        
        print(f"\n[ONLINE SEARCH NODE] ✓ Research Completed")
        print(f"[ONLINE SEARCH NODE] Results length: {len(final_results)} chars\n")
        
        return {
            "messages": [AIMessage(content=final_results)],
            "playlist_context": context
        }
        
    except Exception as e:
        error_msg = f"Error during agentic search: {str(e)}"
        print(f"[ONLINE SEARCH NODE] ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg}
