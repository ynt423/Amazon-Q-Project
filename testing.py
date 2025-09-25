#!/usr/bin/env python3
"""
Fintech Evolution - 跨鏈投資組合管理平台 MVP
技術指標選股 + Swing Trading形態識別 + 評分系統
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# 確保pandas正確導入
pd.options.mode.chained_assignment = None

class TechnicalAnalyzer:
    """技術指標計算引擎"""
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast=12, slow=26, signal=9) -> Dict:
        """MACD指標計算"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        # 安全地檢查交叉信號
        current_macd = float(macd_line.iloc[-1])
        current_signal = float(signal_line.iloc[-1])
        prev_macd = float(macd_line.iloc[-2]) if len(macd_line) > 1 else current_macd
        prev_signal = float(signal_line.iloc[-2]) if len(signal_line) > 1 else current_signal
        
        return {
            'macd': current_macd,
            'signal': current_signal,
            'histogram': float(histogram.iloc[-1]),
            'bullish_crossover': current_macd > current_signal and prev_macd <= prev_signal
        }
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period=14) -> float:
        """RSI指標計算"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        result = rsi.iloc[-1]
        return float(result) if not pd.isna(result) else 50.0
    
    @staticmethod
    def calculate_moving_averages(prices: pd.Series) -> Dict:
        """移動平均線計算"""
        ma20 = prices.rolling(20).mean().iloc[-1]
        ma50 = prices.rolling(50).mean().iloc[-1]
        ma200 = prices.rolling(200).mean().iloc[-1]
        current_price = prices.iloc[-1]
        
        return {
            'ma20': float(ma20) if not pd.isna(ma20) else float(current_price),
            'ma50': float(ma50) if not pd.isna(ma50) else float(current_price),
            'ma200': float(ma200) if not pd.isna(ma200) else float(current_price),
            'current_price': float(current_price)
        }

class PatternRecognizer:
    """Swing Trading形態識別"""
    
    @staticmethod
    def detect_vcp(prices: pd.Series, volumes: pd.Series) -> Dict:
        """VCP形態檢測"""
        if len(prices) < 50:
            return {'is_vcp': False}
        
        # 簡化VCP檢測：尋找成交量收縮 + 價格整理
        min_periods = min(20, len(volumes))
        recent_vol = volumes.tail(min_periods).mean()
        avg_vol = volumes.tail(min(50, len(volumes))).mean()
        
        price_tail = prices.tail(min_periods)
        price_range = (price_tail.max() - price_tail.min()) / price_tail.mean()
        
        volume_contraction = float(recent_vol) < float(avg_vol) * 0.8
        tight_consolidation = float(price_range) < 0.15
        
        return {
            'is_vcp': volume_contraction and tight_consolidation,
            'confidence': 0.8 if volume_contraction and tight_consolidation else 0.3,
            'stage': 3 if volume_contraction and tight_consolidation else 1
        }
    
    @staticmethod
    def detect_breakout(prices: pd.Series, volumes: pd.Series) -> Dict:
        """突破形態檢測"""
        if len(prices) < 30:
            return {'is_breakout': False}
        
        # 尋找阻力位突破
        min_periods = min(30, len(prices))
        resistance = float(prices.tail(min_periods).quantile(0.9))
        current_price = float(prices.iloc[-1])
        
        vol_periods = min(20, len(volumes))
        avg_volume = float(volumes.tail(vol_periods).mean())
        current_volume = float(volumes.iloc[-1])
        
        volume_surge = current_volume > avg_volume * 1.5
        is_breakout = current_price > resistance and volume_surge
        
        return {
            'is_breakout': is_breakout,
            'resistance_level': resistance,
            'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1.0,
            'strength': 0.8 if is_breakout else 0.2
        }

class RSRatingCalculator:
    """相對強度評級計算"""
    
    def __init__(self):
        self.sp500_symbol = '^GSPC'
    
    def calculate_rs_rating(self, symbol: str, period: int = 252) -> Dict:
        """計算RS Rating"""
        try:
            # 獲取股票和市場數據
            stock = yf.download(symbol, period='1y', progress=False)['Close']
            market = yf.download(self.sp500_symbol, period='1y', progress=False)['Close']
            
            if len(stock) < 63 or len(market) < 63:
                return {'rs_rating': 50, 'relative_performance': 0}
            
            # 計算不同時期相對表現
            min_len = min(len(stock), len(market))
            periods = [p for p in [63, 126, 189, 252] if p <= min_len]
            rs_scores = []
            
            for p in periods:
                if min_len >= p:
                    stock_return = (float(stock.iloc[-1]) / float(stock.iloc[-p]) - 1) * 100
                    market_return = (float(market.iloc[-1]) / float(market.iloc[-p]) - 1) * 100
                    relative_perf = stock_return - market_return
                    rs_scores.append(relative_perf)
            
            # 加權計算
            weights = [0.4, 0.3, 0.2, 0.1][:len(rs_scores)]
            weighted_rs = sum(score * weight for score, weight in zip(rs_scores, weights))
            
            # 轉換為1-99評級 (簡化版)
            rs_rating = max(1, min(99, int(50 + weighted_rs)))
            
            return {
                'rs_rating': rs_rating,
                'relative_performance': weighted_rs,
                'interpretation': self._interpret_rs(rs_rating)
            }
            
        except Exception as e:
            print(f"RS Rating計算錯誤 {symbol}: {e}")
            return {'rs_rating': 50, 'relative_performance': 0}
    
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
        scores = {
            'rs_rating': self._score_rs_rating(stock_data.get('rs_rating', {})),
            'technical': self._score_technical(stock_data.get('technical', {})),
            'pattern': self._score_pattern(stock_data.get('patterns', {})),
            'momentum': self._score_momentum(stock_data.get('momentum', {}))
        }
        
        # 加權總分
        total_score = sum(score * self.weights[key] for key, score in scores.items())
        
        return {
            'total_score': round(total_score, 2),
            'grade': self._get_grade(total_score),
            'breakdown': scores,
            'action': self._get_action(total_score, scores)
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
        
        if price > ma20 > ma50: score += 25
        elif price > ma20: score += 15
        
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
        print(f"\n分析股票: {symbol}")
        print("=" * 50)
        
        try:
            # 獲取數據
            data = yf.download(symbol, period='1y', progress=False)
            if data.empty:
                return {'error': f'無法獲取 {symbol} 數據'}
            
            prices = data['Close']
            volumes = data['Volume']
            
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
                'current_price': prices.iloc[-1],
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
        
        # 按評分排序
        results.sort(key=lambda x: x['score']['total_score'], reverse=True)
        return results
    
    def print_analysis(self, analysis: Dict):
        """打印分析結果"""
        if 'error' in analysis:
            print(f"錯誤: {analysis['error']}")
            return
        
        symbol = analysis['symbol']
        price = analysis['current_price']
        score = analysis['score']
        rs = analysis['rs_rating']
        
        print(f"股票代號: {symbol}")
        print(f"當前價格: ${price:.2f}")
        print(f"綜合評分: {score['total_score']}/100 ({score['grade']})")
        print(f"操作建議: {score['action']}")
        print(f"RS Rating: {rs['rs_rating']} ({rs['interpretation']})")
        
        # 技術指標
        tech = analysis['technical']
        print(f"\n技術指標:")
        print(f"  MACD: {tech['macd']['macd']:.3f} (訊號: {tech['macd']['signal']:.3f})")
        print(f"  RSI: {tech['rsi']:.1f}")
        print(f"  MA20: ${tech['ma']['ma20']:.2f}")
        
        # 形態識別
        patterns = analysis['patterns']
        print(f"\n形態識別:")
        if patterns['vcp']['is_vcp']:
            print(f"  ✓ VCP形態 (信心度: {patterns['vcp']['confidence']:.1f})")
        if patterns['breakout']['is_breakout']:
            print(f"  ✓ 突破形態 (強度: {patterns['breakout']['strength']:.1f})")
        
        print(f"\n評分明細:")
        for key, value in score['breakdown'].items():
            print(f"  {key}: {value:.1f}")
        
        print("-" * 50)

def main():
    """主程序 - 演示MVP功能"""
    print("🚀 Fintech Evolution - 跨鏈投資組合管理平台 MVP")
    print("技術指標選股 + Swing Trading形態識別 + 評分系統")
    print("=" * 60)
    
    # 初始化系統
    fintech_mvp = FinTechMVP()
    
    # 測試股票列表 (美股 + 加密貨幣相關)
    test_symbols = ['AAPL', 'TSLA', 'NVDA', 'COIN', 'MSTR']
    
    print("開始批量分析...")
    results = fintech_mvp.screen_stocks(test_symbols)
    
    print(f"\n📊 選股結果 (共 {len(results)} 支股票):")
    print("=" * 60)
    
    # 顯示前3名
    for i, result in enumerate(results[:3], 1):
        print(f"\n🏆 第 {i} 名:")
        fintech_mvp.print_analysis(result)
    
    # 簡化摘要
    print("\n📈 投資組合建議:")
    print("=" * 30)
    for result in results:
        symbol = result['symbol']
        score = result['score']['total_score']
        grade = result['score']['grade']
        action = result['score']['action']
        print(f"{symbol:6} | 評分: {score:5.1f} ({grade:2}) | {action}")

if __name__ == "__main__":
    main()