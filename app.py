# app.py

from flask import Flask, render_template, request, jsonify
import logging
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# 加載環境變量
load_dotenv()
from analyzer import GrowthSignalAnalyzer # 從 analyzer 導入核心邏輯
from config import FLASK_DEBUG, FLASK_PORT, PERIOD_DAILY, PERIOD_WEEKLY, PERIOD_MONTHLY
from stock_scanner import StockScanner  # F3.1: 導入股票掃描器
from gemini_analyzer import GeminiEnhancedAnalyzer
from news_analyzer import EnhancedNewsAnalyzer
from simple_news import get_latest_news
from watchlist import Watchlist

# 這是為了解決 U3.1 的模擬數據 (熱門股票建議)
TICKER_SUGGESTIONS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD", "META", "AMZN"] 

# 初始化 Flask 應用
app = Flask(__name__)
analyzer = GrowthSignalAnalyzer()
scanner = StockScanner()  # F3.1: 初始化股票掃描器

def initialize_database():
    """初始化數據庫，確保有推薦股票數據"""
    try:
        # 檢查是否有推薦股票
        recommended = scanner.get_recommended_stocks(limit=1)
        if not recommended:
            logging.info("數據庫中沒有推薦股票，執行初始掃描...")
            # 執行初始掃描
            initial_stocks = scanner.popular_stocks[:20]  # 掃描前20支熱門股票
            results = scanner.batch_scan_stocks(initial_stocks, max_stocks=20)
            logging.info(f"初始掃描完成，發現 {len(results)} 個形態")
        else:
            logging.info(f"數據庫中已有 {len(scanner.get_recommended_stocks(limit=10))} 支推薦股票")
    except Exception as e:
        logging.error(f"初始化數據庫失敗: {e}")

# 初始化數據庫
initialize_database()

# 初始化 AI 分析器和收藏功能
ai_enhanced_analyzer = None
news_analyzer = EnhancedNewsAnalyzer()
watchlist = Watchlist()

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
        # 如果沒有推薦股票，嘗試執行快速掃描
        if not recommended_stocks:
            logging.info("沒有推薦股票，執行快速掃描...")
            quick_stocks = scanner.popular_stocks[:10]  # 掃描前10支熱門股票
            scanner.batch_scan_stocks(quick_stocks, max_stocks=10)
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

# F3.4: 初始化數據庫API
@app.route('/api/initialize-database', methods=['POST'])
def initialize_database_endpoint():
    """初始化數據庫端點 - 為新用戶提供初始數據"""
    try:
        logging.info("執行數據庫初始化...")
        # 清理舊數據
        scanner.cleanup_old_patterns(days=0)  # 清理所有舊數據
        
        # 執行初始掃描
        initial_stocks = scanner.popular_stocks[:30]  # 掃描前30支熱門股票
        results = scanner.batch_scan_stocks(initial_stocks, max_stocks=30)
        
        # 獲取推薦股票
        recommended = scanner.get_recommended_stocks(limit=8)
        
        return jsonify({
            'success': True,
            'message': f'數據庫初始化完成，發現 {len(results)} 個形態',
            'recommended_count': len(recommended),
            'results': results
        })
    except Exception as e:
        logging.error(f"數據庫初始化失敗: {e}")
        return jsonify({
            'success': False,
            'message': f'初始化失敗: {str(e)}'
        }), 500

