from langgraph.graph import StateGraph, END
from core.state import AlphaState

from agents.supervisor import run_supervisor
from agents.market_context_agent import run_market_context
from agents.data_scout_fundamental import run_fundamental_scout
from agents.data_scout_technical import run_technical_scout
from agents.data_scout_news import run_news_scout
from agents.quant_screener import run_quant_screener
from agents.thesis_agent import run_thesis_agent
from agents.risk_sizer import run_risk_sizer
from agents.validator_node import run_validator
from agents.paper_executor import run_paper_executor
from agents.eod_reporter import run_eod_reporter
from agents.rl_updater import run_rl_updater

def _validator_router(state: dict) -> str:
    """Routes from validator: retry thesis if hallucination, else execute."""
    next_agent = state.get('next_agent', 'end')
    if next_agent == 'thesis_agent':
        return 'thesis_agent'
    elif next_agent == 'paper_executor':
        return 'paper_executor'
    else:
        return 'end'

def build_premarket_graph():
    """
    Builds the premarket LangGraph:
    START → supervisor → market_context → fundamental_scout → technical_scout
          → screener → news_scout → thesis → sizer → validator
          → {paper_executor | thesis_agent} → END
    """
    graph = StateGraph(dict)

    # Add nodes
    graph.add_node("supervisor", run_supervisor)
    graph.add_node("market_context", run_market_context)
    graph.add_node("fundamental_scout", run_fundamental_scout)
    graph.add_node("technical_scout", run_technical_scout)
    graph.add_node("screener", run_quant_screener)
    graph.add_node("news_scout", run_news_scout)
    graph.add_node("thesis_agent", run_thesis_agent)
    graph.add_node("risk_sizer", run_risk_sizer)
    graph.add_node("validator", run_validator)
    graph.add_node("paper_executor", run_paper_executor)

    # Set entry point
    graph.set_entry_point("supervisor")

    # Add edges (linear pipeline)
    graph.add_edge("supervisor", "market_context")
    graph.add_edge("market_context", "fundamental_scout")
    graph.add_edge("fundamental_scout", "technical_scout")
    graph.add_edge("technical_scout", "screener")
    graph.add_edge("screener", "news_scout")
    graph.add_edge("news_scout", "risk_sizer")
    graph.add_edge("risk_sizer", "thesis_agent")
    graph.add_edge("thesis_agent", "validator")

    # Conditional edge from validator
    graph.add_conditional_edges(
        "validator",
        _validator_router,
        {
            "thesis_agent": "thesis_agent",
            "paper_executor": "paper_executor",
            "end": END
        }
    )

    graph.add_edge("paper_executor", END)

    return graph.compile()

def build_eod_graph():
    """
    Builds the EOD LangGraph:
    START → eod_reporter → rl_updater → END
    """
    graph = StateGraph(dict)

    graph.add_node("eod_reporter", run_eod_reporter)
    graph.add_node("rl_updater", run_rl_updater)

    graph.set_entry_point("eod_reporter")
    graph.add_edge("eod_reporter", "rl_updater")
    graph.add_edge("rl_updater", END)

    return graph.compile()
