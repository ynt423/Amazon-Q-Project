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
        
        # 增強形態檢測
        enhanced_vcp_detected, enhanced_vcp_status, enhanced_vcp_details = self.detect_enhanced_vcp(data)
        cup_handle_detected, cup_handle_status = self.detect_cup_handle_pattern(data)
        
        # 合併形態檢測結果
        all_patterns = []
        if vcp_detected:
            all_patterns.append(f"VCP: {vcp_status}")
        if enhanced_vcp_detected:
            all_patterns.append(f"Enhanced VCP: {enhanced_vcp_status}")
        if cup_handle_detected:
            all_patterns.append(f"Cup & Handle: {cup_handle_status}")
        
        pattern_summary = "; ".join(all_patterns) if all_patterns else "未發現形態"

        scores_dict = {
            "RS_RATING": rs_score if rs_score is not None else 50,
            "RSI_SCORE": rsi_score if rsi_score is not None else 50,
            "MACD_SCORE": macd_score if macd_score is not None else 50,
            "BB_SCORE": bb_score if bb_score is not None else 50,
            "VOLUME_OK": volume_ok_score if volume_ok_score is not None else 50,
            "TREND_FILTER": trend_score if trend_score is not None else 50
        }

        # 3. 綜合評分
        final_score = self._calculate_final_score(
            scores_dict, vcp_detected, cup_handle_detected
        )
        
        # 確保分數不為 None
        if final_score is None:
            final_score = 50
        
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
            "scores_breakdown": {k: round(v if v is not None else 0, 2) for k, v in scores_dict.items()},
            "rs_rating": round(rs_score / (WEIGHTS["RS_RATING"] / 100), 1) if rs_score is not None else 50, # 反推原始 RS 1-99 分數
            "rsi": round(rsi_value, 1) if rsi_value is not None else 50,
            "macd": round(macd_value, 2) if macd_value is not None else 0,
            "signal": round(signal_value, 2) if signal_value is not None else 0,
            # 必須強制轉換為 Python 標準 bool 型別，解決 JSON 序列化錯誤
            "vcp_detected": bool(vcp_detected),
            "vcp_status": vcp_status,
            "pattern_summary": pattern_summary,
            "enhanced_vcp_detected": bool(enhanced_vcp_detected),
            "enhanced_vcp_status": enhanced_vcp_status,
            "cup_handle_detected": bool(cup_handle_detected),
            "cup_handle_status": cup_handle_status,
            "market_trend": trend_status,
            "recommended_stop_loss": round(stop_loss_price, 2) if stop_loss_price is not None and stop_loss_price != "N/A" else "N/A",
            "chart_data": chart_data,
            "success": True
        }
    
    
    def detect_enhanced_vcp(self, data, lookback=60):
        """增強版 VCP 形態檢測"""
        try:
            if len(data) < lookback:
                return False, "數據不足", {}
            
            recent_data = data.tail(lookback)
            close_prices = recent_data['Close']
            returns = close_prices.pct_change().dropna()
            
            # 滾動波動率 (20日)
            volatility = returns.rolling(window=20).std()
            
            # 檢查波動率收縮趨勢
            vol_trend = volatility.tail(40)
            if len(vol_trend) >= 20:
                recent_vol = vol_trend.tail(10).mean()
                earlier_vol = vol_trend.head(10).mean()
                vol_contraction = (earlier_vol - recent_vol) / earlier_vol if earlier_vol > 0 else 0
                
                # 價格整理檢查
                price_range = (close_prices.max() - close_prices.min()) / close_prices.mean()
                
                # 成交量分析
                volume_data = recent_data['Volume']
                recent_volume = volume_data.tail(10).mean()
                earlier_volume = volume_data.head(10).mean()
                volume_trend = recent_volume / earlier_volume if earlier_volume > 0 else 1
                
                vcp_score = 0
                criteria = {}
                
                # 波動率收縮 (40% 權重)
                if vol_contraction > 0.3:
                    vcp_score += 40
                    criteria['volatility_contraction'] = f"{vol_contraction:.1%}"
                
                # 價格整理 (30% 權重)
                if price_range < 0.15:  # 小於 15% 價格範圍
                    vcp_score += 30
                    criteria['price_consolidation'] = f"{price_range:.1%}"
                
                # 成交量下降 (20% 權重)
                if volume_trend < 0.8:
                    vcp_score += 20
                    criteria['volume_decline'] = f"{volume_trend:.1%}"
                
                # 時間因子 (10% 權重)
                if len(vol_trend) >= 30:
                    vcp_score += 10
                    criteria['sufficient_time'] = True
                
                detected = vcp_score >= 60
                status = "強烈信號" if vcp_score >= 80 else "潛在信號" if detected else "未發現"
                
                return detected, status, {
                    'score': vcp_score,
                    'criteria': criteria,
                    'volatility_contraction': vol_contraction,
                    'price_range': price_range,
                    'volume_trend': volume_trend
                }
            
            return False, "未發現", {}
        except Exception as e:
            return False, f"分析失敗: {str(e)}", {}
    
    def detect_cup_handle_pattern(self, data):
        """檢測 Cup and Handle 形態"""
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
        except Exception as e:
            return False, f"分析失敗: {str(e)}"
    
    def _calculate_final_score(self, scores_dict, vcp_detected, cup_handle_detected):
        """計算最終評分"""
        from config import WEIGHTS
        
        # 基礎分數計算
        base_score = 0
        for key, weight in WEIGHTS.items():
            if key in scores_dict:
                base_score += scores_dict[key] * (weight / 100)
        
        # 形態獎勵
        pattern_bonus = 0
        if vcp_detected:
            pattern_bonus += 10  # VCP 形態獎勵
        if cup_handle_detected:
            pattern_bonus += 8   # Cup & Handle 形態獎勵
        
        # 最終分數 (不超過100)
        final_score = min(100, base_score + pattern_bonus)
        
        return final_score
    
    def calculate_rs_rating(self, data, sp500_data):
        """計算 RS Rating (相對強度評級)"""
        try:
            if len(data) < 126 or len(sp500_data) < 126:  # 需要至少6個月數據
                return 50  # 默認中性評級
            
            # 取最近6個月數據
            stock_returns = data['Close'].pct_change().dropna()
            sp500_returns = sp500_data['Close'].pct_change().dropna()
            
            # 計算相對表現
            relative_performance = (stock_returns - sp500_returns).mean()
            
            # 轉換為1-99評級
            if relative_performance > 0.02:  # 2%以上超額收益
                rs_rating = min(99, 80 + (relative_performance - 0.02) * 1000)
            elif relative_performance > 0:  # 正超額收益
                rs_rating = 60 + (relative_performance / 0.02) * 20
            elif relative_performance > -0.02:  # 小幅負超額收益
                rs_rating = 40 + (relative_performance + 0.02) / 0.02 * 20
            else:  # 大幅負超額收益
                rs_rating = max(1, 40 + (relative_performance + 0.02) * 1000)
            
            return max(1, min(99, int(rs_rating)))
        except Exception as e:
            logging.error(f"RS Rating計算失敗: {e}")
            return 50
    
    def calculate_rsi_score(self, data):
        """計算 RSI 分數"""
        try:
            if len(data) < RSI_PERIOD + 1:
                return 50, 50
            
            # 計算RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_value = rsi.iloc[-1]
            
            # 轉換為分數 (0-100)
            if rsi_value >= 70:
                rsi_score = 20  # 超買，低分
            elif rsi_value >= 60:
                rsi_score = 40
            elif rsi_value >= 50:
                rsi_score = 60
            elif rsi_value >= 40:
                rsi_score = 80
            elif rsi_value >= 30:
                rsi_score = 60
            else:
                rsi_score = 40  # 超賣，中等分數
            
            return rsi_value, rsi_score
        except Exception as e:
            logging.error(f"RSI計算失敗: {e}")
            return 50, 50
    
    def calculate_macd_score(self, data):
        """計算 MACD 分數"""
        try:
            if len(data) < MACD_LONG_PERIOD + MACD_SIGNAL_PERIOD:
                return 0, 0, 50
            
            # 計算EMA
            ema_short = data['Close'].ewm(span=MACD_SHORT_PERIOD).mean()
            ema_long = data['Close'].ewm(span=MACD_LONG_PERIOD).mean()
            
            # 計算MACD線
            macd_line = ema_short - ema_long
            signal_line = macd_line.ewm(span=MACD_SIGNAL_PERIOD).mean()
            histogram = macd_line - signal_line
            
            macd_value = macd_line.iloc[-1]
            signal_value = signal_line.iloc[-1]
            
            # 計算分數
            if macd_value > signal_value and histogram.iloc[-1] > histogram.iloc[-2]:
                macd_score = 90  # 強勢上升
            elif macd_value > signal_value:
                macd_score = 70  # 上升趨勢
            elif macd_value > 0:
                macd_score = 60  # 中性偏多
            elif macd_value > signal_value:
                macd_score = 40  # 下降趨勢
            else:
                macd_score = 20  # 強勢下降
            
            return macd_value, signal_value, macd_score
        except Exception as e:
            logging.error(f"MACD計算失敗: {e}")
            return 0, 0, 50
    
    def calculate_bb_score(self, data):
        """計算布林帶分數"""
        try:
            if len(data) < BB_PERIOD:
                return 50
            
            # 計算布林帶
            sma = data['Close'].rolling(window=BB_PERIOD).mean()
            std = data['Close'].rolling(window=BB_PERIOD).std()
            upper_band = sma + (std * BB_STD_DEV)
            lower_band = sma - (std * BB_STD_DEV)
            
            current_price = data['Close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # 計算位置分數
            if current_price >= current_upper:
                bb_score = 20  # 超買
            elif current_price <= current_lower:
                bb_score = 80  # 超賣，可能反彈
            else:
                # 在帶內，計算相對位置
                position = (current_price - current_lower) / (current_upper - current_lower)
                bb_score = 60 + (position - 0.5) * 40  # 50-90分範圍
            
            return max(10, min(90, bb_score))
        except Exception as e:
            logging.error(f"布林帶計算失敗: {e}")
            return 50
    
    def check_volume_confirmation(self, data):
        """檢查成交量確認"""
        try:
            if len(data) < 20:
                return 50, "數據不足"
            
            # 計算成交量移動平均
            volume_ma = data['Volume'].rolling(window=20).mean()
            recent_volume = data['Volume'].iloc[-5:].mean()  # 最近5天平均
            avg_volume = volume_ma.iloc[-1]
            
            # 計算成交量比率
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # 價格變化
            price_change = (data['Close'].iloc[-1] - data['Close'].iloc[-5]) / data['Close'].iloc[-5]
            
            # 成交量確認邏輯
            if volume_ratio > 1.5 and price_change > 0:
                return 90, "強勢放量上漲"
            elif volume_ratio > 1.2 and price_change > 0:
                return 70, "溫和放量上漲"
            elif volume_ratio > 1.0:
                return 60, "成交量正常"
            elif volume_ratio > 0.8:
                return 40, "成交量偏低"
            else:
                return 20, "成交量不足"
        except Exception as e:
            logging.error(f"成交量檢查失敗: {e}")
            return 50, "檢查失敗"
    
    def check_market_trend(self, sp500_data):
        """檢查大盤趨勢"""
        try:
            if len(sp500_data) < 200:
                return True, 50, "數據不足"
            
            # 計算MA200
            ma200 = sp500_data['Close'].rolling(window=200).mean()
            current_price = sp500_data['Close'].iloc[-1]
            current_ma200 = ma200.iloc[-1]
            
            # 趨勢判斷
            if current_price > current_ma200 * 1.05:  # 5%以上
                return True, 90, "強勢上升趨勢"
            elif current_price > current_ma200:
                return True, 70, "上升趨勢"
            elif current_price > current_ma200 * 0.95:  # 5%以內
                return True, 50, "震盪趨勢"
            else:
                return False, 30, "下降趨勢"
        except Exception as e:
            logging.error(f"大盤趨勢檢查失敗: {e}")
            return True, 50, "檢查失敗"
    
    def detect_vcp_pattern(self, data):
        """檢測 VCP 形態"""
        try:
            if len(data) < 60:  # 需要至少3個月數據
                return False, "數據不足", None
            
            # 取最近3個月數據
            recent_data = data.tail(60)
            prices = recent_data['Close']
            volumes = recent_data['Volume']
            
            # 計算波動率
            returns = prices.pct_change().dropna()
            volatility = returns.rolling(window=10).std()
            
            # 檢查波動率收縮
            recent_vol = volatility.iloc[-10:].mean()
            early_vol = volatility.iloc[:10].mean()
            vol_contraction = (early_vol - recent_vol) / early_vol if early_vol > 0 else 0
            
            # 檢查價格整理
            price_range = (prices.max() - prices.min()) / prices.mean()
            
            # 檢查成交量下降
            recent_volume = volumes.iloc[-10:].mean()
            early_volume = volumes.iloc[:10].mean()
            volume_decline = (early_volume - recent_volume) / early_volume if early_volume > 0 else 0
            
            # VCP 判斷條件
            if vol_contraction > 0.2 and price_range < 0.2 and volume_decline > 0.1:
                # 計算建議止損點
                stop_loss = prices.min() * 0.95  # 最低價的95%
                return True, "VCP形態確認", stop_loss
            elif vol_contraction > 0.1 and price_range < 0.3:
                return True, "潛在VCP形態", prices.min() * 0.95
            else:
                return False, "未發現VCP", None
        except Exception as e:
            logging.error(f"VCP檢測失敗: {e}")
            return False, "檢測失敗", None
    
    def prepare_chart_data(self, data):
        """準備圖表數據"""
        try:
            if data is None or len(data) < 20:
                return None
            
            # 計算技術指標
            ma20 = data['Close'].rolling(window=20).mean()
            ma50 = data['Close'].rolling(window=50).mean()
            
            # 布林帶
            bb_period = 20
            bb_std = 2
            sma = data['Close'].rolling(window=bb_period).mean()
            std = data['Close'].rolling(window=bb_period).std()
            bb_upper = sma + (std * bb_std)
            bb_lower = sma - (std * bb_std)
            
            # 準備數據，處理 NaN 值
            def clean_nan_values(series):
                """將 NaN 值替換為 None，以便 JSON 序列化"""
                return [None if pd.isna(x) else float(x) for x in series]
            
            chart_data = {
                'dates': data.index.strftime('%Y-%m-%d').tolist(),
                'close': clean_nan_values(data['Close']),
                'volume': clean_nan_values(data['Volume']),
                'ma20': clean_nan_values(ma20),
                'ma50': clean_nan_values(ma50),
                'bb_upper': clean_nan_values(bb_upper),
                'bb_lower': clean_nan_values(bb_lower),
                'bb_middle': clean_nan_values(sma)
            }
            
            return chart_data
        except Exception as e:
            logging.error(f"圖表數據準備失敗: {e}")
            return None