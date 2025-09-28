#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# fresh_news_fetcher.py - 專門獲取最新有效新聞連結

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import yfinance as yf

class FreshNewsFetcher:
    """專門獲取最新有效新聞的類"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_fresh_news(self, ticker: str, max_articles: int = 5) -> List[Dict]:
        """獲取一週內的最新有效新聞"""
        current_time = time.time()
        one_week_ago = current_time - (7 * 24 * 60 * 60)
        
        all_articles = []
        
        # 1. Yahoo Finance 新聞
        yahoo_articles = self._get_yahoo_news(ticker, one_week_ago)
        all_articles.extend(yahoo_articles)
        
        # 2. 如果不夠，嘗試其他源
        if len(all_articles) < max_articles:
            google_articles = self._get_google_news(ticker, one_week_ago)
            all_articles.extend(google_articles)
        
        # 3. 驗證並排序
        verified_articles = self._verify_and_sort(all_articles, max_articles)
        
        return verified_articles
    
    def _get_yahoo_news(self, ticker: str, cutoff_time: float) -> List[Dict]:
        """從Yahoo Finance獲取新聞"""
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            articles = []
            for item in news:
                publish_time = item.get('providerPublishTime', time.time())
                
                # 只要一週內的新聞
                if publish_time < cutoff_time:
                    continue
                
                url = item.get('link', '')
                title = item.get('title', '').strip()
                
                # 基本過濾
                if not url or not title or len(title) < 10:
                    continue
                
                articles.append({
                    'title': title,
                    'url': url,
                    'publishedAt': datetime.fromtimestamp(publish_time).isoformat(),
                    'source': item.get('publisher', 'Yahoo Finance'),
                    'description': item.get('summary', '')[:200],
                    'publish_timestamp': publish_time
                })
            
            return articles[:8]  # 最多8篇
            
        except Exception as e:
            self.logger.error(f"Yahoo新聞獲取失敗: {e}")
            return []
    
    def _get_google_news(self, ticker: str, cutoff_time: float) -> List[Dict]:
        """從Google News獲取新聞（通過RSS）"""
        try:
            # Google News RSS URL
            rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            
            response = self.session.get(rss_url, timeout=10)
            if response.status_code != 200:
                return []
            
            # 簡單解析RSS
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            articles = []
            for item in root.findall('.//item')[:5]:
                title_elem = item.find('title')
                link_elem = item.find('link')
                pub_date_elem = item.find('pubDate')
                
                if title_elem is None or link_elem is None:
                    continue
                
                title = title_elem.text.strip()
                url = link_elem.text.strip()
                
                # 解析發布時間
                pub_time = time.time()  # 默認當前時間
                if pub_date_elem is not None:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_date_elem.text)
                        pub_time = dt.timestamp()
                    except:
                        pass
                
                # 只要一週內的新聞
                if pub_time < cutoff_time:
                    continue
                
                articles.append({
                    'title': title,
                    'url': url,
                    'publishedAt': datetime.fromtimestamp(pub_time).isoformat(),
                    'source': 'Google News',
                    'description': f'{ticker} 相關新聞',
                    'publish_timestamp': pub_time
                })
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Google新聞獲取失敗: {e}")
            return []
    
    def _verify_and_sort(self, articles: List[Dict], max_articles: int) -> List[Dict]:
        """驗證連結並排序"""
        verified = []
        seen_urls = set()
        
        # 按時間排序（最新的在前）
        articles.sort(key=lambda x: x.get('publish_timestamp', 0), reverse=True)
        
        for article in articles:
            if len(verified) >= max_articles:
                break
            
            url = article.get('url', '')
            
            # 去重
            if url in seen_urls:
                continue
            
            # 驗證連結
            if self._is_valid_link(url):
                seen_urls.add(url)
                article['verified'] = True
                article['last_verified'] = datetime.now().isoformat()
                verified.append(article)
        
        return verified
    
    def _is_valid_link(self, url: str) -> bool:
        """驗證連結是否有效"""
        if not url or not url.startswith('http') or len(url) < 20:
            return False
        
        # 排除已知的無效域名
        invalid_domains = ['example.com', 'localhost', 'test.com']
        if any(domain in url for domain in invalid_domains):
            return False
        
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except:
            return False

# 獨立函數供外部調用
def fetch_fresh_news(ticker: str, max_articles: int = 5) -> Dict:
    """獲取最新新聞的主函數"""
    fetcher = FreshNewsFetcher()
    articles = fetcher.get_fresh_news(ticker, max_articles)
    
    return {
        'ticker': ticker,
        'articles': articles,
        'news_count': len(articles),
        'last_updated': datetime.now().isoformat(),
        'source': 'Fresh News Fetcher',
        'success': True
    }

if __name__ == "__main__":
    # 測試
    result = fetch_fresh_news('AAPL')
    print(f"找到 {result['news_count']} 篇新聞:")
    for i, article in enumerate(result['articles'], 1):
        print(f"{i}. {article['title']}")
        print(f"   {article['url']}")
        print(f"   {article['publishedAt']}")
        print()