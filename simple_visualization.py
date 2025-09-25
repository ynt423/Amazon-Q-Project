#!/usr/bin/env python3
"""
簡單股票分析可視化演示
"""

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

def simple_stock_chart(symbol='AAPL'):
    """創建簡單的股票圖表"""
    try:
        print(f"正在分析 {symbol}...")
        
        # 獲取數據
        data = yf.download(symbol, period='3mo', progress=False)
        if data.empty:
            print(f"無法獲取 {symbol} 數據")
            return
        
        # 創建圖表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # 價格圖
        ax1.plot(data.index, data['Close'], linewidth=2, color='blue', label=f'{symbol} 收盤價')
        ax1.set_title(f'{symbol} 股價走勢', fontsize=14, fontweight='bold')
        ax1.set_ylabel('價格 ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 成交量圖
        ax2.bar(data.index, data['Volume'], alpha=0.6, color='lightgreen')
        ax2.set_title('成交量', fontsize=12)
        ax2.set_ylabel('成交量')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # 顯示基本統計
        current_price = data['Close'].iloc[-1]
        high_52w = data['High'].max()
        low_52w = data['Low'].min()
        avg_volume = data['Volume'].mean()
        
        print(f"\n{symbol} 基本資訊:")
        print(f"當前價格: ${current_price:.2f}")
        print(f"期間最高: ${high_52w:.2f}")
        print(f"期間最低: ${low_52w:.2f}")
        print(f"平均成交量: {avg_volume:,.0f}")
        
    except Exception as e:
        print(f"錯誤: {e}")

def compare_stocks(symbols=['AAPL', 'MSFT', 'GOOGL']):
    """比較多支股票"""
    try:
        print("正在比較股票表現...")
        
        # 獲取數據並計算報酬率
        returns = {}
        prices = {}
        
        for symbol in symbols:
            data = yf.download(symbol, period='1y', progress=False)
            if not data.empty:
                start_price = data['Close'].iloc[0]
                end_price = data['Close'].iloc[-1]
                return_pct = ((end_price - start_price) / start_price) * 100
                returns[symbol] = return_pct
                prices[symbol] = end_price
        
        if not returns:
            print("無法獲取股票數據")
            return
        
        # 創建比較圖表
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 報酬率比較
        symbols_list = list(returns.keys())
        returns_list = list(returns.values())
        colors = ['green' if r > 0 else 'red' for r in returns_list]
        
        bars1 = ax1.bar(symbols_list, returns_list, color=colors, alpha=0.7)
        ax1.set_title('年度報酬率比較', fontsize=14, fontweight='bold')
        ax1.set_ylabel('報酬率 (%)')
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax1.grid(True, alpha=0.3)
        
        # 添加數值標籤
        for bar, value in zip(bars1, returns_list):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (1 if value > 0 else -3),
                    f'{value:.1f}%', ha='center', va='bottom' if value > 0 else 'top')
        
        # 當前價格比較
        prices_list = list(prices.values())
        bars2 = ax2.bar(symbols_list, prices_list, alpha=0.7, color='skyblue')
        ax2.set_title('當前股價比較', fontsize=14, fontweight='bold')
        ax2.set_ylabel('價格 ($)')
        ax2.grid(True, alpha=0.3)
        
        # 添加價格標籤
        for bar, value in zip(bars2, prices_list):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(prices_list)*0.01,
                    f'${value:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.show()
        
        # 顯示排名
        print("\n股票表現排名:")
        sorted_returns = sorted(returns.items(), key=lambda x: x[1], reverse=True)
        for i, (symbol, ret) in enumerate(sorted_returns, 1):
            print(f"{i}. {symbol}: {ret:+.1f}% (${prices[symbol]:.2f})")
        
    except Exception as e:
        print(f"比較錯誤: {e}")

def main():
    """主程序"""
    print("簡單股票分析可視化")
    print("=" * 30)
    
    # 單股分析
    print("\n1. 單股分析:")
    simple_stock_chart('AAPL')
    
    # 多股比較
    print("\n2. 多股比較:")
    compare_stocks(['AAPL', 'MSFT', 'GOOGL', 'TSLA'])
    
    print("\n分析完成！")

if __name__ == "__main__":
    main()