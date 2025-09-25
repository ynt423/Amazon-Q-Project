#!/usr/bin/env python3
"""
Fintech Evolution - 跨鏈投資組合管理平台 Web版
Flask + Plotly 可視化界面
"""

from flask import Flask, render_template, request, jsonify
import plotly.graph_objs as go
import plotly.utils
import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
from testing_fixed import FinTechMVP, TechnicalAnalyzer, PatternRecognizer, RSRatingCalculator, StockScorer

app = Flask(__name__)
app.secret_key = 'fintech_evolution_2024'

# 初始化分析引擎
fintech_engine = FinTechMVP()

class WebVisualizer:
    """Web可視化組件"""
    
    @staticmethod
    def create_price_chart(symbol: str, period: str = '6mo'):
        """創建價格走勢圖"""
        try:
            data = yf.download(symbol, period=period, progress=False)
            if data.empty:
                return None
            
            # 計算移動平均線
            data['MA20'] = data['Close'].rolling(20).mean()
            data['MA50'] = data['Close'].rolling(50).mean()
            
            fig = go.Figure()
            
            # K線圖
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name=symbol,
                increasing_line_color='#00ff88',
                decreasing_line_color='#ff4444'
            ))
            
            # 移動平均線
            fig.add_trace(go.Scatter(
                x=data.index, y=data['MA20'],
                name='MA20', line=dict(color='orange', width=1)
            ))
            
            fig.add_trace(go.Scatter(
                x=data.index, y=data['MA50'],
                name='MA50', line=dict(color='blue', width=1)
            ))
            
            fig.update_layout(
                title=f'{symbol} 價格走勢圖',
                xaxis_title='日期',
                yaxis_title='價格 ($)',
                template='plotly_dark',
                height=400,
                showlegend=True
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            print(f"圖表創建錯誤: {e}")
            return None
    
    @staticmethod
    def create_technical_indicators_chart(symbol: str):
        """創建技術指標圖表"""
        try:
            data = yf.download(symbol, period='6mo', progress=False)
            if data.empty:
                return None
            
            # 計算技術指標
            analyzer = TechnicalAnalyzer()
            
            # MACD
            macd_data = []
            rsi_data = []
            
            for i in range(26, len(data)):
                prices = data['Close'].iloc[:i+1]
                macd = analyzer.calculate_macd(prices)
                rsi = analyzer.calculate_rsi(prices)
                
                macd_data.append({
                    'date': data.index[i],
                    'macd': macd['macd'],
                    'signal': macd['signal'],
                    'histogram': macd['histogram']
                })
                
                rsi_data.append({
                    'date': data.index[i],
                    'rsi': rsi
                })
            
            # 創建子圖
            from plotly.subplots import make_subplots
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('MACD', 'RSI'),
                vertical_spacing=0.1
            )
            
            # MACD圖
            macd_df = pd.DataFrame(macd_data)
            fig.add_trace(go.Scatter(
                x=macd_df['date'], y=macd_df['macd'],
                name='MACD', line=dict(color='blue')
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(
                x=macd_df['date'], y=macd_df['signal'],
                name='Signal', line=dict(color='red')
            ), row=1, col=1)
            
            fig.add_trace(go.Bar(
                x=macd_df['date'], y=macd_df['histogram'],
                name='Histogram', marker_color='gray'
            ), row=1, col=1)
            
            # RSI圖
            rsi_df = pd.DataFrame(rsi_data)
            fig.add_trace(go.Scatter(
                x=rsi_df['date'], y=rsi_df['rsi'],
                name='RSI', line=dict(color='purple')
            ), row=2, col=1)
            
            # RSI超買超賣線
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            
            fig.update_layout(
                title=f'{symbol} 技術指標',
                template='plotly_dark',
                height=500,
                showlegend=True
            )
            
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            
        except Exception as e:
            print(f"技術指標圖表錯誤: {e}")
            return None
    
    @staticmethod
    def create_portfolio_pie_chart(portfolio_data):
        """創建投資組合餅圖"""
        if not portfolio_data:
            return None
        
        symbols = [item['symbol'] for item in portfolio_data]
        values = [item['score']['total_score'] for item in portfolio_data]
        
        fig = go.Figure(data=[go.Pie(
            labels=symbols,
            values=values,
            hole=0.3,
            textinfo='label+percent',
            textfont_size=12,
            marker=dict(colors=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc'])
        )])
        
        fig.update_layout(
            title="投資組合評分分布",
            template='plotly_dark',
            height=400
        )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route('/')
def index():
    """主頁面"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_stock():
    """股票分析API"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            return jsonify({'error': '請輸入股票代號'})
        
        # 執行分析
        analysis = fintech_engine.analyze_stock(symbol)
        
        if 'error' in analysis:
            return jsonify(analysis)
        
        # 生成圖表
        visualizer = WebVisualizer()
        price_chart = visualizer.create_price_chart(symbol)
        tech_chart = visualizer.create_technical_indicators_chart(symbol)
        
        analysis['charts'] = {
            'price_chart': price_chart,
            'technical_chart': tech_chart
        }
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': f'分析錯誤: {str(e)}'})

@app.route('/screen', methods=['POST'])
def screen_stocks():
    """批量選股API"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols:
            return jsonify({'error': '請輸入股票代號列表'})
        
        # 執行批量分析
        results = fintech_engine.screen_stocks(symbols)
        
        # 生成投資組合圖表
        visualizer = WebVisualizer()
        portfolio_chart = visualizer.create_portfolio_pie_chart(results)
        
        return jsonify({
            'results': results,
            'portfolio_chart': portfolio_chart,
            'summary': {
                'total_stocks': len(results),
                'avg_score': sum(r['score']['total_score'] for r in results) / len(results) if results else 0,
                'top_pick': results[0]['symbol'] if results else None
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'選股錯誤: {str(e)}'})

@app.route('/dashboard')
def dashboard():
    """儀表板頁面"""
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)