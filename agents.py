import re
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware, ToolCallLimitMiddleware
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, web_scrape
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, max_retries=6)
critic_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, max_retries=6)

# ---------- Agents ----------

def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=(
            "You are a research search assistant. ALWAYS call the web_search tool "
            "at least once. In your final answer, list every result with its "
            "title, URL and snippet exactly as returned. Do not invent URLs."
        ),
        middleware=[ToolCallLimitMiddleware(run_limit=3)],
    )


def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[web_scrape],
        system_prompt=(
            "You are a web reader. Pick the 3 most relevant URLs from the search "
            "results and call web_scrape on each one. Only use URLs that appear "
            "in the search results."
        ),
        middleware=[
            ToolRetryMiddleware(max_retries=2),
            ToolCallLimitMiddleware(run_limit=5),
        ],
    )


# ---------- Writer chain ----------

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. You write ONLY from the research provided. "
               "You never use outside knowledge, never invent facts, numbers, quotes, authors or URLs."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Reviewer feedback to address (ignore if it says 'None'):
{feedback}

Strict rules:
- Every claim must be supported by the research above. If the research does not say it, do not write it.
- Do NOT quote or cite any person, book or paper unless it appears in the research.
- Do NOT add a Methodology section or describe how the research was done.
- If the research is thin on something, say so briefly instead of filling the gap.
- If two sources give different figures for the same thing, report both and name each source. Do not describe one as a "refinement" of the other.
- Do NOT use tables. Use headings and bullet points only.
- Keep numbers consistent across the whole report.

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list only URLs that appear in the research)

Be detailed, factual and professional."""),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# ---------- Critic chain (plain text + regex parsing) ----------

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the report below against the research it was written from.

Research:
{research}

Report:
{report}

Check in this order:
1. Faithfulness: any quote, statistic, name or claim in the report that does NOT appear in the research is an unsupported claim. List each one.
2. Consistency: list any numbers or statements that contradict each other.
3. Structure, clarity and depth.

Rules:
- Only suggest improvements that can be made using the research provided. Never suggest adding facts, dates or sources that are not in the research.
- If the report has a fabricated quote, an unsupported statistic or an internal contradiction, the score must be 6 or lower.

Respond in EXACTLY this format:

Score: X/10

Strengths:
- ...

Areas to Improve:
- ...

Verdict: one line"""),
])

critic_chain = critic_prompt | critic_llm | StrOutputParser()


def parse_score(text: str) -> int:
    m = re.search(r"Score:\s*\**\s*(\d+)", text)
    return int(m.group(1)) if m else 0


def extract_improvements(text: str) -> str:
    m = re.search(r"Areas to Improve:?\**\s*(.*?)(?:\n\s*\**Verdict|\Z)", text, re.S)
    return m.group(1).strip() if m else text