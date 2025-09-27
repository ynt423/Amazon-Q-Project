# analyzer.py

import yfinance as yf
import pandas as pd
import numpy as np
import logging
from functools import lru_cache
from config import SP500_TICKER, WEIGHTS, STOP_LOSS_PERCENTAGE
from config import RSI_PERIOD, MACD_SHORT_PERIOD, MACD_LONG_PERIOD, MACD_SIGNAL_PERIOD, BB_PERIOD, BB_STD_DEV

class GrowthSignalAnalyzer:
    
    def __init__(self):
        self.sp500_ticker = SP500_TICKER
    
    # S1.3: 使用 lru_cache 實現數據緩存
    @lru_cache(maxsize=32)
    def get_stock_data(self, ticker, period="1y", interval="1d"):
        """使用緩存機制獲取股票數據"""
        try:
            stock = yf.Ticker(ticker)
            # 根據週期和間隔下載數據
            data = stock.history(period=period, interval=interval)
            if data.empty:
                 raise ValueError(f"下載 {ticker} 的數據為空。")
            return data.copy() 
        except Exception as e:
            logging.error(f"獲取 {ticker} 數據失敗: {e}")
            return None

    def calculate_rs_rating(self, stock_data, sp500_data):
        """計算RS Rating (相對強度評級)"""
        try:
            # 使用 6 個月數據 (約 120 交易日)
            stock_data_6mo = stock_data['Close'].tail(120)
            sp500_data_6mo = sp500_data['Close'].tail(120)

            if len(stock_data_6mo) < 2 or len(sp500_data_6mo) < 2:
                return 50

            # 計算價格變化
            stock_return = (stock_data_6mo.iloc[-1] / stock_data_6mo.iloc[0] - 1) * 100
            sp500_return = (sp500_data_6mo.iloc[-1] / sp500_data_6mo.iloc[0] - 1) * 100
            relative_performance = stock_return - sp500_return
            
            # 評分邏輯 (保持原邏輯但納入新的加權)
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
            
            # 將 1-99 的分數按權重轉換
            return max(1, min(99, int(rs_rating))) * (WEIGHTS["RS_RATING"] / 100)
        except Exception as e:
            logging.warning(f"RS Rating 計算錯誤: {e}", exc_info=False)
            return 50 * (WEIGHTS["RS_RATING"] / 100)

    def calculate_rsi_score(self, data):
        """計算RSI指標並轉換為分數 (M2.2)"""
        try:
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(com=RSI_PERIOD - 1, min_periods=RSI_PERIOD).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]
            
            # 轉換為分數：接近 50 分數最高 (動量中性但穩定)
            if 40 <= rsi_value <= 70:
                # 接近 55 分數最高
                rsi_score = 100 - abs(rsi_value - 55) * 2
            elif rsi_value > 70: # 超買
                rsi_score = 50 - (rsi_value - 70) * 2
            else: # 超賣
                rsi_score = 50 - (40 - rsi_value) * 2
            
            rsi_score = max(0, min(100, rsi_score))
            return float(rsi_value), rsi_score * (WEIGHTS["RSI_SCORE"] / 100)
        except Exception as e:
            logging.warning(f"RSI 計算錯誤: {e}", exc_info=False)
            return 50, 50 * (WEIGHTS["RSI_SCORE"] / 100)

    def calculate_macd_score(self, data):
        """計算MACD指標並轉換為分數 (M2.1)"""
        try:
            exp1 = data['Close'].ewm(span=MACD_SHORT_PERIOD, adjust=False).mean()
            exp2 = data['Close'].ewm(span=MACD_LONG_PERIOD, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=MACD_SIGNAL_PERIOD, adjust=False).mean()
            
            macd_value = macd.iloc[-1]
            signal_value = signal.iloc[-1]
            
            # MACD 分數邏輯：MACD 線在信號線之上且兩者都在 0 之上得分高
            score = 0
            if macd_value > signal_value and macd_value > 0:
                score += 70 # 黃金交叉且處於強勢區
            elif macd_value > signal_value or macd_value > 0:
                score += 40 # 至少滿足一個條件
            
            # 考慮 MACD 柱狀圖 (Histogram) 擴大
            hist = macd - signal
            if hist.iloc[-1] > hist.iloc[-2]:
                score += 30 # 動量正在增強
            
            macd_score = max(0, min(100, score))
            return macd_value, signal_value, macd_score * (WEIGHTS["MACD_SCORE"] / 100)
        except Exception as e:
            logging.warning(f"MACD 計算錯誤: {e}", exc_info=False)
            return 0, 0, 50 * (WEIGHTS["MACD_SCORE"] / 100)

    def calculate_bb_score(self, data):
        """計算布林通道 (BB) 指標並轉換為分數 (M2.1, M2.4 風險)"""
        try:
            data['MA'] = data['Close'].rolling(window=BB_PERIOD).mean()
            data['STD'] = data['Close'].rolling(window=BB_PERIOD).std()
            data['Upper'] = data['MA'] + (data['STD'] * BB_STD_DEV)
            data['Lower'] = data['MA'] - (data['STD'] * BB_STD_DEV)
            
            current_close = data['Close'].iloc[-1]
            upper = data['Upper'].iloc[-1]
            lower = data['Lower'].iloc[-1]
            
            # BB 分數邏輯：價格在下軌附近得分低 (超賣)，在上軌附近得分低 (超買風險高)
            score = 50
            if current_close < lower:
                score = 10 # 處於極度超賣
            elif current_close > upper:
                score = 30 # 處於超買區，風險較高
            elif current_close > data['MA'].iloc[-1]:
                score = 70 # 價格在中軌之上，短期強勢
            else:
                score = 50 # 中性
                
            # 波動率分析 (M2.4): 波動率壓縮 (BB 帶寬變窄) 預示潛在突破，可給予獎勵
            band_width = (upper - lower) / data['MA'].iloc[-1]
            if band_width < 0.05: # 帶寬小於 5%
                score += 20
                
            bb_score = max(0, min(100, score))
            return bb_score * (WEIGHTS["BB_SCORE"] / 100)
        except Exception as e:
            logging.warning(f"BB 計算錯誤: {e}", exc_info=False)
            return 50 * (WEIGHTS["BB_SCORE"] / 100)


    def check_volume_confirmation(self, data, period=50, volume_multiplier=1.5):
        """檢查最近成交量是否強勁 (功能需求 #2)"""
        if len(data) < period:
            return 0.0, "數據不足"
            
        try:
            avg_volume = data['Volume'].iloc[:-1].tail(period).mean()
            current_volume = data['Volume'].iloc[-1]
            
            if current_volume > avg_volume * volume_multiplier:
                # 成交量確認給予全部分數
                return WEIGHTS["VOLUME_OK"], f"成交量放大 {current_volume/avg_volume:.1f}x"
            return 0.0, "成交量不足"
        except Exception as e:
            logging.error(f"成交量分析失敗: {e}", exc_info=False)
            return 0.0, "分析失敗"

    def detect_vcp_pattern(self, data):
        """檢測VCP形態 - 增加止損點 (M2.3)"""
        # 邏輯保持精簡但加入止損位
        if len(data) < 90:
            return False, "數據不足", "N/A"

        recent_data = data.tail(90).copy()
        
        volatility_current = recent_data['Close'].tail(30).std()
        volatility_earlier = recent_data['Close'].head(30).std()
        
        is_contracting = volatility_current < volatility_earlier * 0.7 
        recent_high = recent_data['High'].max()
        current_close = recent_data['Close'].iloc[-1]
        is_near_breakout = (recent_high - current_close) / current_close < 0.03

        vcp_detected = is_contracting and is_near_breakout
        
        status = "未發現"
        stop_loss_price = "N/A"

        if vcp_detected:
            status = "VCP 收縮且接近突破"
            # 止損點建議：設在最近 20 日低點下方 5% (功能需求 #3)
            stop_loss_price = recent_data['Low'].tail(20).min() * STOP_LOSS_PERCENTAGE
        
        return vcp_detected, status, stop_loss_price
    
    def check_market_trend(self, sp500_data):
        """檢查大盤趨勢 (功能需求 #4)"""
        if len(sp500_data) < 200:
            return True, 0.0, "數據不足，視為中性"

        sp500_data['MA200'] = sp500_data['Close'].rolling(window=200).mean()
        
        current_close = sp500_data['Close'].iloc[-1]
        ma200_value = sp500_data['MA200'].iloc[-1]
        
        trend_ok = False
        trend_score = 0.0
        trend_status = "中性市場 (Neutral)"

        if current_close > ma200_value * 1.05: # 在 MA200 之上 5%
            trend_ok = True
            trend_score = WEIGHTS["TREND_FILTER"] 
            trend_status = "強勢多頭 (Strong Bull)"
        elif current_close > ma200_value:
            trend_ok = True
            trend_score = WEIGHTS["TREND_FILTER"] * 0.5 # 弱多頭給一半分數
            trend_status = "多頭市場 (Bull Market)"
        elif current_close < ma200_value * 0.95:
            trend_ok = False
            trend_score = 0.0 
            trend_status = "空頭市場 (Bear Market)"
        
        return trend_ok, trend_score, trend_status
    
    def _calculate_final_score(self, scores_dict, vcp_detected, cup_handle_detected):
        """M2.2: 綜合評分邏輯 (解決 Strong Buy 偏見)"""
        
        # 基礎分數來自於所有指標的加權分數總和
        base_score = sum(scores_dict.values())
        
        # 形態獎勵 (M2.2)
        pattern_bonus = 0.0
        if vcp_detected:
            pattern_bonus += WEIGHTS["PATTERN_BONUS"] * 0.6 # VCP 權重高
        if cup_handle_detected:
            pattern_bonus += WEIGHTS["PATTERN_BONUS"] * 0.4
        
        final_score = base_score + pattern_bonus
        
        return min(100, max(0, final_score))

    def generate_signal(self, ticker, period, interval="1d"):
        """生成綜合信號"""
        
        # 1. 獲取數據
        data = self.get_stock_data(ticker, period=period, interval=interval)
        data_sp500 = self.get_stock_data(self.sp500_ticker, period="2y", interval="1d") # 大盤數據拉長週期確保 MA200 有數據

        if data is None or data_sp500 is None or len(data) < 30:
             return {
                "error": "無法獲取股票或大盤數據，請檢查代號或網路連線。",
                "ticker": ticker.upper(),
                "success": False
             }
        
        # 2. 計算各項指標和分數 (M2.2 修正)
        rs_score = self.calculate_rs_rating(data, data_sp500)
        rsi_value, rsi_score = self.calculate_rsi_score(data)
        macd_value, signal_value, macd_score = self.calculate_macd_score(data)
        bb_score = self.calculate_bb_score(data)
        
        volume_ok_score, volume_status = self.check_volume_confirmation(data)
        trend_ok, trend_score, trend_status = self.check_market_trend(data_sp500)
        
        # 形態檢測 (VCP 止損位)
        vcp_detected, vcp_status, stop_loss_price = self.detect_vcp_pattern(data)
        # 簡化 Cup and Handle 檢測
        cup_handle_detected, cup_handle_status = False, "未發現" # 暫時關閉，待 M2.3 實現嚴格邏輯

        scores_dict = {
            "RS_RATING": rs_score,
            "RSI_SCORE": rsi_score,
            "MACD_SCORE": macd_score,
            "BB_SCORE": bb_score,
            "VOLUME_OK": volume_ok_score,
            "TREND_FILTER": trend_score
        }

        # 3. 綜合評分
        final_score = self._calculate_final_score(
            scores_dict, vcp_detected, cup_handle_detected
        )
        
        # 4. 操作建議 (使用 config 閾值)
        from config import SCORE_STRONG_BUY, SCORE_HOLD
        if final_score >= SCORE_STRONG_BUY and trend_ok:
            advice = "Strong Buy (趨勢確認)"
            advice_color = "success"
        elif final_score >= SCORE_HOLD:
            advice = "Hold / Wait for Confirmation"
            advice_color = "warning"
        else:
            advice = "Avoid (風險高)"
            advice_color = "danger"
        
        # 準備圖表數據
        chart_data = self.prepare_chart_data(data)
        
        return {
            "ticker": ticker.upper(),
            "final_score": round(final_score, 1),
            "advice": advice,
            "advice_color": advice_color,
            "scores_breakdown": {k: round(v, 2) for k, v in scores_dict.items()},
            "rs_rating": round(rs_score / (WEIGHTS["RS_RATING"] / 100), 1), # 反推原始 RS 1-99 分數
            "rsi": round(rsi_value, 1),
            "macd": round(macd_value, 2),
            "signal": round(signal_value, 2),
            # 必須強制轉換為 Python 標準 bool 型別，解決 JSON 序列化錯誤
            "vcp_detected": bool(vcp_detected),
            "vcp_status": vcp_status,
            "market_trend": trend_status,
            "recommended_stop_loss": round(stop_loss_price, 2) if stop_loss_price != "N/A" else stop_loss_price,
            "chart_data": chart_data,
            "success": True
        }
    
    def prepare_chart_data(self, data):
        """準備圖表數據，新增 MA20/MA50"""
        try:
            data = data.copy()
            # 增加 MA50
            data['MA20'] = data['Close'].rolling(window=20).mean()
            data['MA50'] = data['Close'].rolling(window=50).mean()
            
            # 重新計算 BB 以供圖表顯示
            data['MA'] = data['Close'].rolling(window=BB_PERIOD).mean()
            data['STD'] = data['Close'].rolling(window=BB_PERIOD).std()
            data['Upper'] = data['MA'] + (data['STD'] * BB_STD_DEV)
            data['Lower'] = data['MA'] - (data['STD'] * BB_STD_DEV)

            chart_data = {
                "dates": [d.strftime('%Y-%m-%d') for d in data.index],
                "open": [None if pd.isna(x) else float(x) for x in data['Open']],
                "high": [None if pd.isna(x) else float(x) for x in data['High']],
                "low": [None if pd.isna(x) else float(x) for x in data['Low']],
                "close": [None if pd.isna(x) else float(x) for x in data['Close']],
                "ma20": [None if pd.isna(x) else float(x) for x in data['MA20']],
                "ma50": [None if pd.isna(x) else float(x) for x in data['MA50']],
                "bb_upper": [None if pd.isna(x) else float(x) for x in data['Upper']],
                "bb_lower": [None if pd.isna(x) else float(x) for x in data['Lower']]
            }
            return chart_data
        except Exception as e:
            logging.error(f"圖表數據準備錯誤: {e}", exc_info=False)
            return {}