# app.py

from flask import Flask, render_template, request, jsonify
import logging
import asyncio
import os
from dotenv import load_dotenv

# 加載環境變量
load_dotenv()
from analyzer import GrowthSignalAnalyzer # 從 analyzer 導入核心邏輯
from config import FLASK_DEBUG, FLASK_PORT, PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY
from stock_scanner import StockScanner  # F3.1: 導入股票掃描器
from gemini_analyzer import GeminiEnhancedAnalyzer
from news_analyzer import EnhancedNewsAnalyzer

# 這是為了解決 U3.1 的模擬數據 (熱門股票建議)
TICKER_SUGGESTIONS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD", "META", "AMZN"] 

# 初始化 Flask 應用
app = Flask(__name__)
analyzer = GrowthSignalAnalyzer()
scanner = StockScanner()  # F3.1: 初始化股票掃描器

# 初始化 AI 分析器
ai_enhanced_analyzer = None
news_analyzer = EnhancedNewsAnalyzer()

# 檢查是否有OpenRouter API密鑰
api_key = os.getenv('OPENROUTER_API_KEY')
logging.info(f"API密鑰狀態: {'已設置' if api_key else '未設置'}")
if api_key and api_key != 'your_openrouter_api_key_here':
    try:
        ai_enhanced_analyzer = GeminiEnhancedAnalyzer(api_key)
        logging.info("AI增強功能已啟用")
    except Exception as e:
        logging.error(f"AI分析器初始化失敗: {e}")
        ai_enhanced_analyzer = None
else:
    logging.warning("未設置有效的OPENROUTER_API_KEY，AI功能將被禁用")

@app.route('/')
def index():
    """根路由：處理前端介面"""
    # U3.2: 傳遞時間週期選項給前端
    time_periods = {
        "Daily (1Y)": PERIOD_DAILY,
        "Weekly (5Y)": PERIOD_WEEKLY,
        "Monthly (10Y)": PERIOD_MONTHLY
    }
    
    # F3.2: 獲取推薦股票
    try:
        recommended_stocks = scanner.get_recommended_stocks(limit=8)
    except Exception as e:
        logging.error(f"獲取推薦股票失敗: {e}")
        recommended_stocks = []
    
    # U3.1: 傳遞建議股票列表和推薦股票
    return render_template('index.html', 
                           time_periods=time_periods,
                           suggestions=TICKER_SUGGESTIONS,
                           recommended_stocks=recommended_stocks)

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

# F3.2: 推薦股票API
@app.route('/api/recommended-stocks', methods=['GET'])
def get_recommended_stocks():
    """獲取推薦股票列表"""
    try:
        limit = request.args.get('limit', 10, type=int)
        recommended_stocks = scanner.get_recommended_stocks(limit=limit)
        
        return jsonify({
            "success": True,
            "recommended_stocks": recommended_stocks,
            "count": len(recommended_stocks)
        })
    except Exception as e:
        logging.error(f"獲取推薦股票失敗: {e}")
        return jsonify({"error": f"獲取推薦股票失敗: {str(e)}", "success": False})

# F3.3: 手動觸發掃描API
@app.route('/api/trigger-scan', methods=['POST'])
def trigger_scan():
    """手動觸發股票掃描"""
    try:
        max_stocks = request.json.get('max_stocks', 30) if request.json else 30
        
        logging.info(f"手動觸發掃描: {max_stocks} 支股票")
        
        # 執行動態掃描
        results = scanner.batch_scan_stocks(max_stocks=max_stocks)
        
        return jsonify({
            "success": True,
            "message": f"掃描完成: 掃描 {results['total_scanned']} 支股票，找到 {results['patterns_found']} 個形態",
            "scan_results": results
        })
    except Exception as e:
        logging.error(f"手動掃描失敗: {e}")
        return jsonify({"error": f"手動掃描失敗: {str(e)}", "success": False})

# F3.4: 止損建議API
@app.route('/api/stop-loss/<ticker>', methods=['GET'])
def get_stop_loss_advice(ticker):
    """獲取止損建議"""
    try:
        # 獲取股票數據
        stock_data = analyzer.get_stock_data(ticker, period="1y")
        if stock_data is None or len(stock_data) < 20:
            return jsonify({"error": "數據不足，無法計算止損建議", "success": False})
        
        # 計算止損建議
        current_price = stock_data['Close'].iloc[-1]
        recent_low = stock_data['Low'].tail(20).min()
        support_level = recent_low
        
        # 建議止損點 (支撐位下方3-5%)
        stop_loss_percentage = 0.03  # 3%
        suggested_stop_loss = support_level * (1 - stop_loss_percentage)
        
        # 計算風險評分
        returns = stock_data['Close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5)  # 年化波動率
        
        if volatility < 0.2:
            risk_level = "低風險"
            risk_score = 1
        elif volatility < 0.4:
            risk_level = "中風險"
            risk_score = 2
        else:
            risk_level = "高風險"
            risk_score = 3
        
        # 最大損失百分比
        max_loss_pct = (current_price - suggested_stop_loss) / current_price * 100
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "current_price": round(current_price, 2),
            "suggested_stop_loss": round(suggested_stop_loss, 2),
            "support_level": round(support_level, 2),
            "max_loss_percentage": round(max_loss_pct, 2),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "volatility": round(volatility, 3),
            "advice": f"建議止損點: ${suggested_stop_loss:.2f} (最大損失: {max_loss_pct:.1f}%)"
        })
        
    except Exception as e:
        logging.error(f"計算止損建議失敗: {e}")
        return jsonify({"error": f"計算止損建議失敗: {str(e)}", "success": False})


# AI 分析路由
@app.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    """AI 增強分析"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "無效的請求數據", "success": False})
            
        ticker = data.get('ticker', '').strip().upper()
        period = data.get('period', PERIOD_DAILY)
        
        if not ticker:
            return jsonify({"error": "請輸入股票代號", "success": False})
        
        logging.info(f"正在進行AI分析: {ticker}")
        
        # 1. 執行技術分析
        technical_result = analyzer.generate_signal(ticker, period=period)
        
        if not technical_result.get('success'):
            return jsonify(technical_result)
        
        # 2. 如果啟用AI，執行AI增強分析
        if ai_enhanced_analyzer:
            enhanced_result = asyncio.run(ai_enhanced_analyzer.enhanced_analysis(ticker, technical_result))
            return jsonify(enhanced_result)
        else:
            # 回退到純技術分析，但添加新聞分析
            news_result = asyncio.run(news_analyzer.comprehensive_analysis(ticker))
            return jsonify({
                **technical_result,
                "news_analysis": news_result,
                "ai_enhanced": False,
                "message": "AI功能未啟用，顯示技術分析結果"
            })
            
    except Exception as e:
        logging.error(f"AI分析失敗: {e}")
        return jsonify({"error": f"AI分析失敗: {str(e)}", "success": False})

# 新聞分析路由
@app.route('/api/news/<ticker>')
def get_news(ticker):
    """獲取股票新聞"""
    try:
        news_result = asyncio.run(news_analyzer.comprehensive_analysis(ticker))
        return jsonify(news_result)
    except Exception as e:
        logging.error(f"新聞獲取失敗: {e}")
        return jsonify({"error": f"新聞獲取失敗: {str(e)}", "success": False})

if __name__ == '__main__':
    logging.info("啟動股票分析服務...")
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)