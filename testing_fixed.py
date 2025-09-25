#!/usr/bin/env python3
"""
Fintech Evolution - 跨鏈投資組合管理平台 MVP (修復版)
技術指標選股 + Swing Trading形態識別 + 評分系統
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple, Optional
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
from io import BytesIO
import base64
warnings.filterwarnings('ignore')

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

class TechnicalAnalyzer:
    """技術指標計算引擎"""
    
    @staticmethod
    def safe_float(value) -> float:
        """安全轉換為float"""
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except:
            return 0.0
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast=12, slow=26, signal=9) -> Dict:
        """MACD指標計算"""
        try:
            if len(prices) < slow:
                return {'macd': 0, 'signal': 0, 'histogram': 0, 'bullish_crossover': False}
            
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            
            # 安全地獲取值
            current_macd = TechnicalAnalyzer.safe_float(macd_line.iloc[-1])
            current_signal = TechnicalAnalyzer.safe_float(signal_line.iloc[-1])
            current_histogram = TechnicalAnalyzer.safe_float(histogram.iloc[-1])
            
            # 檢查交叉信號
            bullish_crossover = False
            if len(macd_line) > 1:
                prev_macd = TechnicalAnalyzer.safe_float(macd_line.iloc[-2])
                prev_signal = TechnicalAnalyzer.safe_float(signal_line.iloc[-2])
                bullish_crossover = (current_macd > current_signal and prev_macd <= prev_signal)
            
            return {
                'macd': current_macd,
                'signal': current_signal,
                'histogram': current_histogram,
                'bullish_crossover': bullish_crossover
            }
        except Exception as e:
            print(f"MACD計算錯誤: {e}")
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'bullish_crossover': False}
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period=14) -> float:
        """RSI指標計算"""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # 避免除零錯誤
            loss = loss.replace(0, 0.0001)
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            result = TechnicalAnalyzer.safe_float(rsi.iloc[-1])
            return result if 0 <= result <= 100 else 50.0
            
        except Exception as e:
            print(f"RSI計算錯誤: {e}")
            return 50.0
    
    @staticmethod
    def calculate_moving_averages(prices: pd.Series) -> Dict:
        """移動平均線計算"""
        try:
            current_price = TechnicalAnalyzer.safe_float(prices.iloc[-1])
            
            ma20 = TechnicalAnalyzer.safe_float(prices.rolling(20).mean().iloc[-1]) if len(prices) >= 20 else current_price
            ma50 = TechnicalAnalyzer.safe_float(prices.rolling(50).mean().iloc[-1]) if len(prices) >= 50 else current_price
            ma200 = TechnicalAnalyzer.safe_float(prices.rolling(200).mean().iloc[-1]) if len(prices) >= 200 else current_price
            
            return {
                'ma20': ma20,
                'ma50': ma50,
                'ma200': ma200,
                'current_price': current_price
            }
        except Exception as e:
            print(f"移動平均計算錯誤: {e}")
            current_price = TechnicalAnalyzer.safe_float(prices.iloc[-1])
            return {
                'ma20': current_price,
                'ma50': current_price,
                'ma200': current_price,
                'current_price': current_price
            }

class PatternRecognizer:
    """Swing Trading形態識別"""
    
    @staticmethod
    def detect_vcp(prices: pd.Series, volumes: pd.Series) -> Dict:
        """VCP形態檢測"""
        try:
            if len(prices) < 20 or len(volumes) < 20:
                return {'is_vcp': False, 'confidence': 0.0, 'stage': 0}
            
            # 計算成交量收縮
            recent_periods = min(20, len(volumes))
            avg_periods = min(50, len(volumes))
            
            recent_vol = volumes.tail(recent_periods).mean()
            avg_vol = volumes.tail(avg_periods).mean()
            
            # 計算價格整理
            price_tail = prices.tail(recent_periods)
            price_high = price_tail.max()
            price_low = price_tail.min()
            price_mean = price_tail.mean()
            
            # 安全計算
            recent_vol_val = TechnicalAnalyzer.safe_float(recent_vol)
            avg_vol_val = TechnicalAnalyzer.safe_float(avg_vol)
            price_high_val = TechnicalAnalyzer.safe_float(price_high)
            price_low_val = TechnicalAnalyzer.safe_float(price_low)
            price_mean_val = TechnicalAnalyzer.safe_float(price_mean)
            
            price_range = (price_high_val - price_low_val) / price_mean_val if price_mean_val > 0 else 1.0
            
            volume_contraction = recent_vol_val < avg_vol_val * 0.8 if avg_vol_val > 0 else False
            tight_consolidation = price_range < 0.15
            
            is_vcp = volume_contraction and tight_consolidation
            
            return {
                'is_vcp': is_vcp,
                'confidence': 0.8 if is_vcp else 0.3,
                'stage': 3 if is_vcp else 1
            }
            
        except Exception as e:
            print(f"VCP檢測錯誤: {e}")
            return {'is_vcp': False, 'confidence': 0.0, 'stage': 0}
    
    @staticmethod
    def detect_breakout(prices: pd.Series, volumes: pd.Series) -> Dict:
        """突破形態檢測"""
        try:
            if len(prices) < 20 or len(volumes) < 20:
                return {'is_breakout': False, 'resistance_level': 0, 'volume_ratio': 1.0, 'strength': 0.0}
            
            # 計算阻力位
            lookback_periods = min(30, len(prices))
            resistance = TechnicalAnalyzer.safe_float(prices.tail(lookback_periods).quantile(0.9))
            current_price = TechnicalAnalyzer.safe_float(prices.iloc[-1])
            
            # 計算成交量
            vol_periods = min(20, len(volumes))
            avg_volume = TechnicalAnalyzer.safe_float(volumes.tail(vol_periods).mean())
            current_volume = TechnicalAnalyzer.safe_float(volumes.iloc[-1])
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_surge = volume_ratio > 1.5
            price_breakout = current_price > resistance if resistance > 0 else False
            
            is_breakout = price_breakout and volume_surge
            
            return {
                'is_breakout': is_breakout,
                'resistance_level': resistance,
                'volume_ratio': volume_ratio,
                'strength': 0.8 if is_breakout else 0.2
            }
            
        except Exception as e:
            print(f"突破檢測錯誤: {e}")
            return {'is_breakout': False, 'resistance_level': 0, 'volume_ratio': 1.0, 'strength': 0.0}

class RSRatingCalculator:
    """相對強度評級計算"""
    
    def __init__(self):
        self.sp500_symbol = '^GSPC'
    
    def calculate_rs_rating(self, symbol: str) -> Dict:
        """計算RS Rating"""
        try:
            # 獲取數據
            stock_data = yf.download(symbol, period='1y', progress=False)
            market_data = yf.download(self.sp500_symbol, period='1y', progress=False)
            
            if stock_data.empty or market_data.empty:
                return {'rs_rating': 50, 'relative_performance': 0, 'interpretation': '中性'}
            
            stock_prices = stock_data['Close']
            market_prices = market_data['Close']
            
            if len(stock_prices) < 63 or len(market_prices) < 63:
                return {'rs_rating': 50, 'relative_performance': 0, 'interpretation': '中性'}
            
            # 計算相對表現
            periods = [63, 126, 189, 252]
            rs_scores = []
            
            for period in periods:
                if len(stock_prices) >= period and len(market_prices) >= period:
                    stock_current = TechnicalAnalyzer.safe_float(stock_prices.iloc[-1])
                    stock_past = TechnicalAnalyzer.safe_float(stock_prices.iloc[-period])
                    market_current = TechnicalAnalyzer.safe_float(market_prices.iloc[-1])
                    market_past = TechnicalAnalyzer.safe_float(market_prices.iloc[-period])
                    
                    if stock_past > 0 and market_past > 0:
                        stock_return = (stock_current / stock_past - 1) * 100
                        market_return = (market_current / market_past - 1) * 100
                        relative_perf = stock_return - market_return
                        rs_scores.append(relative_perf)
            
            if not rs_scores:
                return {'rs_rating': 50, 'relative_performance': 0, 'interpretation': '中性'}
            
            # 加權計算
            weights = [0.4, 0.3, 0.2, 0.1][:len(rs_scores)]
            weighted_rs = sum(score * weight for score, weight in zip(rs_scores, weights))
            
            # 轉換為評級
            rs_rating = max(1, min(99, int(50 + weighted_rs * 0.5)))
            
            return {
                'rs_rating': rs_rating,
                'relative_performance': weighted_rs,
                'interpretation': self._interpret_rs(rs_rating)
            }
            
        except Exception as e:
            print(f"RS Rating計算錯誤 {symbol}: {e}")
            return {'rs_rating': 50, 'relative_performance': 0, 'interpretation': '中性'}
    
    def _interpret_rs(self, rating: int) -> str:
        """RS Rating解釋"""
        if rating >= 90: return "極強勢"
        elif rating >= 80: return "強勢"
        elif rating >= 70: return "中等偏強"
        elif rating >= 30: return "中性"
        else: return "弱勢"

class StockScorer:
    """股票評分系統"""
    
    def __init__(self):
        self.weights = {
            'rs_rating': 0.25,
            'technical': 0.25,
            'pattern': 0.25,
            'momentum': 0.25
        }
    
    def calculate_score(self, stock_data: Dict) -> Dict:
        """計算綜合評分"""
        try:
            scores = {
                'rs_rating': self._score_rs_rating(stock_data.get('rs_rating', {})),
                'technical': self._score_technical(stock_data.get('technical', {})),
                'pattern': self._score_pattern(stock_data.get('patterns', {})),
                'momentum': self._score_momentum(stock_data.get('momentum', {}))
            }
            
            # 加權總分
            total_score = sum(score * self.weights[key] for key, score in scores.items())
            total_score = max(0, min(100, total_score))  # 限制在0-100範圍
            
            return {
                'total_score': round(total_score, 2),
                'grade': self._get_grade(total_score),
                'breakdown': scores,
                'action': self._get_action(total_score, scores)
            }
        except Exception as e:
            print(f"評分計算錯誤: {e}")
            return {
                'total_score': 50.0,
                'grade': 'C',
                'breakdown': {'rs_rating': 50, 'technical': 50, 'pattern': 50, 'momentum': 50},
                'action': '觀望'
            }
    
    def _score_rs_rating(self, rs_data: Dict) -> float:
        """RS Rating評分"""
        rating = rs_data.get('rs_rating', 50)
        if rating >= 90: return 100
        elif rating >= 80: return 85
        elif rating >= 70: return 70
        elif rating >= 60: return 55
        else: return max(0, rating - 10)
    
    def _score_technical(self, tech_data: Dict) -> float:
        """技術指標評分"""
        score = 0
        
        # MACD評分
        macd = tech_data.get('macd', {})
        if macd.get('bullish_crossover'): score += 30
        elif macd.get('histogram', 0) > 0: score += 15
        
        # RSI評分
        rsi = tech_data.get('rsi', 50)
        if 30 < rsi < 70: score += 25
        elif 50 < rsi < 80: score += 15
        
        # 移動平均評分
        ma = tech_data.get('ma', {})
        price = ma.get('current_price', 0)
        ma20 = ma.get('ma20', 0)
        ma50 = ma.get('ma50', 0)
        
        if price > ma20 and ma20 > ma50 and price > 0: score += 25
        elif price > ma20 and price > 0: score += 15
        
        return min(score, 100)
    
    def _score_pattern(self, patterns: Dict) -> float:
        """形態評分"""
        score = 0
        
        vcp = patterns.get('vcp', {})
        if vcp.get('is_vcp'): 
            score += 40 * vcp.get('confidence', 0.5)
        
        breakout = patterns.get('breakout', {})
        if breakout.get('is_breakout'):
            score += 30 * breakout.get('strength', 0.5)
        
        return min(score, 100)
    
    def _score_momentum(self, momentum: Dict) -> float:
        """動量評分"""
        rsi = momentum.get('rsi', 50)
        if 50 < rsi < 80: return 80
        elif 40 < rsi < 90: return 60
        else: return 30
    
    def _get_grade(self, score: float) -> str:
        """評級轉換"""
        if score >= 80: return 'A+'
        elif score >= 70: return 'A'
        elif score >= 60: return 'B+'
        elif score >= 50: return 'B'
        elif score >= 40: return 'C'
        else: return 'D'
    
    def _get_action(self, total_score: float, scores: Dict) -> str:
        """操作建議"""
        if total_score >= 75 and scores['rs_rating'] > 70:
            return "強烈買入"
        elif total_score >= 60:
            return "考慮買入"
        elif total_score >= 40:
            return "觀望"
        else:
            return "避免"

class FinTechMVP:
    """跨鏈投資組合管理平台 MVP"""
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.rs_calculator = RSRatingCalculator()
        self.scorer = StockScorer()
    
    def analyze_stock(self, symbol: str) -> Dict:
        """完整股票分析"""
        try:
            print(f"正在分析 {symbol}...")
            
            # 獲取數據
            data = yf.download(symbol, period='1y', progress=False)
            if data.empty:
                return {'error': f'無法獲取 {symbol} 數據'}
            
            prices = data['Close']
            volumes = data['Volume']
            
            if len(prices) < 10:
                return {'error': f'{symbol} 數據不足'}
            
            # 技術指標分析
            macd = self.technical_analyzer.calculate_macd(prices)
            rsi = self.technical_analyzer.calculate_rsi(prices)
            ma = self.technical_analyzer.calculate_moving_averages(prices)
            
            # 形態識別
            vcp = self.pattern_recognizer.detect_vcp(prices, volumes)
            breakout = self.pattern_recognizer.detect_breakout(prices, volumes)
            
            # RS Rating
            rs_rating = self.rs_calculator.calculate_rs_rating(symbol)
            
            # 整合數據
            stock_data = {
                'symbol': symbol,
                'current_price': TechnicalAnalyzer.safe_float(prices.iloc[-1]),
                'rs_rating': rs_rating,
                'technical': {
                    'macd': macd,
                    'rsi': rsi,
                    'ma': ma
                },
                'patterns': {
                    'vcp': vcp,
                    'breakout': breakout
                },
                'momentum': {'rsi': rsi}
            }
            
            # 計算評分
            score_result = self.scorer.calculate_score(stock_data)
            stock_data['score'] = score_result
            
            return stock_data
            
        except Exception as e:
            return {'error': f'分析 {symbol} 時發生錯誤: {str(e)}'}
    
    def screen_stocks(self, symbols: List[str]) -> List[Dict]:
        """批量選股分析"""
        results = []
        
        for symbol in symbols:
            result = self.analyze_stock(symbol)
            if 'error' not in result:
                results.append(result)
            else:
                print(f"跳過 {symbol}: {result['error']}")
        

    
    def create_stock_chart(self, symbol: str, analysis_result: Dict) -> None:
        """創建股票技術分析圖表"""
        try:
            # 獲取更多數據用於繪圖
            data = yf.download(symbol, period='6mo', progress=False)
            if data.empty:
                print(f"無法獲取 {symbol} 圖表數據")
                return
            
            # 創建子圖
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), 
                                               gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # 主圖：價格和移動平均線
            ax1.plot(data.index, data['Close'], label=f'{symbol} 收盤價', linewidth=2, color='black')
            
            # 移動平均線
            if len(data) >= 20:
                ma20 = data['Close'].rolling(20).mean()
                ax1.plot(data.index, ma20, label='MA20', alpha=0.7, color='blue')
            
            if len(data) >= 50:
                ma50 = data['Close'].rolling(50).mean()
                ax1.plot(data.index, ma50, label='MA50', alpha=0.7, color='orange')
            
            # VCP區域標記
            if analysis_result.get('patterns', {}).get('vcp', {}).get('is_vcp'):
                recent_data = data.tail(20)
                ax1.axvspan(recent_data.index[0], recent_data.index[-1], 
                           alpha=0.2, color='green', label='VCP區域')
            
            ax1.set_title(f'{symbol} 技術分析圖表', fontsize=16, fontweight='bold')
            ax1.set_ylabel('價格 ($)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 成交量圖
            ax2.bar(data.index, data['Volume'], alpha=0.6, color='lightblue')
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            # RSI圖
            if len(data) >= 14:
                rsi_data = []
                for i in range(14, len(data)):
                    price_slice = data['Close'].iloc[i-14:i+1]
                    rsi = self.technical_analyzer.calculate_rsi(price_slice)
                    rsi_data.append(rsi)
                
                rsi_dates = data.index[14:]
                ax3.plot(rsi_dates, rsi_data, color='purple', linewidth=2)
                ax3.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超買線')
                ax3.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超賣線')
                ax3.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
                ax3.set_ylabel('RSI', fontsize=12)
                ax3.set_ylim(0, 100)
                ax3.legend()
                ax3.grid(True, alpha=0.3)
            
            # 格式化x軸日期
            for ax in [ax1, ax2, ax3]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator())
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"圖表創建錯誤: {e}")
    
    def create_portfolio_dashboard(self, results: List[Dict]) -> None:
        """創建投資組合儀表板"""
        try:
            if not results:
                print("沒有數據可供顯示")
                return
            
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. 評分分佈圖
            symbols = [r['symbol'] for r in results]
            scores = [r['score']['total_score'] for r in results]
            colors = ['green' if s >= 60 else 'orange' if s >= 40 else 'red' for s in scores]
            
            bars = ax1.bar(symbols, scores, color=colors, alpha=0.7)
            ax1.set_title('股票評分分佈', fontsize=14, fontweight='bold')
            ax1.set_ylabel('評分')
            ax1.set_ylim(0, 100)
            
            # 添加評分標籤
            for bar, score in zip(bars, scores):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                        f'{score:.1f}', ha='center', va='bottom')
            
            # 2. RS Rating vs 技術評分散點圖
            rs_ratings = [r['rs_rating']['rs_rating'] for r in results]
            tech_scores = [r['score']['breakdown']['technical'] for r in results]
            
            scatter = ax2.scatter(rs_ratings, tech_scores, c=scores, cmap='RdYlGn', 
                                s=100, alpha=0.7, edgecolors='black')
            ax2.set_xlabel('RS Rating')
            ax2.set_ylabel('技術評分')
            ax2.set_title('RS Rating vs 技術評分', fontsize=14, fontweight='bold')
            
            # 添加股票代號標籤
            for i, symbol in enumerate(symbols):
                ax2.annotate(symbol, (rs_ratings[i], tech_scores[i]), 
                           xytext=(5, 5), textcoords='offset points', fontsize=9)
            
            plt.colorbar(scatter, ax=ax2, label='總評分')
            
            # 3. 評級分佈餅圖
            grades = [r['score']['grade'] for r in results]
            grade_counts = pd.Series(grades).value_counts()
            
            colors_pie = ['green', 'lightgreen', 'yellow', 'orange', 'red']
            ax3.pie(grade_counts.values, labels=grade_counts.index, autopct='%1.1f%%',
                   colors=colors_pie[:len(grade_counts)], startangle=90)
            ax3.set_title('評級分佈', fontsize=14, fontweight='bold')
            
            # 4. 各項指標雷達圖
            if results:
                categories = ['RS Rating', '技術指標', '形態識別', '動量指標']
                
                # 計算平均分數
                avg_scores = {
                    'RS Rating': np.mean([r['score']['breakdown']['rs_rating'] for r in results]),
                    '技術指標': np.mean([r['score']['breakdown']['technical'] for r in results]),
                    '形態識別': np.mean([r['score']['breakdown']['pattern'] for r in results]),
                    '動量指標': np.mean([r['score']['breakdown']['momentum'] for r in results])
                }
                
                values = list(avg_scores.values())
                values += values[:1]  # 閉合圖形
                
                angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
                angles += angles[:1]
                
                ax4.plot(angles, values, 'o-', linewidth=2, color='blue')
                ax4.fill(angles, values, alpha=0.25, color='blue')
                ax4.set_xticks(angles[:-1])
                ax4.set_xticklabels(categories)
                ax4.set_ylim(0, 100)
                ax4.set_title('平均指標表現', fontsize=14, fontweight='bold')
                ax4.grid(True)
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"儀表板創建錯誤: {e}")

def main():
    """主程序 - 演示MVP功能"""
    print("Fintech Evolution - 跨鏈投資組合管理平台 MVP (修復版)")
    print("技術指標選股 + Swing Trading形態識別 + 評分系統")
    print("=" * 60)
    
    # 初始化系統
    fintech_mvp = FinTechMVP()
    
    # 測試單股分析
    print("\n單股分析測試:")
    test_result = fintech_mvp.analyze_stock('TSLA')
    
    if 'error' in test_result:
        print(f"錯誤: {test_result['error']}")
    else:
        print(f"{test_result['symbol']} 分析成功")
        print(f"   評分: {test_result['score']['total_score']}/100 ({test_result['score']['grade']})")
        print(f"   建議: {test_result['score']['action']}")
    
    # 測試批量分析
    print("\n批量分析測試:")
    test_symbols = ['AAPL', 'MSFT', 'GOOGL']
    results = fintech_mvp.screen_stocks(test_symbols)
    

    
    # 可視化展示
    if results:
        print("\n生成可視化圖表...")
        
        # 創建投資組合儀表板
        fintech_mvp.create_portfolio_dashboard(results)
        
        # 為第一支股票創建詳細技術分析圖
        if results:
            print(f"\n{results[0]['symbol']} 詳細技術分析圖:")
            fintech_mvp.create_stock_chart(results[0]['symbol'], results[0])

if __name__ == "__main__":
    main()