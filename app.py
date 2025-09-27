# app.py

from flask import Flask, render_template, request, jsonify, url_for
import logging
from analyzer import GrowthSignalAnalyzer # 從 analyzer 導入核心邏輯
from config import FLASK_DEBUG, FLASK_PORT, PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY

# 這是為了解決 U3.1 的模擬數據 (熱門股票建議)
TICKER_SUGGESTIONS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD", "META", "AMZN"] 

# 初始化 Flask 應用
app = Flask(__name__)
analyzer = GrowthSignalAnalyzer()

@app.route('/')
def index():
    """根路由：處理前端介面"""
    # U3.2: 傳遞時間週期選項給前端
    time_periods = {
        "Daily (1Y)": PERIOD_DAILY,
        "Weekly (5Y)": PERIOD_WEEKLY,
        "Monthly (10Y)": PERIOD_MONTHLY
    }
    # U3.1: 傳遞建議股票列表
    return render_template('index.html', 
                           time_periods=time_periods,
                           suggestions=TICKER_SUGGESTIONS)

@app.route('/signal/generate', methods=['POST'])
def generate_signal_route():
    """API 路由：生成分析信號"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "無效的請求數據", "success": False})
            
        ticker = data.get('ticker', '').strip().upper()
        # U3.2: 接收前端傳入的時間週期選項
        period = data.get('period', PERIOD_DAILY) 
        
        if not ticker:
            return jsonify({"error": "請輸入股票代號", "success": False})
        
        logging.info(f"正在分析股票: {ticker} (週期: {period})")
        
        # 核心邏輯在 analyzer.py 處理
        result = analyzer.generate_signal(ticker, period=period) 
        
        if not result.get('success'):
             # S1.4: 改善錯誤回饋
             error_msg = result.get('error', '未知分析錯誤')
             logging.warning(f"分析失敗: {error_msg}")
             return jsonify({"error": f"分析失敗: {error_msg}", "success": False})
        
        logging.info(f"分析成功: {ticker}")
        
        return jsonify(result)
    
    except Exception as e:
        # S1.4: 服務器致命錯誤處理
        logging.critical(f"服務器錯誤: {str(e)}", exc_info=True)
        return jsonify({"error": f"服務器致命錯誤: {str(e)}", "success": False})

if __name__ == '__main__':
    logging.info("啟動股票分析服務...")
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)