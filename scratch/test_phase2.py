import json
from agents.market_context_agent import run_market_context
from agents.quant_screener import run_quant_screener
from agents.risk_sizer import run_risk_sizer
from agents.validator_node import run_validator

def main():
    # 1. Load Phase 1 output to avoid re-fetching
    print("Loading Phase 1 data...")
    with open('scratch/phase1_output.json', 'r') as f:
        phase1 = json.load(f)

    state = {
        'fundamentals': phase1.get('fundamentals', {}),
        'technicals': phase1.get('technicals', {}),
        'universe': list(phase1.get('fundamentals', {}).keys()),
        'market_context': {},
        'candidates': [],
        'trades': [],
        'next_agent': ''
    }

    # 2. Market Context
    print("\n--- Market Context Agent ---")
    state = run_market_context(state)
    mc = state['market_context']
    print(f"  Regime:     {mc.get('regime')}")
    print(f"  NIFTY:      {mc.get('nifty_close')}")
    print(f"  VIX:        {mc.get('vix')}")
    print(f"  FII Net:    {mc.get('fii_net')}")
    print(f"  US Change:  {mc.get('us_futures_change')}")
    print(f"  NIFTY 5d:   {mc.get('nifty_5d_return')}")

    # 3. Quant Screener
    print("\n--- Quant Screener ---")
    state = run_quant_screener(state)
    candidates = state.get('candidates', [])
    print(f"  Candidates found: {len(candidates)}")
    for c in candidates:
        print(f"    {c['ticker']:20s}  setup={c['setup']:25s}  score={c['score']:.2f}")

    if not candidates:
        print("\n  No candidates passed screener filters with 5 test tickers.")
        print("  This is expected — filters are strict and designed for NSE500.")
        print("  Injecting test candidates to validate the rest of the pipeline...\n")

        # Inject synthetic candidates so we can test risk_sizer + validator
        techs = state['technicals']
        for ticker in list(techs.keys())[:3]:
            state['candidates'].append({
                'ticker': ticker,
                'setup': 'value_breakout',
                'score': 1.5,
                'expected_R': 3.0
            })
        candidates = state['candidates']
        print(f"  Injected {len(candidates)} test candidates.")

    # 4. Risk Sizer
    print("\n--- Risk Sizer ---")
    state = run_risk_sizer(state)
    trades = state.get('trades', [])
    print(f"  Sized trades: {len(trades)}")
    for t in trades:
        print(f"    {t['ticker']:15s}  entry={t['entry']:>10.2f}  SL={t['sl']:>10.2f}  "
              f"target={t['target']:>10.2f}  qty={t['qty']:>5d}  risk={t['total_risk']:>10.2f}")

    # 5. Validator
    print("\n--- Validator ---")
    state = run_validator(state)
    valid_trades = state.get('trades', [])
    print(f"  Valid trades: {len(valid_trades)}")
    print(f"  Next agent:   {state.get('next_agent')}")
    for t in valid_trades:
        print(f"    {t['ticker']:15s}  entry={t['entry']:>10.2f}  SL={t['sl']:>10.2f}  "
              f"target={t['target']:>10.2f}  qty={t['qty']:>5d}  risk={t['total_risk']:>10.2f}")

    # 6. Save output
    output = {
        'market_context': state['market_context'],
        'candidates': state.get('candidates', []),
        'trades': valid_trades,
        'next_agent': state.get('next_agent')
    }
    with open('scratch/phase2_output.json', 'w') as f:
        json.dump(output, f, indent=4)
    print("\nSaved to scratch/phase2_output.json")

if __name__ == "__main__":
    main()
