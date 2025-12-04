"""
Page summarizer using Qwen 3:4B via Ollama and LangGraph.
Provides an AI-powered summary generation for book pages.
"""

from typing import TypedDict
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
import re


class SummaryState(TypedDict):
    """State for the summary workflow."""
    page_content: str
    summary: str
    error: str | None


def create_summary_workflow():
    """
    Creates a LangGraph workflow for summarizing page content.
    Uses Qwen 3:4B model via Ollama.
    """

    # Initialize the Qwen 3:4B model via Ollama
    model = ChatOllama(
        model="qwen3:4b",
        base_url="http://localhost:11434",  # Default Ollama endpoint
        temperature=0.7,
    )

    # Create prompt template for summarization
    summary_prompt = PromptTemplate(
        input_variables=["content"],
        template="""You are an expert book summarizer. Your task is to create a concise, 
informative summary of the given page content. Focus on the main ideas, key events, 
and important details. Keep the summary clear and easy to understand.

Page Content:
{content}

Please provide a summary of this page content in 2-3 sentences:"""
    )

    # Create the workflow graph
    workflow = StateGraph(SummaryState)

    # Define the summarization node
    def summarize_node(state: SummaryState) -> SummaryState:
        """Node that performs the actual summarization."""
        try:
            # Prepare the input
            formatted_prompt = summary_prompt.format(content=state["page_content"])

            # Call the model
            response = model.invoke(formatted_prompt)

            # Extract the text from the response
            summary_text = response.content.strip()

            return {
                **state,
                "summary": summary_text,
                "error": None,
            }
        except Exception as e:
            return {
                **state,
                "summary": "",
                "error": str(e),
            }

    # Add nodes to the workflow
    workflow.add_node("summarize", summarize_node)

    # Add edges
    workflow.add_edge(START, "summarize")
    workflow.add_edge("summarize", END)

    # Compile the workflow
    return workflow.compile()


# Global workflow instance (lazy-loaded)
_summary_workflow = None


def get_summary_workflow():
    """Get or create the summary workflow."""
    global _summary_workflow
    if _summary_workflow is None:
        _summary_workflow = create_summary_workflow()
    return _summary_workflow


def summarize_page(page_content: str) -> tuple[str, str | None]:
    """
    Summarizes a page content using the LangGraph workflow.

    Args:
        page_content: The HTML or text content of the page to summarize

    Returns:
        A tuple of (summary, error_message) where error_message is None if successful
    """
    # Strip HTML tags for better summarization
    clean_content = strip_html_tags(page_content)

    # Limit content to first 2000 characters to avoid token limits
    if len(clean_content) > 2000:
        clean_content = clean_content[:2000] + "..."

    # Run the workflow
    workflow = get_summary_workflow()
    result = workflow.invoke(
        {
            "page_content": clean_content,
            "summary": "",
            "error": None,
        }
    )

    return result["summary"], result["error"]


def strip_html_tags(html_content: str) -> str:
    """
    Removes HTML tags from content for cleaner text processing.

    Args:
        html_content: HTML content to clean

    Returns:
        Cleaned text content
    """
    # Remove script and style tags
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)

    # Remove all other HTML tags
    clean = re.sub(r"<[^>]+>", "", clean)

    # Decode HTML entities
    clean = clean.replace("&nbsp;", " ")
    clean = clean.replace("&quot;", '"')
    clean = clean.replace("&apos;", "'")
    clean = clean.replace("&amp;", "&")
    clean = clean.replace("&lt;", "<")
    clean = clean.replace("&gt;", ">")

    # Clean up whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean
