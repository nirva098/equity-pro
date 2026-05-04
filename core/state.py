from typing import TypedDict, List, Dict, Any

class AlphaState(TypedDict):
    date: str
    universe: List[str]
    market_context: Dict[str, Any]
    fundamentals: Dict[str, Any]
    technicals: Dict[str, Any]
    news_sentiment: Dict[str, Any]
    thesis: Dict[str, Any]
    trades: List[Dict[str, Any]]
    execution_log: List[Any]
    eod_pnl: Dict[str, Any]
    strategy_memory: Dict[str, Any]
    next_agent: str
