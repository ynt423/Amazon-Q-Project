# news_analyzer.py - 市場新聞和情緒分析模組

import requests
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class NewsAnalyzer:
    """市場新聞和情緒分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 新聞API配置
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.tiingo_api_key = os.getenv('TIINGO_API_KEY')
        
        # 免費新聞源
        self.free_sources = [
            'https://newsapi.org/v2/everything',
            'https://api.marketaux.com/v1/news/all',
            'https://finnhub.io/api/v1/company-news'
        ]
    
    async def get_market_news(self, ticker: str, days: int = 7) -> Dict:
        """獲取股票相關新聞"""
        try:
            all_articles = []
            current_time = time.time()
            
            # 1. 嘗試Tiingo API (優先級最高)
            if self.tiingo_api_key and self.tiingo_api_key != 'your_tiingo_api_key_here':
                tiingo_articles = await self._get_tiingo_news(ticker, days)
                if tiingo_articles:
                    all_articles.extend(tiingo_articles)
                    self.logger.info(f"Tiingo API: 獲取到 {len(tiingo_articles)} 篇新聞")
            
            # 2. 嘗試RSS新聞源 (最可靠)
            rss_articles = await self._get_rss_news(ticker)
            if rss_articles:
                all_articles.extend(rss_articles)
                self.logger.info(f"RSS News: 獲取到 {len(rss_articles)} 篇新聞")
            
            # 3. 嘗試網頁爬蟲 (可靠)
            web_articles = await self._get_web_scraped_news(ticker)
            if web_articles:
                all_articles.extend(web_articles)
                self.logger.info(f"Web Scraping: 獲取到 {len(web_articles)} 篇新聞")
            
            # 4. 如果文章不够，使用備用方案 (僅在必要時)
            if len(all_articles) < 1:
                backup_result = await self._get_free_news(ticker, days)
                all_articles.extend(backup_result.get('articles', []))
                self.logger.info(f"Backup News: 獲取到 {len(backup_result.get('articles', []))} 篇新聞")
            
            # 7. 驗證所有連結
            verified_articles = await self._verify_article_links(all_articles)
            
            # 5. 去重和排序
            unique_articles = []
            seen_urls = set()
            
            for article in verified_articles:
                url = article.get('url', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_articles.append(article)
            
            # 按時間排序（最新的在前）
            unique_articles.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
            
            # 過濾出最近7天的新聞，優先選擇最新的
            current_date = datetime.now()
            recent_articles = []
            
            for article in unique_articles:
                try:
                    # 嘗試解析發布時間
                    published_str = article.get('publishedAt', '')
                    if published_str:
                        # 處理不同的時間格式
                        if 'T' in published_str:
                            published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        else:
                            published_date = datetime.fromisoformat(published_str)
                        
                        # 檢查是否在最近7天內
                        if (current_date - published_date).days <= 7:
                            recent_articles.append(article)
                    else:
                        # 如果沒有時間信息，假設是最近的
                        recent_articles.append(article)
                        
                except Exception as e:
                    # 如果時間解析失敗，假設是最近的
                    recent_articles.append(article)
            
            # 只保留前5篇最新新聞
            final_articles = recent_articles[:5]
            
            news_data = {
                "ticker": ticker,
                "articles": final_articles,
                "news_count": len(final_articles),
                "last_updated": datetime.now().isoformat(),
                "source": "Multi-source News API",
                "fetch_time": current_time
            }
            
            # 分析新聞情緒
            if final_articles:
                sentiment = await self._analyze_news_sentiment(final_articles)
                news_data["sentiment_score"] = sentiment["score"]
                news_data["sentiment_breakdown"] = sentiment["breakdown"]
            
            return news_data
            
        except Exception as e:
            self.logger.error(f"獲取新聞失敗: {e}")
            return {
                "ticker": ticker,
                "articles": [],
                "sentiment_score": 0,
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
    
    async def _get_newsapi_news(self, ticker: str, days: int) -> Dict:
        """使用 NewsAPI 獲取新聞"""
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f'{ticker} stock',
                'apiKey': self.news_api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                'pageSize': 20
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'url': article.get('url', ''),
                    'publishedAt': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'content': article.get('content', '')
                })
            
            return {
                "ticker": ticker,
                "articles": articles,
                "news_count": len(articles),
                "source": "NewsAPI"
            }
            
        except Exception as e:
            self.logger.error(f"NewsAPI 獲取失敗: {e}")
            return {"ticker": ticker, "articles": [], "error": str(e)}
    
    async def _get_alpha_vantage_news(self, ticker: str, days: int) -> Dict:
        """使用 Alpha Vantage 獲取新聞"""
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': ticker,
                'apikey': self.alpha_vantage_key,
                'limit': 20
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            for item in data.get('feed', []):
                articles.append({
                    'title': item.get('title', ''),
                    'summary': item.get('summary', ''),
                    'url': item.get('url', ''),
                    'time_published': item.get('time_published', ''),
                    'source': item.get('source', ''),
                    'overall_sentiment_score': item.get('overall_sentiment_score', 0),
                    'ticker_sentiment': item.get('ticker_sentiment', [])
                })
            
            return {
                "ticker": ticker,
                "articles": articles,
                "news_count": len(articles),
                "source": "Alpha Vantage"
            }
            
        except Exception as e:
            self.logger.error(f"Alpha Vantage 獲取失敗: {e}")
            return {"ticker": ticker, "articles": [], "error": str(e)}
    
    async def _get_free_news(self, ticker: str, days: int) -> Dict:
        """使用免費新聞源"""
        try:
            articles = []
            
            # 嘗試使用 RSS 新聞源
            try:
                rss_news = await self._get_rss_news(ticker)
                articles.extend(rss_news)
            except Exception as e:
                self.logger.warning(f"RSS新聞獲取失敗: {e}")
            
            # 嘗試使用Yahoo Finance新聞API
            try:
                yahoo_news = await self._get_yahoo_finance_news(ticker)
                articles.extend(yahoo_news)
            except Exception as e:
                self.logger.warning(f"Yahoo Finance新聞獲取失敗: {e}")
            
            # 如果沒有獲取到新聞，使用可靠的備用連結
            if not articles:
                current_time = datetime.now()
                
                # 使用可靠的備用連結（經過測試的有效連結）
                articles = [
                    {
                        'title': f'{ticker} 股票即時報價與分析',
                        'description': f'查看 {ticker} 的即時股價、技術分析圖表和市場數據。',
                        'url': f'https://finance.yahoo.com/quote/{ticker}',
                        'publishedAt': current_time.isoformat(),
                        'source': 'Yahoo Finance',
                        'category': 'Market Data',
                        'verified': True
                    },
                    {
                        'title': f'{ticker} 新聞與市場洞察',
                        'description': f'獲取 {ticker} 的最新新聞、分析師評級和市場洞察。',
                        'url': f'https://finance.yahoo.com/quote/{ticker}/news',
                        'publishedAt': current_time.isoformat(),
                        'source': 'Yahoo Finance News',
                        'category': 'News',
                        'verified': True
                    }
                ]
            
            # 驗證和過濾連結
            verified_articles = await self._verify_article_links(articles)
            
            return {
                "ticker": ticker,
                "articles": verified_articles,
                "news_count": len(verified_articles),
                "source": "Enhanced Free News Sources",
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"免費新聞源獲取失敗: {e}")
            return {"ticker": ticker, "articles": [], "error": str(e)}
    
    async def _get_rss_news(self, ticker: str) -> List[Dict]:
        """使用RSS獲取新聞"""
        try:
            import feedparser
            
            # 更新的RSS源，確保連結有效
            rss_urls = [
                f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US',
                f'https://feeds.marketwatch.com/marketwatch/topstories/?company={ticker}',
                'https://feeds.bloomberg.com/markets/news.rss',
                'https://www.cnbc.com/id/100003114/device/rss/rss.html',  # CNBC Markets
                'https://feeds.reuters.com/reuters/businessNews',  # Reuters Business
                f'https://seekingalpha.com/api/sa/combined/{ticker}.xml',  # Seeking Alpha
                'https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US'  # S&P 500 for market context
            ]
            
            articles = []
            for url in rss_urls:
                try:
                    feed = feedparser.parse(url)
                    if not feed.entries:
                        continue
                        
                    for entry in feed.entries[:5]:  # 取前5篇
                        # 檢查是否與股票相關
                        title_lower = entry.title.lower()
                        summary_lower = entry.get('summary', '').lower()
                        
                        if (ticker.lower() in title_lower or 
                            ticker.lower() in summary_lower or
                            # 對於主要指數，也包含相關新聞
                            any(keyword in title_lower for keyword in ['market', 'stock', 'trading', 'earnings', 'apple', 'tech', 'nasdaq', 'dow', 'sp500']) or
                            # 對於AAPL，也包含Apple相關新聞
                            (ticker.upper() == 'AAPL' and 'apple' in title_lower)):
                            
                            # 驗證連結有效性
                            article_url = entry.link
                            if not article_url or not article_url.startswith('http') or 'example.com' in article_url:
                                continue
                            
                            # 實際測試連結
                            try:
                                import requests
                                response = requests.head(article_url, timeout=3, allow_redirects=True)
                                if response.status_code >= 400:
                                    continue
                            except:
                                continue
                            
                            articles.append({
                                'title': entry.title,
                                'description': entry.get('summary', entry.title)[:200] + '...' if len(entry.get('summary', '')) > 200 else entry.get('summary', entry.title),
                                'url': article_url,
                                'publishedAt': entry.get('published', datetime.now().isoformat()),
                                'source': self._extract_source_name(url),
                                'category': 'News',
                                'verified': True
                            })
                except Exception as e:
                    self.logger.warning(f"RSS URL {url} 獲取失敗: {e}")
                    continue
            
            return articles[:8]  # 最多返回8篇
            
        except ImportError:
            self.logger.warning("feedparser 未安裝，跳過RSS新聞")
            return []
        except Exception as e:
            self.logger.error(f"RSS新聞獲取失敗: {e}")
            return []
    
    async def _analyze_news_sentiment(self, articles: List[Dict]) -> Dict:
        """分析新聞情緒"""
        try:
            # 簡單的情緒分析（可以整合更複雜的 NLP 模型）
            positive_keywords = [
                'bullish', 'growth', 'profit', 'gain', 'rise', 'increase', 
                'positive', 'strong', 'beat', 'exceed', 'outperform'
            ]
            negative_keywords = [
                'bearish', 'decline', 'loss', 'fall', 'decrease', 'negative',
                'weak', 'miss', 'underperform', 'cut', 'reduce'
            ]
            
            total_score = 0
            sentiment_breakdown = {
                'positive': 0,
                'negative': 0,
                'neutral': 0
            }
            
            for article in articles:
                text = f"{article.get('title', '')} {article.get('description', '')} {article.get('summary', '')}"
                text_lower = text.lower()
                
                positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
                negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
                
                if positive_count > negative_count:
                    sentiment_breakdown['positive'] += 1
                    total_score += 1
                elif negative_count > positive_count:
                    sentiment_breakdown['negative'] += 1
                    total_score -= 1
                else:
                    sentiment_breakdown['neutral'] += 1
            
            # 計算情緒分數 (-100 到 +100)
            if len(articles) > 0:
                sentiment_score = (total_score / len(articles)) * 100
            else:
                sentiment_score = 0
            
            return {
                "score": round(sentiment_score, 2),
                "breakdown": sentiment_breakdown,
                "total_articles": len(articles)
            }
            
        except Exception as e:
            self.logger.error(f"情緒分析失敗: {e}")
            return {"score": 0, "breakdown": {}, "total_articles": 0}
    
    async def get_social_sentiment(self, ticker: str) -> Dict:
        """獲取社交媒體情緒（模擬）"""
        try:
            # 這裡可以整合 Twitter API、Reddit API 等
            # 目前返回模擬數據
            return {
                "ticker": ticker,
                "twitter_sentiment": 0.2,  # -1 到 1
                "reddit_sentiment": 0.1,
                "overall_social_sentiment": 0.15,
                "mention_count": 150,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"社交媒體情緒分析失敗: {e}")
            return {"ticker": ticker, "error": str(e)}
    
    async def _get_yahoo_finance_news(self, ticker: str) -> List[Dict]:
        """使用Yahoo Finance API獲取新聞"""
        try:
            import yfinance as yf
            
            # 獲取當前時間
            current_time = time.time()
            one_week_ago = current_time - (7 * 24 * 60 * 60)  # 7天前
            
            # 使用yfinance獲取新聞
            stock = yf.Ticker(ticker)
            news = stock.news
            
            articles = []
            for item in news[:10]:  # 取前10篇然後過濾
                # 檢查新聞時間（只要一週內的新聞）
                publish_time = item.get('providerPublishTime', current_time)
                if publish_time < one_week_ago:
                    continue
                
                # 獲取真實的連結
                article_url = item.get('link')
                
                # 過濾假連結和無效連結
                if (not article_url or 
                    not article_url.startswith('http') or 
                    'example.com' in article_url or
                    len(article_url) < 20):
                    continue
                
                # 實際驗證連結可訪問性
                try:
                    response = requests.get(article_url, timeout=5, allow_redirects=True)
                    if response.status_code >= 400 or 'not found' in response.text.lower():
                        continue
                except:
                    continue
                
                # 確保標題和摘要不為空
                title = item.get('title', '').strip()
                summary = item.get('summary', '').strip()
                
                if not title or len(title) < 10:
                    continue
                
                articles.append({
                    'title': title,
                    'description': summary[:200] + '...' if len(summary) > 200 else summary,
                    'url': article_url,
                    'publishedAt': datetime.fromtimestamp(publish_time).isoformat(),
                    'source': item.get('publisher', 'Yahoo Finance'),
                    'category': 'Financial News',
                    'verified': True,
                    'freshness_score': current_time - publish_time  # 新鮮度評分
                })
                
                # 只返回前5篇有效新聞
                if len(articles) >= 5:
                    break
            
            # 按時間排序（最新的在前）
            articles.sort(key=lambda x: x['publishedAt'], reverse=True)
            
            return articles
            
        except Exception as e:
            self.logger.warning(f"Yahoo Finance新聞獲取失敗: {e}")
            return []
    
    def _extract_source_name(self, url: str) -> str:
        """從URL提取源名稱"""
        if 'yahoo' in url:
            return 'Yahoo Finance'
        elif 'marketwatch' in url:
            return 'MarketWatch'
        elif 'bloomberg' in url:
            return 'Bloomberg'
        elif 'cnbc' in url:
            return 'CNBC'
        elif 'reuters' in url:
            return 'Reuters'
        else:
            return 'Financial News'
    
    async def _verify_article_links(self, articles: List[Dict]) -> List[Dict]:
        """驗證文章連結的有效性"""
        verified_articles = []
        
        for article in articles:
            url = article.get('url', '')
            
            # 過濾假連結和無效連結
            if (not url or 
                not url.startswith('http') or 
                'example.com' in url or 
                len(url) < 15 or
                'localhost' in url or
                'placeholder' in url.lower()):
                continue
            
            # 簡化的連結驗證（更寬鬆的檢查）
            try:
                # 只使用HEAD請求進行快速檢查
                head_response = requests.head(url, timeout=3, allow_redirects=True)
                
                # 如果HEAD請求成功，認為連結有效
                if head_response.status_code < 400:
                    article['url'] = head_response.url  # 更新為最終URL
                    article['link_verified'] = True
                    article['last_verified'] = datetime.now().isoformat()
                    article['final_url'] = head_response.url
                    article['status_code'] = head_response.status_code
                    verified_articles.append(article)
                else:
                    # 即使HEAD失敗，也嘗試添加（可能是某些網站不支援HEAD）
                    article['link_verified'] = False
                    article['last_verified'] = datetime.now().isoformat()
                    article['status_code'] = head_response.status_code
                    verified_articles.append(article)
                    
            except requests.exceptions.Timeout:
                # 超時也添加文章，但標記為未驗證
                article['link_verified'] = False
                article['last_verified'] = datetime.now().isoformat()
                article['status_code'] = 'timeout'
                verified_articles.append(article)
            except requests.exceptions.ConnectionError:
                # 連接錯誤也添加文章，但標記為未驗證
                article['link_verified'] = False
                article['last_verified'] = datetime.now().isoformat()
                article['status_code'] = 'connection_error'
                verified_articles.append(article)
            except Exception as e:
                # 其他錯誤也添加文章，但標記為未驗證
                self.logger.warning(f"連結驗證失敗 {url}: {e}")
                article['link_verified'] = False
                article['last_verified'] = datetime.now().isoformat()
                article['status_code'] = 'error'
                verified_articles.append(article)
        
        return verified_articles
    
    async def _get_tiingo_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """使用Tiingo API獲取新聞"""
        try:
            if not self.tiingo_api_key or self.tiingo_api_key == 'your_tiingo_api_key_here':
                return []
            
            # 計算日期範圍
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 構建API請求
            url = 'https://api.tiingo.com/tiingo/news'
            params = {
                'tickers': ticker.lower(),
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'limit': 10
            }
            headers = {
                'Authorization': f'Token {self.tiingo_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = []
                
                for item in data:
                    # 解析發布時間
                    published_date = item.get('publishedDate', '')
                    if published_date:
                        try:
                            # 處理ISO格式時間
                            if 'T' in published_date:
                                published_date = published_date.replace('Z', '+00:00')
                        except:
                            published_date = datetime.now().isoformat()
                    else:
                        published_date = datetime.now().isoformat()
                    
                    articles.append({
                        'title': item.get('title', ''),
                        'description': item.get('description', '')[:200] + '...' if len(item.get('description', '')) > 200 else item.get('description', ''),
                        'url': item.get('url', ''),
                        'publishedAt': published_date,
                        'source': item.get('source', 'Tiingo'),
                        'category': 'Financial News',
                        'verified': True,  # Tiingo links are generally reliable
                        'tickers': item.get('tickers', []),
                        'tags': item.get('tags', []),
                        'crawl_date': item.get('crawlDate', ''),
                        'article_id': item.get('id', '')
                    })
                
                self.logger.info(f"Tiingo API: 獲取到 {len(articles)} 篇新聞")
                return articles
                
            else:
                self.logger.warning(f"Tiingo API 請求失敗: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Tiingo API 獲取失敗: {e}")
            return []
    
    async def _get_web_scraped_news(self, ticker: str) -> List[Dict]:
        """使用網頁爬蟲獲取最新新聞"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            articles = []
            
            # 嘗試多個新聞源
            news_sources = [
                {
                    'url': f'https://finance.yahoo.com/quote/{ticker}',
                    'title_selector': 'h3 a, .js-content-viewer a, [data-module="Stream"] a',
                    'link_selector': 'h3 a, .js-content-viewer a, [data-module="Stream"] a',
                    'source_name': 'Yahoo Finance'
                },
                {
                    'url': f'https://www.marketwatch.com/investing/stock/{ticker}',
                    'title_selector': '.article__headline a, .headline a',
                    'link_selector': '.article__headline a, .headline a',
                    'source_name': 'MarketWatch'
                }
            ]
            
            for source in news_sources:
                try:
                    response = requests.get(source['url'], timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 查找新聞標題和連結
                        title_elements = soup.select(source['title_selector'])
                        
                        for element in title_elements[:5]:  # 限制前5篇
                            title = element.get_text(strip=True)
                            link = element.get('href', '')
                            
                            # 處理相對連結
                            if link.startswith('/'):
                                if 'yahoo.com' in source['url']:
                                    link = f"https://finance.yahoo.com{link}"
                                elif 'marketwatch.com' in source['url']:
                                    link = f"https://www.marketwatch.com{link}"
                            
                            if title and link and len(title) > 10:
                                # 嘗試從頁面中提取實際發布時間
                                published_time = await self._extract_article_date(element, source['url'])
                                
                                articles.append({
                                    'title': title,
                                    'url': link,
                                    'source': source['source_name'],
                                    'publishedAt': published_time,
                                    'description': title[:150] + '...',
                                    'category': 'News',
                                    'verified': False  # 稍後驗證
                                })
                                
                except Exception as e:
                    self.logger.warning(f"網頁爬蟲失敗 {source['url']}: {e}")
                    continue
            
            return articles
            
        except ImportError:
            self.logger.warning("BeautifulSoup 未安裝，跳過網頁爬蟲")
            return []
        except Exception as e:
            self.logger.error(f"網頁爬蟲新聞獲取失敗: {e}")
            return []
    
    async def _extract_article_date(self, element, source_url: str) -> str:
        """從新聞元素中提取實際發布時間"""
        try:
            # 嘗試從父元素中查找時間信息
            parent = element.parent
            if parent:
                # 查找常見的時間選擇器
                time_selectors = [
                    'time',
                    '.time',
                    '.date',
                    '.timestamp',
                    '[datetime]',
                    '.published',
                    '.publish-date'
                ]
                
                for selector in time_selectors:
                    time_element = parent.select_one(selector)
                    if time_element:
                        # 嘗試從datetime屬性獲取
                        datetime_attr = time_element.get('datetime')
                        if datetime_attr:
                            return datetime_attr
                        
                        # 嘗試從文本內容獲取
                        time_text = time_element.get_text(strip=True)
                        if time_text:
                            # 嘗試解析時間文本
                            parsed_time = self._parse_time_text(time_text)
                            if parsed_time:
                                return parsed_time
            
            # 如果無法提取時間，使用當前時間作為fallback
            return datetime.now().isoformat()
            
        except Exception as e:
            self.logger.warning(f"提取文章時間失敗: {e}")
            return datetime.now().isoformat()
    
    def _parse_time_text(self, time_text: str) -> Optional[str]:
        """解析時間文本為ISO格式"""
        try:
            import re
            from dateutil import parser
            
            # 清理時間文本
            time_text = time_text.strip()
            
            # 嘗試直接解析
            try:
                parsed_date = parser.parse(time_text)
                return parsed_date.isoformat()
            except:
                pass
            
            # 嘗試匹配常見格式
            patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
                r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
                r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})',  # DD Mon YYYY
            ]
            
            for pattern in patterns:
                match = re.search(pattern, time_text)
                if match:
                    try:
                        parsed_date = parser.parse(match.group(0))
                        return parsed_date.isoformat()
                    except:
                        continue
            
            return None
            
        except Exception as e:
            self.logger.warning(f"解析時間文本失敗: {e}")
            return None
    
    async def get_market_overview(self) -> Dict:
        """獲取市場概況"""
        try:
            # 獲取主要指數新聞
            major_indices = ['^GSPC', '^DJI', '^IXIC', '^VIX']
            market_news = []
            
            for index in major_indices:
                news = await self.get_market_news(index, days=1)
                market_news.append(news)
            
            return {
                "market_overview": market_news,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"市場概況獲取失敗: {e}")
            return {"error": str(e)}

