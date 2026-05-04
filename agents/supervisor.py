import json
from tools.llm_tool import get_llm

def run_supervisor(state: dict) -> dict:
    """
    Supervisor Agent: Reads strategy_memory + trading_journal.
    Uses LLM to decide active_setups and risk_modifier.
    Routes to market_context_agent.
    """
    # Load strategy memory
    try:
        with open('memory/strategy_memory.json', 'r') as f:
            memory = json.load(f)
    except Exception:
        memory = {"setups": {}, "regime_multipliers": {}, "special_events": []}

    # Load last 2000 chars of trading journal
    try:
        with open('memory/trading_journal.md', 'r') as f:
            journal_full = f.read()
            journal_tail = journal_full[-2000:] if len(journal_full) > 2000 else journal_full
    except Exception:
        journal_tail = ""

    market_context = state.get('market_context', {})

    llm = get_llm(temperature=0.3)
    if not llm:
        print("Warning: LLM not configured. Using defaults for supervisor.")
        state['active_setups'] = list(memory.get('setups', {}).keys())
        state['risk_modifier'] = 1.0
        state['next_agent'] = 'market_context_agent'
        return state

    try:
        weights_summary = {
            k: {"weight": v.get("weight"), "trades": v.get("trades"), "wins": v.get("wins")}
            for k, v in memory.get('setups', {}).items()
        }

        prompt = f"""You are the trading supervisor for an NSE pre-market system.

Strategy Memory (setup weights):
{json.dumps(weights_summary, indent=2)}

Recent Trading Journal (lessons learned):
{journal_tail}

Today's Market Context:
{json.dumps(market_context, indent=2, default=str)}

Based on the above, decide:
1. Which setups should be ACTIVE today (list from: value_breakout, momentum_pullback, quality_compounder)
2. A risk_modifier between 0.5 and 1.5 (reduce if journal warns about losses or if today is an event day)

Rules:
- If journal mentions losses for a setup but trades < 30, do NOT deactivate it
- If market_context has event_flag != "none", reduce risk_modifier
- If regime is "high_vix", prefer quality_compounder over momentum

Return ONLY valid JSON with no markdown formatting:
{{
  "active_setups": ["setup1", "setup2"],
  "risk_modifier": 1.0,
  "reasoning": "1-2 sentence explanation"
}}

JSON response:"""

        response = llm.invoke(prompt)
        content = response.content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        parsed = json.loads(content)
        state['active_setups'] = parsed.get('active_setups', list(memory.get('setups', {}).keys()))
        state['risk_modifier'] = max(0.5, min(1.5, float(parsed.get('risk_modifier', 1.0))))
        print(f"Supervisor: active_setups={state['active_setups']}, risk_modifier={state['risk_modifier']}")
        if parsed.get('reasoning'):
            print(f"  Reasoning: {parsed['reasoning']}")

    except Exception as e:
        print(f"Supervisor LLM error: {e}")
        state['active_setups'] = list(memory.get('setups', {}).keys())
        state['risk_modifier'] = 1.0

    state['next_agent'] = 'market_context_agent'
    return state
