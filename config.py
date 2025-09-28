# config.py

import os

# --- 系統設定 ---
FLASK_DEBUG = True
FLASK_PORT = 5001
SP500_TICKER = "^GSPC"
CACHE_TIMEOUT_SECONDS = 300  # 數據緩存時間 (5 分鐘)

# --- 技術指標週期設定 ---
PERIOD_DAILY = "1y"
PERIOD_WEEKLY = "5y"
PERIOD_MONTHLY = "10y"
DEFAULT_CHART_PERIOD = PERIOD_DAILY

RSI_PERIOD = 14
MACD_SHORT_PERIOD = 12
MACD_LONG_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
BB_PERIOD = 20
BB_STD_DEV = 2

# --- 交易信號閾值與建議 ---
SCORE_STRONG_BUY = 80
SCORE_HOLD = 60
STOP_LOSS_PERCENTAGE = 0.95  # 建議止損點為最低價的 95%

# --- 評分機制權重 (M2.2 修正後的權重) ---
# 總和為 100%
WEIGHTS = {
    "RS_RATING": 20,       # 相對強度
    "RSI_SCORE": 15,       # 相對強弱指數 (動量)
    "MACD_SCORE": 15,      # 移動平均線聚合離散 (趨勢)
    "BB_SCORE": 10,        # 布林通道 (波動率/超買超賣)
    "VOLUME_OK": 10,       # 成交量確認
    "PATTERN_BONUS": 10,   # 形態獎勵 (VCP/Cup)
    "TREND_FILTER": 20     # MA200 大盤趨勢過濾
}

# --- AI增強分析權重 (新增) ---
# 總和為 100%
AI_ANALYSIS_WEIGHTS = {
    "TECHNICAL_ANALYSIS": 50,    # 技術分析 (50%)
    "NEWS_ANALYSIS": 20,         # 新聞分析 (20%)
    "MARKET_SENTIMENT": 15,      # 市場情緒 (15%)
    "RISK_ASSESSMENT": 15        # 風險評估 (15%)
}