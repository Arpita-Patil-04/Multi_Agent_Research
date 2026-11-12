import time
from langchain_core.messages import ToolMessage
from agents import (
    build_reader_agent,
    build_search_agent,
    writer_chain,
    critic_chain,
    parse_score,
    extract_improvements,
)

MAX_REVISIONS = 2
PASS_SCORE = 7


def tool_outputs(result: dict) -> str:
    """Collect the RAW outputs of tool calls (not the LLM's paraphrase)."""
    outs = [m.content for m in result["messages"] if isinstance(m, ToolMessage)]
    return "\n\n=====\n\n".join(outs)


def run_research_pipeline(topic: str, on_step=print) -> dict:
    state = {}

    # Step 1: search
    on_step("🔍 Step 1/4 - Search agent is working...")
    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages": [("user", f"Find recent, reliable and relevant information about: {topic}")]
    })
    state["search_results"] = tool_outputs(search_result) or search_result["messages"][-1].content

    # Step 2: read
    on_step("📖 Step 2/4 - Reader agent is scraping sources...")
    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Based on these search results about '{topic}', pick the 3 most relevant "
            f"URLs and scrape each one.\n\nSearch Results:\n{state['search_results']}"
        )]
    })
    state["scraped_content"] = tool_outputs(reader_result) or reader_result["messages"][-1].content

    research = (
        f"SEARCH RESULTS:\n{state['search_results']}\n\n"
        f"SCRAPED CONTENT:\n{state['scraped_content']}"
    )

    # Steps 3-4: write -> critique -> (revise if score is low)
    feedback_text = "None"
    for attempt in range(MAX_REVISIONS + 1):
        on_step(f"✍️ Step 3/4 - Writer is drafting (attempt {attempt + 1})...")
        state["report"] = writer_chain.invoke({
            "topic": topic,
            "research": research,
            "feedback": feedback_text,
        })

        on_step("🧐 Step 4/4 - Critic is reviewing the report...")
        critique_text = None
        last_error = None
        for try_no in range(2):
            try:
                out = critic_chain.invoke({
                    "report": state["report"],
                    "research": research[:8000],
                })
                if out and out.strip():
                    critique_text = out
                    break
                last_error = ValueError("empty critic response")
            except Exception as e:
                last_error = e
            if try_no == 0:
                on_step("⏳ Critic had a problem, waiting 20s and retrying...")
                time.sleep(20)

        if critique_text is None:
            on_step(f"⚠️ Critic failed ({type(last_error).__name__}); keeping the current report.")
            state["feedback"] = f"Critic unavailable for this run ({type(last_error).__name__})."
            state["score"] = 0
            break

        state["feedback"] = critique_text
        state["score"] = parse_score(critique_text)

        if state["score"] == 0 or state["score"] >= PASS_SCORE:
            break  # 0 means the score could not be read, so don't loop blindly
        feedback_text = extract_improvements(critique_text)

    state["attempts"] = attempt + 1
    return state


if __name__ == "__main__":
    topic = input("\nEnter research topic: ")
    result = run_research_pipeline(topic)
    print("\n=== REPORT ===\n", result["report"])
    print("\n=== CRITIC ===\n", result["feedback"])

    # save this run as a backup for demos
    with open("sample_run.md", "w", encoding="utf-8") as f:
        f.write(f"# Topic: {topic}\n\n{result['report']}\n\n---\n\n## Critic\n\n{result['feedback']}\n")
    print("\nSaved to sample_run.md")