#!/usr/bin/env python3
"""
股票分析可視化演示
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 設置中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def create_stock_analysis_chart(symbol='AAPL'):
    """創建股票技術分析圖表"""
    try:
        print(f"正在獲取 {symbol} 數據...")
        
        # 獲取6個月數據
        data = yf.download(symbol, period='6mo', progress=False)
        if data.empty:
            print(f"無法獲取 {symbol} 數據")
            return
        
        # 計算技術指標
        data['MA20'] = data['Close'].rolling(20).mean()
        data['MA50'] = data['Close'].rolling(50).mean()
        
        # 計算RSI
        if len(data) >= 14:
            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            loss = loss.replace(0, 0.0001)
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
        else:
            data['RSI'] = 50
        
        # 創建子圖
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12), 
                                           gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # 主圖：價格和移動平均線
        ax1.plot(data.index, data['Close'], label=f'{symbol} 收盤價', linewidth=2, color='black')
        ax1.plot(data.index, data['MA20'], label='MA20', alpha=0.7, color='blue')
        ax1.plot(data.index, data['MA50'], label='MA50', alpha=0.7, color='orange')
        
        ax1.set_title(f'{symbol} 技術分析圖表', fontsize=16, fontweight='bold')
        ax1.set_ylabel('價格 ($)', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 成交量圖
        ax2.bar(data.index, data['Volume'], alpha=0.6, color='lightblue')
        ax2.set_ylabel('成交量', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # RSI圖
        ax3.plot(data.index, data['RSI'], color='purple', linewidth=2)
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
        
        print(f"{symbol} 技術分析圖表已生成")
        
    except Exception as e:
        print(f"圖表創建錯誤: {e}")

def create_portfolio_comparison(symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA']):
    """創建投資組合比較圖表"""
    try:
        print("正在獲取多股數據進行比較...")
        
        # 獲取數據
        data = {}
        for symbol in symbols:
            stock_data = yf.download(symbol, period='1y', progress=False)
            if not stock_data.empty:
                data[symbol] = stock_data['Close']
        
        if not data:
            print("無法獲取任何股票數據")
            return
        
        # 創建DataFrame
        df = pd.DataFrame(data)
        
        # 計算歸一化價格（以第一天為基準）
        normalized_df = df / df.iloc[0] * 100
        
        # 創建圖表
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 歸一化價格走勢
        for symbol in symbols:
            if symbol in normalized_df.columns:
                ax1.plot(normalized_df.index, normalized_df[symbol], label=symbol, linewidth=2)
        
        ax1.set_title('股票價格走勢比較 (歸一化)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('相對價格 (%)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 成交量比較
        volumes = {}
        for symbol in symbols:
            stock_data = yf.download(symbol, period='1mo', progress=False)
            if not stock_data.empty and 'Volume' in stock_data.columns:
                avg_vol = stock_data['Volume'].mean()
                if not pd.isna(avg_vol):
                    volumes[symbol] = avg_vol
        
        if volumes:
            symbols_list = list(volumes.keys())
            values_list = list(volumes.values())
            ax2.bar(symbols_list, values_list, alpha=0.7)
            ax2.set_title('平均成交量比較', fontsize=14, fontweight='bold')
            ax2.set_ylabel('平均成交量')
            ax2.tick_params(axis='x', rotation=45)
        
        # 3. 波動率比較
        volatility = {}
        for symbol in symbols:
            if symbol in df.columns:
                returns = df[symbol].pct_change().dropna()
                if len(returns) > 0:
                    vol = returns.std() * np.sqrt(252) * 100  # 年化波動率
                    if not pd.isna(vol):
                        volatility[symbol] = vol
        
        if volatility:
            symbols_list = list(volatility.keys())
            values_list = list(volatility.values())
            colors = ['green' if v < 30 else 'orange' if v < 50 else 'red' for v in values_list]
            ax3.bar(symbols_list, values_list, color=colors, alpha=0.7)
            ax3.set_title('年化波動率比較', fontsize=14, fontweight='bold')
            ax3.set_ylabel('波動率 (%)')
            ax3.tick_params(axis='x', rotation=45)
        
        # 4. 相關性熱力圖
        if len(df.columns) > 1:
            correlation_matrix = df.corr()
            im = ax4.imshow(correlation_matrix, cmap='coolwarm', aspect='auto')
            ax4.set_xticks(range(len(correlation_matrix.columns)))
            ax4.set_yticks(range(len(correlation_matrix.columns)))
            ax4.set_xticklabels(correlation_matrix.columns)
            ax4.set_yticklabels(correlation_matrix.columns)
            ax4.set_title('股票相關性矩陣', fontsize=14, fontweight='bold')
            
            # 添加數值標籤
            for i in range(len(correlation_matrix.columns)):
                for j in range(len(correlation_matrix.columns)):
                    text = ax4.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                   ha="center", va="center", color="black")
            
            plt.colorbar(im, ax=ax4)
        
        plt.tight_layout()
        plt.show()
        
        print("投資組合比較圖表已生成")
        
    except Exception as e:
        print(f"比較圖表創建錯誤: {e}")

def main():
    """主程序"""
    print("股票分析可視化演示")
    print("=" * 40)
    
    # 創建單股分析圖
    print("\n1. 單股技術分析圖表:")
    create_stock_analysis_chart('AAPL')
    
    # 創建投資組合比較圖
    print("\n2. 投資組合比較圖表:")
    create_portfolio_comparison(['AAPL', 'MSFT', 'GOOGL', 'TSLA'])
    
    print("\n可視化演示完成！")

if __name__ == "__main__":
    main()