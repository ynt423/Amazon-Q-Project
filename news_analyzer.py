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
            
            # 1. 嘗試Yahoo Finance API
            yahoo_articles = await self._get_yahoo_finance_news(ticker)
            if yahoo_articles:
                all_articles.extend(yahoo_articles)
            
            # 2. 如果文章不够，嘗試其他API
            if len(all_articles) < 3:
                if self.news_api_key:
                    result = await self._get_newsapi_news(ticker, days)
                    all_articles.extend(result.get('articles', []))
                elif self.alpha_vantage_key:
                    result = await self._get_alpha_vantage_news(ticker, days)
                    all_articles.extend(result.get('articles', []))
            
            # 3. 如果仍然不够，使用備用方案
            if len(all_articles) < 2:
                backup_result = await self._get_free_news(ticker, days)
                all_articles.extend(backup_result.get('articles', []))
            
            # 4. 驗證所有連結
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
            
            # 只保留前5篇
            final_articles = unique_articles[:5]
            
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
                'https://feeds.marketwatch.com/marketwatch/topstories/',
                'https://feeds.bloomberg.com/markets/news.rss',
                'https://www.cnbc.com/id/100003114/device/rss/rss.html',  # CNBC Markets
                'https://feeds.reuters.com/reuters/businessNews'  # Reuters Business
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
                            any(keyword in title_lower for keyword in ['market', 'stock', 'trading', 'earnings'])):
                            
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
                'localhost' in url):
                continue
            
            # 實際驗證連結（使用GET請求確保頁面存在）
            try:
                response = requests.get(url, timeout=8, allow_redirects=True)
                
                # 檢查狀態碼和頁面內容
                if (response.status_code < 400 and 
                    'not found' not in response.text.lower() and
                    'page not found' not in response.text.lower() and
                    len(response.text) > 1000):  # 確保有實際內容
                    
                    article['link_verified'] = True
                    article['last_verified'] = datetime.now().isoformat()
                    article['final_url'] = response.url
                    article['content_length'] = len(response.text)
                    verified_articles.append(article)
                    
            except Exception as e:
                self.logger.warning(f"連結驗證失敗 {url}: {e}")
                continue
        
        return verified_articles
    
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
