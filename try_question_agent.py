import sys
import os
import asyncio
from dotenv import load_dotenv

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

# Load env variables BEFORE importing modules that instantiate OpenAI clients
load_dotenv()

from ai.subagents import question_agent

async def main():
    print("=========================================")
    print("   Testing Question Agent (Step 1)       ")
    print("=========================================\n")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-your-openai-api-key-here" or api_key == "dummy-key-for-testing":
        print("ERROR: Real OPENAI_API_KEY is not set.")
        print("Please copy .env.example to .env and insert your real OpenAI API key.")
        return

    problem = input("Enter a problem description (e.g., 'The dots are too small and inconsistent'):\n> ")
    
    print("\nCalling Question Agent...\n")
    try:
        result = await question_agent.run(problem_description=problem)
        print("Questions Asked by the Agent:\n" + "-"*30)
        for i, q in enumerate(result.get("questions", []), 1):
            print(f"{i}. {q}")
        print("-" * 30)
        print(f"\nEnough Info boolean output: {result.get('enough_info')}")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
