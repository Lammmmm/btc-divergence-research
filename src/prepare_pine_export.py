from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=(R/'pine/original_user_source.pine').read_text(encoding='utf-8')
s=s[:s.index('// check minimum number of divergence')]
s=s.replace('Divergence for Many Indicators v4','Divergence Signal Audit Export').replace('overlay = true','overlay = false')
s+='\n// Research export: confirmed-bar signals. Pine compilation/export still requires TradingView.\n'
for j,n in enumerate(['MACD','Hist','RSI','Stoch','CCI','MOM','OBV','VWMACD','CMF','MFI']):
    for side,k in [('bull',0),('bear',1)]:
        s+=f'plot(barstate.isconfirmed and array.get(all_divergences, {j*4+k}) > 0 ? 1 : 0, title="{n}_{side}")\n'
s+='plot(atr(14), title="ATR14")\n'
(R/'pine/signal_audit_export.pine').write_text(s,encoding='utf-8')
print('Saved signal audit Pine; not compiled in TradingView')
