import sys
import os
import asyncio

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

# Load env variables BEFORE importing modules that instantiate OpenAI clients
if load_dotenv:
    load_dotenv()


async def main():
    print("=========================================")
    print("   Testing Text Defect Agent (Step 2)    ")
    print("=========================================\n")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-your-openai-api-key-here" or api_key == "dummy-key-for-testing":
        print("ERROR: Real OPENAI_API_KEY is not set.")
        print("Please copy .env.example to .env and insert your real OpenAI API key.")
        return

    from ai.subagents import text_defect_agent

    problem = input(
        "Enter a problem description "
        "(e.g., 'The dots are too small and inconsistent'):\n> "
    )

    print("\nEnter a few Q&A pairs from the questioning step.")
    print("Press Enter on an empty question when finished.\n")

    qa_pairs = []
    while True:
        question = input(f"Question {len(qa_pairs) + 1}:\n> ").strip()
        if not question:
            break

        answer = input("Answer:\n> ").strip()
        qa_pairs.append({"question": question, "answer": answer})
        print()

    print("\nCalling Text Defect Agent...\n")
    try:
        result = await text_defect_agent.run(
            problem_description=problem,
            qa_pairs=qa_pairs,
        )

        print("Detected Defect")
        print("-" * 30)
        print(f"Type: {result.get('defect_type')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Reasoning: {result.get('reasoning')}")
    except Exception as e:
        print(f"Error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
