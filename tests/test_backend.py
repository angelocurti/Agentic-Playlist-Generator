from dotenv import load_dotenv
import os

# Carica le variabili da .env
load_dotenv()

from langchain_core.messages import HumanMessage

from src.agent import build_agent


def main() -> None:

    cfg = {"configurable": {"thread_id": "5"}}
    app = build_agent()

    inputs = {"messages": [HumanMessage(content="Generami una playlist per sentire il vero suono della dogo gang, solo cose da intenditore")]}

    result = app.invoke(inputs, config=cfg)

    print("=============Execution Resume=============")
    print(result.get("messages", []))

if __name__ == "__main__":
    main()