class EnhancedNewsAnalyzer:
    """增強版新聞分析器"""
    
    def __init__(self):
        self.news_analyzer = NewsAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    async def comprehensive_analysis(self, ticker: str) -> Dict:
        """綜合新聞分析"""
        try:
            # 獲取多種新聞源
            news_data = await self.news_analyzer.get_market_news(ticker, days=7)
            social_sentiment = await self.news_analyzer.get_social_sentiment(ticker)
            market_overview = await self.news_analyzer.get_market_overview()
            
            # 綜合分析
            comprehensive_score = self._calculate_comprehensive_sentiment(
                news_data, social_sentiment, market_overview
            )
            
            return {
                "ticker": ticker,
                "news_analysis": news_data,
                "social_sentiment": social_sentiment,
                "market_overview": market_overview,
                "comprehensive_sentiment": comprehensive_score,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"綜合新聞分析失敗: {e}")
            return {"ticker": ticker, "error": str(e)}
    
    def _calculate_comprehensive_sentiment(self, news_data: Dict, 
                                         social_sentiment: Dict, 
                                         market_overview: Dict) -> Dict:
        """計算綜合情緒分數"""
        try:
            # 權重分配
            news_weight = 0.5
            social_weight = 0.3
            market_weight = 0.2
            
            # 新聞情緒分數
            news_score = news_data.get('sentiment_score', 0) / 100  # 轉換為 -1 到 1
            
            # 社交媒體情緒分數
            social_score = social_sentiment.get('overall_social_sentiment', 0)
            
            # 市場情緒分數（簡化）
            market_score = 0  # 可以根據市場概況計算
            
            # 加權平均
            comprehensive_score = (
                news_score * news_weight + 
                social_score * social_weight + 
                market_score * market_weight
            )
            
            return {
                "score": round(comprehensive_score, 3),
                "confidence": self._calculate_confidence(news_data, social_sentiment),
                "trend": "positive" if comprehensive_score > 0.1 else "negative" if comprehensive_score < -0.1 else "neutral",
                "factors": {
                    "news_impact": news_score,
                    "social_impact": social_score,
                    "market_impact": market_score
                }
            }
            
        except Exception as e:
            self.logger.error(f"綜合情緒計算失敗: {e}")
            return {"score": 0, "confidence": 0, "trend": "neutral"}
    
    def _calculate_confidence(self, news_data: Dict, social_sentiment: Dict) -> float:
        """計算分析置信度"""
        try:
            news_count = news_data.get('news_count', 0)
            social_mentions = social_sentiment.get('mention_count', 0)
            
            # 基於數據量計算置信度
            confidence = min(1.0, (news_count * 0.1 + social_mentions * 0.01))
            return round(confidence, 2)
            
        except Exception as e:
            self.logger.error(f"置信度計算失敗: {e}")
            return 0.5
