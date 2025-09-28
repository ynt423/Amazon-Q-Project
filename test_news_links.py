# test_news_links.py - 測試新聞連結功能

import asyncio
import logging
from news_analyzer import EnhancedNewsAnalyzer
import requests
from datetime import datetime

# 設置日誌
logging.basicConfig(level=logging.INFO)

async def test_news_links():
    """測試新聞連結的有效性"""
    print("🔍 測試新聞連結功能...")
    
    # 初始化新聞分析器
    news_analyzer = EnhancedNewsAnalyzer()
    
    # 測試股票列表
    test_tickers = ['AAPL', 'TSLA', 'NVDA', 'MSFT']
    
    for ticker in test_tickers:
        print(f"\n📊 測試 {ticker} 的新聞連結...")
        
        try:
            # 獲取新聞分析
            result = await news_analyzer.comprehensive_analysis(ticker)
            
            if result.get('news_analysis', {}).get('articles'):
                articles = result['news_analysis']['articles']
                print(f"✅ 找到 {len(articles)} 篇新聞文章")
                
                # 測試每個連結
                for i, article in enumerate(articles[:3], 1):  # 只測試前3篇
                    title = article.get('title', 'N/A')
                    url = article.get('url', '')
                    source = article.get('source', 'Unknown')
                    
                    print(f"\n{i}. 標題: {title[:50]}...")
                    print(f"   來源: {source}")
                    print(f"   連結: {url}")
                    
                    # 驗證連結
                    if url and url.startswith('http'):
                        try:
                            response = requests.head(url, timeout=5, allow_redirects=True)
                            if response.status_code < 400:
                                print(f"   ✅ 連結有效 (狀態碼: {response.status_code})")
                            else:
                                print(f"   ❌ 連結無效 (狀態碼: {response.status_code})")
                        except Exception as e:
                            print(f"   ❌ 連結測試失敗: {str(e)}")
                    else:
                        print(f"   ⚠️  無效的URL格式")
            else:
                print(f"❌ 沒有找到 {ticker} 的新聞文章")
                
        except Exception as e:
            print(f"❌ 測試 {ticker} 時發生錯誤: {str(e)}")
    
    print("\n🎉 新聞連結測試完成！")

def test_url_validation():
    """測試URL驗證功能"""
    print("\n🔗 測試URL驗證功能...")
    
    test_urls = [
        'https://finance.yahoo.com/quote/AAPL',
        'https://www.marketwatch.com/investing/stock/tsla',
        'https://seekingalpha.com/symbol/NVDA',
        'https://invalid-url-test.com/nonexistent',
        'not-a-url',
        ''
    ]
    
    for url in test_urls:
        print(f"\n測試URL: {url}")
        
        if not url:
            print("   ⚠️  空URL")
            continue
            
        if not url.startswith('http'):
            print("   ❌ 無效的URL格式")
            continue
            
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code < 400:
                print(f"   ✅ URL有效 (狀態碼: {response.status_code})")
                if response.url != url:
                    print(f"   🔄 重定向到: {response.url}")
            else:
                print(f"   ❌ URL無效 (狀態碼: {response.status_code})")
        except requests.exceptions.Timeout:
            print("   ⏰ 請求超時")
        except requests.exceptions.ConnectionError:
            print("   🔌 連接錯誤")
        except Exception as e:
            print(f"   ❌ 測試失敗: {str(e)}")

def generate_test_report():
    """生成測試報告"""
    print("\n📋 生成新聞連結測試報告...")
    
    report = {
        "test_time": datetime.now().isoformat(),
        "test_summary": {
            "total_tickers_tested": 4,
            "news_sources_tested": ["Yahoo Finance", "MarketWatch", "Seeking Alpha", "RSS Feeds"],
            "url_validation_methods": ["HTTP HEAD request", "Status code check", "Redirect handling"]
        },
        "recommendations": [
            "使用多個新聞源以提高可靠性",
            "實施連結驗證和自動更新機制",
            "添加連結失效時的備用方案",
            "定期檢查和更新新聞API配置"
        ]
    }
    
    print("✅ 測試報告:")
    for key, value in report.items():
        print(f"   {key}: {value}")

if __name__ == "__main__":
    print("🚀 開始新聞連結功能測試...")
    
    # 運行異步測試
    asyncio.run(test_news_links())
    
    # 運行URL驗證測試
    test_url_validation()
    
    # 生成測試報告
    generate_test_report()
    
    print("\n✨ 所有測試完成！")