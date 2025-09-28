#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_real_news.py - 測試真實新聞連結

import asyncio
import yfinance as yf
import requests
import time
from datetime import datetime

async def test_real_yahoo_news():
    """測試真實的Yahoo Finance新聞"""
    print("🔍 測試真實Yahoo Finance新聞連結...")
    
    tickers = ['AAPL', 'TSLA', 'NVDA']
    current_time = time.time()
    one_week_ago = current_time - (7 * 24 * 60 * 60)
    
    for ticker in tickers:
        print(f"\n📊 測試 {ticker}...")
        
        try:
            # 使用yfinance獲取新聞
            stock = yf.Ticker(ticker)
            news = stock.news
            
            print(f"找到 {len(news)} 篇新聞")
            
            valid_count = 0
            for i, item in enumerate(news[:5], 1):
                title = item.get('title', 'N/A')
                url = item.get('link', '')
                publisher = item.get('publisher', 'Unknown')
                publish_time = item.get('providerPublishTime', current_time)
                
                # 檢查新聞時效性
                if publish_time < one_week_ago:
                    print(f"\n{i}. [過期] {title[:50]}...")
                    continue
                
                print(f"\n{i}. {title[:60]}...")
                print(f"   來源: {publisher}")
                print(f"   時間: {datetime.fromtimestamp(publish_time).strftime('%Y-%m-%d %H:%M')}")
                print(f"   連結: {url}")
                
                # 深度驗證連結
                if url and url.startswith('http') and 'example.com' not in url and len(url) > 20:
                    try:
                        response = requests.get(url, timeout=8, allow_redirects=True)
                        if (response.status_code < 400 and 
                            'not found' not in response.text.lower() and
                            len(response.text) > 1000):
                            print(f"   ✅ 連結有效且有內容 (狀態碼: {response.status_code}, 內容長度: {len(response.text)})")
                            valid_count += 1
                        else:
                            print(f"   ❌ 連結無效或無內容 (狀態碼: {response.status_code})")
                    except Exception as e:
                        print(f"   ❌ 連結測試失敗: {str(e)}")
                else:
                    print(f"   ⚠️  無效的URL格式")
            
            print(f"\n📈 {ticker} 總結: {valid_count} 個有效連結")
                    
        except Exception as e:
            print(f"❌ 測試 {ticker} 失敗: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_real_yahoo_news())