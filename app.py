from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

app = Flask(__name__)

class GrowthSignalGenerator:
    def __init__(self):
        self.sp500_ticker = "^GSPC"
    
    def get_stock_data(self, ticker, period="1y"):
        """獲取股票數據"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            return data
        except Exception as e:
            return None
    
    def calculate_rs_rating(self, ticker):
        """計算RS Rating (相對強度評級)"""
        try:
            # 獲取股票和S&P 500數據
            stock_data = self.get_stock_data(ticker, "6mo")
            sp500_data = self.get_stock_data(self.sp500_ticker, "6mo")
            
            if stock_data is None or sp500_data is None or len(stock_data) < 2 or len(sp500_data) < 2:
                return 50
            
            # 計算6個月價格變化
            stock_return = (stock_data['Close'].iloc[-1] / stock_data['Close'].iloc[0] - 1) * 100
            sp500_return = (sp500_data['Close'].iloc[-1] / sp500_data['Close'].iloc[0] - 1) * 100
            
            # 相對表現
            relative_performance = stock_return - sp500_return
            
            print(f"股票回報: {stock_return:.2f}%, S&P500回報: {sp500_return:.2f}%, 相對表現: {relative_performance:.2f}%")
            
            # 改進的RS Rating算法
            if relative_performance >= 20:
                rs_rating = 90 + min(9, relative_performance - 20) // 5
            elif relative_performance >= 10:
                rs_rating = 80 + (relative_performance - 10)
            elif relative_performance >= 0:
                rs_rating = 60 + (relative_performance * 2)
            elif relative_performance >= -10:
                rs_rating = 40 + (relative_performance + 10) * 2
            else:
                rs_rating = max(1, 40 + relative_performance + 10)
            
            return max(1, min(99, int(rs_rating)))
        except Exception as e:
            print(f"RS Rating計算錯誤: {e}")
            return 50
    
    def calculate_rsi(self, data, period=14):
        """計算RSI指標"""
        try:
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]
            return 50 if pd.isna(rsi_value) else float(rsi_value)
        except:
            return 50
    
    def detect_vcp_pattern(self, data):
        """檢測VCP (Volatility Contraction Pattern) 形態"""
        try:
            if len(data) < 60:  # 需要至少3個月數據
                return False, "數據不足"
            
            # 取最近3個月數據
            recent_data = data.tail(60)
            
            # 計算波動率 (使用20日滾動標準差)
            volatility = recent_data['Close'].rolling(window=20).std()
            
            # 檢查波動率是否呈收縮趨勢
            vol_trend = volatility.tail(40)
            
            # 簡化邏輯：檢查最近的波動率是否小於前期
            if len(vol_trend) >= 20:
                recent_vol = vol_trend.tail(10).mean()
                earlier_vol = vol_trend.head(10).mean()
                
                if recent_vol < earlier_vol * 0.7:  # 波動率收縮30%以上
                    return True, "潛在突破中"
            
            return False, "未發現"
        except:
            return False, "分析失敗"
    
    def detect_cup_handle_pattern(self, data):
        """檢測Cup and Handle形態"""
        try:
            if len(data) < 120:  # 需要至少6個月數據
                return False, "數據不足"
            
            # 取最近6個月數據
            recent_data = data.tail(120)
            prices = recent_data['Close']
            
            # 尋找最高點和最低點
            max_price = prices.max()
            min_price = prices.min()
            
            # 檢查是否形成U形底部
            max_idx = prices.idxmax()
            min_idx = prices.idxmin()
            
            # 簡化邏輯：檢查價格是否從低點回升
            if min_idx < max_idx:  # 最低點在最高點之前
                recent_price = prices.iloc[-1]
                recovery_ratio = (recent_price - min_price) / (max_price - min_price)
                
                if recovery_ratio > 0.6:  # 已回升60%以上
                    return True, "突破在即"
            
            return False, "未發現"
        except:
            return False, "分析失敗"
    
    def generate_signal(self, ticker):
        """生成綜合信號"""
        try:
            print(f"開始獲取 {ticker} 的數據...")  # 調試信息
            # 獲取數據
            data = self.get_stock_data(ticker, "1y")
            if data is None or len(data) < 30:
                return {
                    "error": "無法獲取股票數據或數據不足",
                    "ticker": ticker,
                    "success": False
                }
            
            # 計算各項指標
            rs_rating = self.calculate_rs_rating(ticker)
            rsi = self.calculate_rsi(data)
            vcp_detected, vcp_status = self.detect_vcp_pattern(data)
            cup_handle_detected, cup_handle_status = self.detect_cup_handle_pattern(data)
            
            # 調試信息
            print(f"RS Rating: {rs_rating}, RSI: {rsi}")
            print(f"VCP: {vcp_detected}, Cup&Handle: {cup_handle_detected}")
            
            # 修正評分算法
            # RS Rating 權重 50%
            rs_score = rs_rating * 0.5
            
            # RSI 權重 50% (RSI在30-70之間得分較高)
            if 30 <= rsi <= 70:
                rsi_score = 50 - abs(rsi - 50)  # RSI接近50分數最高
            elif rsi > 70:
                rsi_score = max(0, 50 - (rsi - 70) * 2)  # 超買懲罰
            else:
                rsi_score = max(0, 50 - (30 - rsi) * 2)  # 超賣懲罰
            
            base_score = rs_score + rsi_score
            
            # 形態獎勵
            pattern_bonus = 0
            if vcp_detected:
                pattern_bonus += 10
            if cup_handle_detected:
                pattern_bonus += 8
            
            # 最終分數
            final_score = min(100, max(0, base_score + pattern_bonus))
            
            print(f"基礎分數: {base_score}, 形態獎勵: {pattern_bonus}, 最終分數: {final_score}")
            
            # 操作建議
            if final_score >= 80:
                advice = "Strong Buy"
                advice_color = "success"
            elif final_score >= 60:
                advice = "Hold"
                advice_color = "warning"
            else:
                advice = "Avoid"
                advice_color = "danger"
            
            # 準備圖表數據
            chart_data = self.prepare_chart_data(data.tail(120))  # 最近6個月
            
            return {
                "ticker": ticker.upper(),
                "final_score": round(final_score, 1),
                "advice": advice,
                "advice_color": advice_color,
                "rs_rating": rs_rating,
                "rsi": round(rsi, 1),
                "vcp_detected": vcp_detected,
                "vcp_status": vcp_status,
                "cup_handle_detected": cup_handle_detected,
                "cup_handle_status": cup_handle_status,
                "chart_data": chart_data,
                "success": True
            }
        except Exception as e:
            print(f"分析錯誤: {str(e)}")  # 調試信息
            return {
                "error": f"分析過程中發生錯誤: {str(e)}",
                "ticker": ticker,
                "success": False
            }
    
    def prepare_chart_data(self, data):
        """準備圖表數據"""
        try:
            # 創建數據副本並計算MA20
            data = data.copy()
            data['MA20'] = data['Close'].rolling(window=20).mean()
            
            # 處理NaN值
            chart_data = {
                "dates": [d.strftime('%Y-%m-%d') for d in data.index],
                "open": [None if pd.isna(x) else float(x) for x in data['Open']],
                "high": [None if pd.isna(x) else float(x) for x in data['High']],
                "low": [None if pd.isna(x) else float(x) for x in data['Low']],
                "close": [None if pd.isna(x) else float(x) for x in data['Close']],
                "ma20": [None if pd.isna(x) else float(x) for x in data['MA20']]
            }
            return chart_data
        except Exception as e:
            print(f"圖表數據準備錯誤: {e}")
            return {}

# 初始化信號生成器
signal_generator = GrowthSignalGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signal/generate', methods=['POST'])
def generate_signal():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "無效的請求數據", "success": False})
            
        ticker = data.get('ticker', '').strip().upper()
        
        if not ticker:
            return jsonify({"error": "請輸入股票代號", "success": False})
        
        print(f"正在分析股票: {ticker}")  # 調試信息
        result = signal_generator.generate_signal(ticker)
        print(f"分析結果: {result.get('success', False)}")  # 調試信息
        
        return jsonify(result)
    
    except Exception as e:
        print(f"服務器錯誤: {str(e)}")  # 調試信息
        return jsonify({"error": f"服務器錯誤: {str(e)}", "success": False})

if __name__ == '__main__':
    app.run(debug=True, port=5000)