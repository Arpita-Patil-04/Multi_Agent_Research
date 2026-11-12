import streamlit as st
from pipeline import run_research_pipeline


# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Multi-Agent AI Research System",
    page_icon="🔎",
    layout="wide"
)


# --------------------------------------------------
# Custom Styling
# --------------------------------------------------

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 700;
    margin-bottom: 5px;
}

.subtitle {
    font-size: 18px;
    color: #777;
    margin-bottom: 30px;
}



</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# Header
# --------------------------------------------------

st.markdown(
    '<div class="main-title">🔎 Multi-Agent AI Research System</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Search → Read → Write → Critic'
    '</div>',
    unsafe_allow_html=True
)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.header("⚙️ Research System")

    st.write(
        """
        This system uses multiple AI components to research
        a topic and generate a structured report.
        """
    )

    st.divider()

    st.markdown("### Pipeline")

    st.markdown("""
    **1. 🔍 Search Agent**  
    Searches the web using Tavily.

    **2. 📖 Reader Agent**  
    Selects and scrapes relevant sources.

    **3. ✍️ Writer Chain**  
    Generates a structured research report.

    **4. 🧐 Critic Chain**  
    Reviews the generated report.
    """)

    st.divider()

    st.caption("Built with LangChain, OpenAI, Tavily and Streamlit")


# --------------------------------------------------
# User Input
# --------------------------------------------------

st.subheader("Research Topic")

topic = st.text_input(
    "Enter a topic you want to research:",
    placeholder="Example: Impact of AI on the stock market"
)


# --------------------------------------------------
# Run Research
# --------------------------------------------------

if st.button("🚀 Start Research", type="primary"):

    if not topic.strip():
        st.warning("Please enter a research topic first.")

    else:
        st.session_state["research_result"] = None

        try:
            with st.status("🤖 AI agents are researching...", expanded=True) as status:
                result = run_research_pipeline(topic, on_step=st.write)
                status.update(label="Research complete", state="complete", expanded=False)

            st.session_state["research_result"] = result

        except Exception as e:
            st.error(f"An error occurred while running the research pipeline:\n\n{e}")


# --------------------------------------------------
# Display Results
# --------------------------------------------------

if st.session_state.get("research_result"):

    result = st.session_state["research_result"]

    st.success("✅ Research completed successfully!")

    # ----------------------------------------------
    # Search Results
    # ----------------------------------------------

    with st.expander("🔍 Search Results", expanded=False):

        st.markdown(
            result.get(
                "search_results",
                "No search results available."
            )
        )

    # ----------------------------------------------
    # Scraped Content
    # ----------------------------------------------

    with st.expander("📖 Scraped Research Content", expanded=False):

        st.markdown(
            result.get(
                "scraped_content",
                "No scraped content available."
            )
        )

    # ----------------------------------------------
    # Final Report
    # ----------------------------------------------

    st.subheader("📄 Final Research Report")

    report = result.get(
        "report",
        "No report generated."
    )

    st.markdown(report)

    # ----------------------------------------------
    # Critic Feedback
    # ----------------------------------------------

    if result.get("score"):
        st.caption(f"Final score: {result['score']}/10 after {result.get('attempts')} draft(s)")

    st.subheader("🧐 Critic Evaluation")

    feedback = result.get("feedback") or "No critic feedback available."

    st.markdown(feedback)

    # ----------------------------------------------
    # Download Report
    # ----------------------------------------------

    st.download_button(
        label="⬇️ Download Research Report",
        data=report,
        file_name="research_report.md",
        mime="text/markdown"
    )