import json
from agents.supervisor import run_supervisor
from agents.market_context_agent import run_market_context
from agents.data_scout_news import run_news_scout
from agents.quant_screener import run_quant_screener
from agents.risk_sizer import run_risk_sizer
from agents.thesis_agent import run_thesis_agent
from agents.validator_node import run_validator

def main():
    # 1. Load Phase 1 + Phase 2 data
    print("=" * 60)
    print("PHASE 3: LLM QUAL LAYER TEST")
    print("=" * 60)

    print("\nLoading Phase 1 data...")
    with open('scratch/phase1_output.json', 'r') as f:
        phase1 = json.load(f)

    state = {
        'fundamentals': phase1.get('fundamentals', {}),
        'technicals': phase1.get('technicals', {}),
        'universe': list(phase1.get('fundamentals', {}).keys()),
        'market_context': {},
        'candidates': [],
        'trades': [],
        'thesis': {},
        'news_sentiment': {},
        'active_setups': [],
        'risk_modifier': 1.0,
        'next_agent': ''
    }

    # 2. Supervisor (LLM node 1)
    print("\n--- 1. Supervisor Agent (LLM) ---")
    state = run_supervisor(state)
    print(f"  Active setups: {state.get('active_setups')}")
    print(f"  Risk modifier: {state.get('risk_modifier')}")

    # 3. Market Context (Deterministic + LLM node 2)
    print("\n--- 2. Market Context Agent (Deterministic + LLM) ---")
    state = run_market_context(state)
    mc = state['market_context']
    print(f"  Regime:          {mc.get('regime')}")
    print(f"  VIX:             {mc.get('vix')}")
    print(f"  Event Flag:      {mc.get('event_flag')}")
    print(f"  Narrative:       {mc.get('regime_narrative')}")

    # 4. Quant Screener (Deterministic)
    print("\n--- 3. Quant Screener (Deterministic) ---")
    state = run_quant_screener(state)
    candidates = state.get('candidates', [])
    print(f"  Candidates found: {len(candidates)}")

    if not candidates:
        print("  Injecting test candidates for pipeline validation...")
        techs = state['technicals']
        for ticker in list(techs.keys())[:3]:
            state['candidates'].append({
                'ticker': ticker,
                'setup': 'value_breakout',
                'score': 1.5,
                'expected_R': 3.0
            })

    # 5. Risk Sizer (Deterministic)
    print("\n--- 4. Risk Sizer (Deterministic) ---")
    state = run_risk_sizer(state)
    print(f"  Sized trades: {len(state.get('trades', []))}")

    # 6. News Scout (Tavily + LLM)
    print("\n--- 5. News Scout (Tavily + LLM) ---")
    state = run_news_scout(state)
    for ticker, news in state.get('news_sentiment', {}).items():
        print(f"  {ticker}: sentiment={news['sentiment']}, events={news['events']}, articles={news['articles_found']}")

    # 7. Thesis Agent (LLM node 3)
    print("\n--- 6. Thesis Agent (LLM) ---")
    state = run_thesis_agent(state)
    for ticker, t in state.get('thesis', {}).items():
        print(f"\n  {ticker}:")
        print(f"    Thesis:     {t.get('thesis', '')[:150]}...")
        print(f"    Confidence: {t.get('confidence')}/10")

    # 8. Validator v2 (Deterministic + hallucination check)
    print("\n--- 7. Validator v2 (Deterministic + Hallucination Check) ---")
    state = run_validator(state)
    valid_trades = state.get('trades', [])
    print(f"  Valid trades: {len(valid_trades)}")
    print(f"  Next agent:   {state.get('next_agent')}")
    for t in valid_trades:
        print(f"    {t['ticker']:15s}  entry={t['entry']:>10.2f}  SL={t['sl']:>10.2f}  "
              f"target={t['target']:>10.2f}  confidence={t.get('confidence', 'N/A')}")

    # 9. Save output
    output = {
        'market_context': state['market_context'],
        'active_setups': state.get('active_setups', []),
        'risk_modifier': state.get('risk_modifier', 1.0),
        'news_sentiment': state.get('news_sentiment', {}),
        'thesis': state.get('thesis', {}),
        'trades': valid_trades,
        'next_agent': state.get('next_agent')
    }
    with open('scratch/phase3_output.json', 'w') as f:
        json.dump(output, f, indent=4, default=str)

    print("\n" + "=" * 60)
    print("Phase 3 test complete. Output: scratch/phase3_output.json")
    print("=" * 60)

if __name__ == "__main__":
    main()
