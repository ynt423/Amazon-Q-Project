#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_fresh_news.py - 測試新的新聞獲取函數

from fresh_news_fetcher import fetch_fresh_news
import requests

def test_fresh_news():
    """測試新的新聞獲取函數"""
    print("🔍 測試新的新聞獲取函數...")
    
    tickers = ['AAPL', 'TSLA', 'NVDA']
    
    for ticker in tickers:
        print(f"\n📊 測試 {ticker}...")
        
        try:
            result = fetch_fresh_news(ticker, max_articles=3)
            
            if result['success']:
                print(f"✅ 成功獲取 {result['news_count']} 篇新聞")
                
                for i, article in enumerate(result['articles'], 1):
                    print(f"\n{i}. {article['title'][:60]}...")
                    print(f"   來源: {article['source']}")
                    print(f"   時間: {article['publishedAt']}")
                    print(f"   連結: {article['url']}")
                    
                    # 驗證連結
                    if article.get('verified'):
                        print("   ✅ 連結已驗證")
                    else:
                        # 手動驗證
                        try:
                            response = requests.head(article['url'], timeout=5)
                            if response.status_code < 400:
                                print("   ✅ 連結有效")
                            else:
                                print(f"   ❌ 連結無效 ({response.status_code})")
                        except:
                            print("   ❌ 連結測試失敗")
            else:
                print("❌ 獲取新聞失敗")
                
        except Exception as e:
            print(f"❌ 測試失敗: {e}")

if __name__ == "__main__":
    test_fresh_news()