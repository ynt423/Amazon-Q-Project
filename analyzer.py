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
    
    def calculate_keltner_channels(self, data, period=20, multiplier=2):
        """計算肯特納通道 (Keltner Channels) 指標"""
        try:
            # 計算EMA作為中線
            ema = data['Close'].ewm(span=period).mean()
            
            # 計算ATR (Average True Range)
            high_low = data['High'] - data['Low']
            high_close = np.abs(data['High'] - data['Close'].shift())
            low_close = np.abs(data['Low'] - data['Close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean()
            
            # 計算上下軌
            upper_channel = ema + (multiplier * atr)
            lower_channel = ema - (multiplier * atr)
            
            return {
                'basis': ema,
                'upper': upper_channel,
                'lower': lower_channel,
                'atr': atr
            }
        except Exception as e:
            logging.warning(f"KC 計算錯誤: {e}")
            return None
    
    def analyze_keltner_signals(self, data, kc_data):
        """分析肯特納通道信號"""
        try:
            if kc_data is None:
                return "無法計算", 50, "neutral"
            
            current_price = data['Close'].iloc[-1]
            upper = kc_data['upper'].iloc[-1]
            lower = kc_data['lower'].iloc[-1]
            basis = kc_data['basis'].iloc[-1]
            
            # 檢查通道寬度 (波動性)
            channel_width = (upper - lower) / basis
            is_contracting = channel_width < 0.04  # 通道收窄
            is_expanding = channel_width > 0.12    # 通道擴張
            
            # 判斷趨勢和信號
            if current_price > upper:
                signal = "突破上軌 - 強勢上漲"
                strategy = "strong_bullish"
                score = 85
                if is_contracting:
                    signal += " (低波動突破)"
                    score += 10
            elif current_price < lower:
                signal = "跌破下軌 - 超賣反彈機會"
                strategy = "oversold_opportunity"
                score = 25
                if is_contracting:
                    signal += " (低波動超賣)"
                    score += 15  # 超賣反彈機會更大
            elif current_price > basis:
                if is_contracting:
                    signal = "中軌上方 - 整理待突破"
                    strategy = "consolidation_bullish"
                    score = 75
                else:
                    signal = "中軌上方 - 多頭趨勢"
                    strategy = "bullish_trend"
                    score = 70
            else:
                if is_contracting:
                    signal = "中軌下方 - 整理觀望"
                    strategy = "consolidation_bearish"
                    score = 45
                else:
                    signal = "中軌下方 - 空頭趨勢"
                    strategy = "bearish_trend"
                    score = 40
            
            # 高波動性懲罰
            if is_expanding:
                signal += " (高波動性)"
                score -= 5
            
            return signal, min(100, max(0, score)), strategy
        except Exception as e:
            logging.warning(f"KC 信號分析錯誤: {e}")
            return "分析失敗", 50, "neutral"
    
    def get_kc_strategy_recommendation(self, kc_strategy, vcp_detected, rs_rating, final_score):
        """根據KC策略給出建議"""
        recommendations = {
            "strong_bullish": {
                "action": "📈 強勢買入信號",
                "description": "KC上軌突破 + 強勢動能",
                "color": "success"
            },
            "consolidation_bullish": {
                "action": "⏳ 整理待突破",
                "description": "KC通道收窄 + 價格在中軌上方",
                "color": "warning"
            },
            "bullish_trend": {
                "action": "📈 多頭趨勢持續",
                "description": "價格在KC中軌上方運行",
                "color": "info"
            },
            "oversold_opportunity": {
                "action": "💰 超賣反彈機會",
                "description": "KC下軌超賣 + 潛在反彈",
                "color": "primary"
            },
            "consolidation_bearish": {
                "action": "⏳ 觀望為主",
                "description": "價格在KC中軌下方整理",
                "color": "secondary"
            },
            "bearish_trend": {
                "action": "📉 空頭趨勢警告",
                "description": "價格在KC中軌下方運行",
                "color": "danger"
            },
            "neutral": {
                "action": "⏳ 中性觀望",
                "description": "KC指標無明確信號",
                "color": "secondary"
            }
        }
        
        base_rec = recommendations.get(kc_strategy, recommendations["neutral"])
        
        # 結合VCP和RS Rating增強建議
        if kc_strategy == "strong_bullish" and vcp_detected and rs_rating > 80:
            base_rec["action"] = "🚀 最佳買入機會"
            base_rec["description"] += " + VCP形態 + 高RS評級"
        elif kc_strategy == "consolidation_bullish" and vcp_detected:
            base_rec["action"] = "🎯 突破在即"
            base_rec["description"] += " + VCP形態確認"
        
        return base_rec


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
        
        # 計算肯特納通道指標
        kc_data = self.calculate_keltner_channels(data)
        kc_signal, kc_score, kc_strategy = self.analyze_keltner_signals(data, kc_data)
        
        volume_ok_score, volume_status = self.check_volume_confirmation(data)
        trend_ok, trend_score, trend_status = self.check_market_trend(data_sp500)
        
        # 形態檢測 (VCP 止損位)
        vcp_detected, vcp_status, stop_loss_price = self.detect_vcp_pattern(data)
        
        # 增強形態檢測
        enhanced_vcp_detected, enhanced_vcp_status, enhanced_vcp_details = self.detect_enhanced_vcp(data)
        cup_handle_detected, cup_handle_status = self.detect_cup_handle_pattern(data)
        
        # 合併形態檢測結果，統一VCP檢測結果
        all_patterns = []
        final_vcp_detected = vcp_detected or enhanced_vcp_detected
        if final_vcp_detected:
            if vcp_detected and enhanced_vcp_detected:
                all_patterns.append(f"VCP: {vcp_status} + {enhanced_vcp_status}")
            elif enhanced_vcp_detected:
                all_patterns.append(f"VCP: {enhanced_vcp_status}")
            else:
                all_patterns.append(f"VCP: {vcp_status}")
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
        
        # 計算突破位
        breakout_price = self.calculate_breakout_price(data, final_vcp_detected, cup_handle_detected)
        
        # KC策略建議
        kc_recommendation = self.get_kc_strategy_recommendation(
            kc_strategy, 
            final_vcp_detected, 
            rs_score/(WEIGHTS["RS_RATING"]/100) if rs_score else 50, 
            final_score
        )
        
        # 準備圖表數據
        chart_data = self.prepare_chart_data(data)
        
        # 計算缺失的數值
        current_price = data['Close'].iloc[-1]
        
        # 計算支撐位 (最近20日最低點)
        support_level = data['Low'].tail(20).min()
        
        # 計算年化波動率
        returns = data['Close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5) if len(returns) > 0 else 0.25
        
        # 如果沒有止損價，使用支撐位下方3%
        if stop_loss_price == "N/A" or stop_loss_price is None:
            stop_loss_price = support_level * 0.97
        
        # 檢查成交量狀態
        volume_ok = volume_ok_score > 0
        
        return {
            "ticker": ticker.upper(),
            "current_price": round(current_price, 2),
            "final_score": round(final_score, 1),
            "advice": advice,
            "advice_color": advice_color,
            "scores_breakdown": {k: round(v if v is not None else 0, 2) for k, v in scores_dict.items()},
            "rs_rating": round(rs_score / (WEIGHTS["RS_RATING"] / 100), 1) if rs_score is not None else 50,
            "rsi": round(rsi_value, 1) if rsi_value is not None else 50,
            "macd": round(macd_value, 2) if macd_value is not None else 0,
            "signal": round(signal_value, 2) if signal_value is not None else 0,
            "kc_signal": kc_signal,
            "kc_score": round(kc_score, 1) if kc_score is not None else 50,
            "kc_strategy": kc_strategy,
            "kc_recommendation": kc_recommendation,
            "vcp_detected": bool(final_vcp_detected),
            "vcp_status": vcp_status if vcp_detected else enhanced_vcp_status if enhanced_vcp_detected else "未發現",
            "pattern_summary": pattern_summary,
            "enhanced_vcp_detected": bool(enhanced_vcp_detected),
            "enhanced_vcp_status": enhanced_vcp_status,
            "cup_handle_detected": bool(cup_handle_detected),
            "cup_handle_status": cup_handle_status,
            "market_trend": trend_status,
            "support_level": round(support_level, 2),
            "recommended_stop_loss": round(stop_loss_price, 2) if isinstance(stop_loss_price, (int, float)) else round(support_level * 0.97, 2),
            "volatility": round(volatility, 3),
            "volume_ok": volume_ok,
            "chart_data": chart_data,
            "breakout_price": breakout_price,
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
                
                detected = vcp_score >= 40
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
    
    def calculate_breakout_price(self, data, vcp_detected, cup_handle_detected):
        """計算突破位 - 基於 William O'Neil 和 Mark Minervini 哲學"""
        try:
            current_price = data['Close'].iloc[-1]
            
            if vcp_detected:
                # VCP突破位: 最近30日最高價 + 2-3%
                recent_high = data['High'].tail(30).max()
                breakout_price = recent_high * 1.025  # 2.5%突破
                return round(breakout_price, 2)
            
            elif cup_handle_detected:
                # Cup & Handle突破位: 杯口最高價 + 1-2%
                cup_high = data['High'].tail(120).max()
                breakout_price = cup_high * 1.015  # 1.5%突破
                return round(breakout_price, 2)
            
            else:
                # 無形態: 使用20日最高價 + 3%
                resistance_level = data['High'].tail(20).max()
                breakout_price = resistance_level * 1.03
                return round(breakout_price, 2)
                
        except Exception as e:
            logging.error(f"突破位計算錯誤: {e}")
            return "N/A"
    
    def prepare_chart_data(self, data):
        """準備圖表數據"""
        try:
            if data is None or len(data) < 20:
                return None
            
            # 計算技術指標
            ma20 = data['Close'].rolling(window=20).mean()
            ma50 = data['Close'].rolling(window=50).mean()
            
            # 布林通道
            bb_period = 20
            bb_std = 2
            sma = data['Close'].rolling(window=bb_period).mean()
            std = data['Close'].rolling(window=bb_period).std()
            upper_band = sma + (std * bb_std)
            lower_band = sma - (std * bb_std)
            
            # 肯特納通道
            kc_data = self.calculate_keltner_channels(data)
            kc_upper = kc_data['upper'] if kc_data else None
            kc_lower = kc_data['lower'] if kc_data else None
            kc_basis = kc_data['basis'] if kc_data else None
            
            # 處理 NaN 值，替換為 None 以便 JSON 序列化
            def clean_series(series):
                return [None if pd.isna(x) else x for x in series.tolist()]
            
            chart_data = {
                'dates': data.index.strftime('%Y-%m-%d').tolist(),
                'open': data['Open'].tolist(),
                'high': data['High'].tolist(),
                'low': data['Low'].tolist(),
                'close': data['Close'].tolist(),
                'volume': data['Volume'].tolist(),
                'ma20': clean_series(ma20),
                'ma50': clean_series(ma50),
                'bb_upper': clean_series(upper_band),
                'bb_lower': clean_series(lower_band),
                'kc_upper': clean_series(kc_upper) if kc_upper is not None else None,
                'kc_lower': clean_series(kc_lower) if kc_lower is not None else None,
                'kc_basis': clean_series(kc_basis) if kc_basis is not None else None
            }
            
            return chart_data
        except Exception as e:
            logging.error(f"圖表數據準備失敗: {e}")
            return None
