import time
import yfinance as yf
from datetime import datetime

def get_latest_news(ticker):
    """獲取最新新聞 - 簡化版本"""
    current_time = time.time()
    
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        articles = []
        for item in news[:5]:
            publish_time = item.get('providerPublishTime', current_time)
            
            # 只要24小時內的新聞
            if current_time - publish_time > 86400:  # 24小時 = 86400秒
                continue
                
            articles.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'source': item.get('publisher', 'Yahoo Finance'),
                'publishedAt': datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M'),
                'description': item.get('summary', '')[:150] + '...'
            })
        
        return {
            'success': True,
            'articles': articles,
            'news_count': len(articles),
            'current_time': datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'articles': [],
            'current_time': datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
        }