# F3.5: 止損建議API
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
        
        # 計算突破位
        breakout_price = analyzer.calculate_breakout_price(stock_data, False, False)
        
        # 最大損失百分比 (修正計算: 突破位 - 止損位 / 突破位)
        if breakout_price != "N/A" and isinstance(breakout_price, (int, float)):
            max_loss_pct = (breakout_price - suggested_stop_loss) / breakout_price * 100
        else:
            # 如果無法計算突破位，使用當前價格
            max_loss_pct = (current_price - suggested_stop_loss) / current_price * 100
        
        # 專業判斷
        if max_loss_pct <= 7:
            risk_judgment = "優秀"
            judgment_color = "success"
        elif max_loss_pct <= 10:
            risk_judgment = "可接受"
            judgment_color = "warning"
        else:
            risk_judgment = "風險過高"
            judgment_color = "danger"
        
        return jsonify({
            "success": True,
            "ticker": ticker.upper(),
            "current_price": round(current_price, 2),
            "suggested_stop_loss": round(suggested_stop_loss, 2),
            "support_level": round(support_level, 2),
            "breakout_price": breakout_price,
            "max_loss_percentage": round(max_loss_pct, 2),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "volatility": round(volatility, 3),
            "risk_judgment": risk_judgment,
            "judgment_color": judgment_color,
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
            latest_news = get_latest_news(ticker)
            return jsonify({
                **technical_result,
                "news_analysis": latest_news,
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
        latest_news = get_latest_news(ticker)
        return jsonify({
            "success": True,
            "news_analysis": latest_news,
            "ticker": ticker
        })
            
    except Exception as e:
        logging.error(f"新聞獲取失敗: {e}")
        return jsonify({"error": f"新聞獲取失敗: {str(e)}", "success": False})

# 新聞連結驗證路由
@app.route('/api/verify-news-links/<ticker>')
def verify_news_links(ticker):
    """驗證新聞連結的有效性"""
    try:
        import requests
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        def check_url(url, timeout=5):
            """檢查URL是否可訪問"""
            try:
                response = requests.head(url, timeout=timeout, allow_redirects=True)
                return {
                    'url': url,
                    'status_code': response.status_code,
                    'accessible': response.status_code < 400,
                    'final_url': response.url,
                    'response_time': time.time()
                }
            except Exception as e:
                return {
                    'url': url,
                    'status_code': None,
                    'accessible': False,
                    'error': str(e),
                    'response_time': time.time()
                }
        
        # 獲取新聞數據
        news_result = asyncio.run(news_analyzer.comprehensive_analysis(ticker))
        
        if not news_result.get('news_analysis', {}).get('articles'):
            return jsonify({
                "success": True,
                "ticker": ticker,
                "verified_links": [],
                "message": "沒有找到新聞文章"
            })
        
        articles = news_result['news_analysis']['articles'][:5]  # 只驗證前5篇
        urls_to_check = [article.get('url') for article in articles if article.get('url') and article.get('url').startswith('http')]
        
        if not urls_to_check:
            return jsonify({
                "success": True,
                "ticker": ticker,
                "verified_links": [],
                "message": "沒有找到有效的URL"
            })
        
        # 並行檢查URL
        with ThreadPoolExecutor(max_workers=3) as executor:
            verification_results = list(executor.map(check_url, urls_to_check))
        
        # 統計結果
        accessible_count = sum(1 for result in verification_results if result['accessible'])
        total_count = len(verification_results)
        
        return jsonify({
            "success": True,
            "ticker": ticker,
            "verified_links": verification_results,
            "summary": {
                "total_links": total_count,
                "accessible_links": accessible_count,
                "success_rate": round((accessible_count / total_count) * 100, 1) if total_count > 0 else 0
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"新聞連結驗證失敗: {e}")
        return jsonify({"error": f"新聞連結驗證失敗: {str(e)}", "success": False})

# 新聞更新路由
@app.route('/api/refresh-news/<ticker>')
def refresh_news(ticker):
    """刷新股票新聞數據"""
    try:
        latest_news = get_latest_news(ticker)
        
        return jsonify({
            "success": True,
            "ticker": ticker,
            "news_data": {
                "news_analysis": latest_news
            },
            "message": f"已刷新 {ticker} 的新聞數據，找到 {latest_news['news_count']} 篇最新新聞",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"刷新新聞失敗: {e}")
        return jsonify({"error": f"刷新新聞失敗: {str(e)}", "success": False})

# 收藏列表API端點
@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """獲取收藏列表"""
    try:
        watchlist_data = watchlist.get_watchlist()
        return jsonify({
            "success": True,
            "watchlist": watchlist_data
        })
    except Exception as e:
        logging.error(f"獲取收藏列表失敗: {e}")
        return jsonify({"error": f"獲取收藏列表失敗: {str(e)}", "success": False})

@app.route('/api/watchlist/<ticker>', methods=['POST'])
def add_to_watchlist(ticker):
    """添加股票到收藏列表"""
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '收藏股票')
        
        success = watchlist.add_stock(ticker.upper(), notes)
        if success:
            return jsonify({
                "success": True,
                "message": f"已添加 {ticker.upper()} 到收藏列表"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"{ticker.upper()} 已在收藏列表中"
            })
    except Exception as e:
        logging.error(f"添加收藏失敗: {e}")
        return jsonify({"error": f"添加收藏失敗: {str(e)}", "success": False})

@app.route('/api/watchlist/<ticker>', methods=['DELETE'])
def remove_from_watchlist(ticker):
    """從收藏列表移除股票"""
    try:
        success = watchlist.remove_stock(ticker.upper())
        if success:
            return jsonify({
                "success": True,
                "message": f"已從收藏列表移除 {ticker.upper()}"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"{ticker.upper()} 不在收藏列表中"
            })
    except Exception as e:
        logging.error(f"移除收藏失敗: {e}")
        return jsonify({"error": f"移除收藏失敗: {str(e)}", "success": False})

if __name__ == '__main__':
    logging.info("啟動股票分析服務...")
    app.run(debug=FLASK_DEBUG, port=FLASK_PORT)