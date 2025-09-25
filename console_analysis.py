#!/usr/bin/env python3
"""
控制台股票分析 - 修復VCP錯誤版本
"""

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

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

class PatternRecognizer:
    """形態識別 - 修復版"""
    
    @staticmethod
    def detect_vcp_fixed(prices: pd.Series, volumes: pd.Series) -> dict:
        """VCP形態檢測 - 修復版本"""
        try:
            if len(prices) < 20 or len(volumes) < 20:
                return {'is_vcp': False, 'confidence': 0.0, 'stage': 0, 'details': '數據不足'}
            
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
            
            # 修復：安全地轉換所有pandas對象為float
            recent_vol_val = TechnicalAnalyzer.safe_float(recent_vol)
            avg_vol_val = TechnicalAnalyzer.safe_float(avg_vol)
            price_high_val = TechnicalAnalyzer.safe_float(price_high)
            price_low_val = TechnicalAnalyzer.safe_float(price_low)
            price_mean_val = TechnicalAnalyzer.safe_float(price_mean)
            
            # 計算價格範圍
            if price_mean_val > 0:
                price_range = (price_high_val - price_low_val) / price_mean_val
            else:
                price_range = 1.0
            
            # 判斷條件
            volume_contraction = recent_vol_val < avg_vol_val * 0.8 if avg_vol_val > 0 else False
            tight_consolidation = price_range < 0.15
            
            is_vcp = volume_contraction and tight_consolidation
            
            # 詳細信息
            details = f"成交量收縮: {volume_contraction}, 價格整理: {tight_consolidation}, 價格範圍: {price_range:.3f}"
            
            return {
                'is_vcp': is_vcp,
                'confidence': 0.8 if is_vcp else 0.3,
                'stage': 3 if is_vcp else 1,
                'details': details,
                'volume_ratio': recent_vol_val / avg_vol_val if avg_vol_val > 0 else 1.0,
                'price_range': price_range
            }
            
        except Exception as e:
            return {
                'is_vcp': False, 
                'confidence': 0.0, 
                'stage': 0, 
                'details': f'VCP檢測錯誤: {str(e)}',
                'volume_ratio': 1.0,
                'price_range': 0.0
            }

def analyze_stock_comprehensive(symbol: str) -> dict:
    """綜合股票分析"""
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
        
        # 基本信息
        current_price = TechnicalAnalyzer.safe_float(prices.iloc[-1])
        
        if len(prices) > 1:
            prev_price = TechnicalAnalyzer.safe_float(prices.iloc[-2])
            price_change = current_price - prev_price
            price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0
        else:
            price_change = 0
            price_change_pct = 0
        
        # 技術指標
        rsi = TechnicalAnalyzer.calculate_rsi(prices)
        
        # 移動平均
        if len(prices) >= 20:
            ma20_series = prices.rolling(20).mean()
            ma20 = TechnicalAnalyzer.safe_float(ma20_series.iloc[-1])
        else:
            ma20 = current_price
            
        if len(prices) >= 50:
            ma50_series = prices.rolling(50).mean()
            ma50 = TechnicalAnalyzer.safe_float(ma50_series.iloc[-1])
        else:
            ma50 = current_price
        
        # VCP檢測 - 使用修復版本
        vcp_result = PatternRecognizer.detect_vcp_fixed(prices, volumes)
        
        # 成交量分析
        volume_tail = volumes.tail(20)
        avg_volume = TechnicalAnalyzer.safe_float(volume_tail.mean())
        current_volume = TechnicalAnalyzer.safe_float(volumes.iloc[-1])
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        return {
            'symbol': symbol,
            'basic_info': {
                'current_price': current_price,
                'price_change': price_change,
                'price_change_pct': price_change_pct,
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio
            },
            'technical': {
                'rsi': rsi,
                'ma20': ma20,
                'ma50': ma50,
                'trend': 'up' if current_price > ma20 > ma50 else 'down' if current_price < ma20 < ma50 else 'sideways'
            },
            'vcp_analysis': vcp_result,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        return {'error': f'分析 {symbol} 時發生錯誤: {str(e)}'}

def print_analysis_report(result: dict):
    """打印分析報告"""
    if 'error' in result:
        print(f"錯誤: {result['error']}")
        return
    
    symbol = result['symbol']
    basic = result['basic_info']
    tech = result['technical']
    vcp = result['vcp_analysis']
    
    print(f"\n{'='*50}")
    print(f"{symbol} 股票分析報告")
    print(f"{'='*50}")
    
    # 基本信息
    print(f"\n基本信息:")
    print(f"  當前價格: ${basic['current_price']:.2f}")
    print(f"  價格變化: {basic['price_change']:+.2f} ({basic['price_change_pct']:+.2f}%)")
    print(f"  當前成交量: {basic['current_volume']:,.0f}")
    print(f"  成交量比率: {basic['volume_ratio']:.2f}x")
    
    # 技術指標
    print(f"\n技術指標:")
    print(f"  RSI: {tech['rsi']:.1f}")
    print(f"  MA20: ${tech['ma20']:.2f}")
    print(f"  MA50: ${tech['ma50']:.2f}")
    print(f"  趨勢: {tech['trend']}")
    
    # VCP分析
    print(f"\nVCP形態分析:")
    print(f"  VCP形態: {'是' if vcp['is_vcp'] else '否'}")
    print(f"  信心度: {vcp['confidence']:.1%}")
    print(f"  階段: {vcp['stage']}")
    print(f"  成交量比率: {vcp['volume_ratio']:.2f}")
    print(f"  價格範圍: {vcp['price_range']:.3f}")
    print(f"  詳細: {vcp['details']}")
    
    # 簡單評分
    score = 0
    if tech['rsi'] > 30 and tech['rsi'] < 70: score += 25
    if basic['current_price'] > tech['ma20']: score += 25
    if tech['ma20'] > tech['ma50']: score += 25
    if vcp['is_vcp']: score += 25
    
    grade = 'A' if score >= 75 else 'B' if score >= 50 else 'C' if score >= 25 else 'D'
    action = '買入' if score >= 75 else '觀望' if score >= 50 else '避免'
    
    print(f"\n綜合評估:")
    print(f"  評分: {score}/100 ({grade})")
    print(f"  建議: {action}")
    print(f"  分析時間: {result['analysis_time']}")

def main():
    """主程序"""
    print("股票技術分析系統 (VCP錯誤修復版)")
    print("="*50)
    
    # 測試股票列表
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    print(f"\n正在分析 {len(test_symbols)} 支股票...")
    
    results = []
    for symbol in test_symbols:
        result = analyze_stock_comprehensive(symbol)
        results.append(result)
        
        # 打印個別報告
        print_analysis_report(result)
    
    # 總結
    successful_analyses = [r for r in results if 'error' not in r]
    print(f"\n分析總結:")
    print(f"成功分析: {len(successful_analyses)}/{len(test_symbols)} 支股票")
    
    if successful_analyses:
        vcp_stocks = [r['symbol'] for r in successful_analyses if r['vcp_analysis']['is_vcp']]
        if vcp_stocks:
            print(f"發現VCP形態: {', '.join(vcp_stocks)}")
        else:
            print("未發現明顯VCP形態")

if __name__ == "__main__":
    main()