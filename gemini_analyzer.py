# gemini_analyzer.py - Gemini 2.5 Flash 推理分析器

import openai
import json
import logging
from typing import Dict, List
from datetime import datetime
from news_analyzer import EnhancedNewsAnalyzer

class GeminiStockAnalyzer:
    """使用 Gemini 2.5 Flash 推理能力的股票分析器"""
    
    def __init__(self, openrouter_api_key: str):
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key
        )
        self.model = "google/gemini-2.5-flash-preview-09-2025"
        self.news_analyzer = EnhancedNewsAnalyzer()
        self.logger = logging.getLogger(__name__)
    
    async def analyze_stock_with_reasoning(self, ticker: str, technical_data: Dict) -> Dict:
        """使用 Gemini 推理能力分析股票"""
        try:
            # 獲取新聞和市場情緒數據
            news_analysis = await self.news_analyzer.comprehensive_analysis(ticker)
            
            # 構建包含新聞數據的分析提示
            prompt = self._build_enhanced_analysis_prompt(ticker, technical_data, news_analysis)
            
            # 使用推理能力進行分析
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3000
            )
            
            # 提取分析結果
            message = response.choices[0].message
            content = message.content
            
            # 解析AI分析結果
            ai_analysis = self._parse_ai_response(content)
            
            return {
                "ticker": ticker,
                "ai_analysis": ai_analysis,
                "news_analysis": news_analysis,
                "reasoning_details": [],
                "reasoning_text": content[:500] + "..." if len(content) > 500 else content,
                "confidence": ai_analysis.get("confidence", 0),
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Gemini分析失敗: {e}")
            return {
                "error": f"Gemini分析失敗: {str(e)}",
                "success": False
            }
    
    def _build_enhanced_analysis_prompt(self, ticker: str, technical_data: Dict, news_analysis: Dict) -> str:
        """構建包含新聞數據的增強分析提示"""
        news_summary = ""
        if news_analysis.get('news_analysis', {}).get('articles'):
            articles = news_analysis['news_analysis']['articles'][:5]  # 取前5篇新聞
            news_summary = "\n\n最新市場新聞：\n"
            for i, article in enumerate(articles, 1):
                title = article.get('title', 'N/A')
                source = article.get('source', 'Unknown Source')
                url = article.get('url', '')
                
                # 確保URL有效且格式正確
                verified = article.get('link_verified', False)
                if url and url.startswith('http'):
                    # 創建可點擊的HTML連結
                    clickable_link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
                    if verified:
                        clickable_link += " [已驗證]"
                    news_summary += f"{i}. {clickable_link}\n"
                else:
                    news_summary += f"{i}. {title} [無有效連結]\n"
                
                news_summary += f"   來源: {source}\n"
                
                # 添加發布時間
                published_time = article.get('publishedAt', article.get('published_at', ''))
                if published_time:
                    try:
                        from datetime import datetime
                        if 'T' in published_time:
                            pub_date = datetime.fromisoformat(published_time.replace('Z', '+00:00'))
                            news_summary += f"   發布時間: {pub_date.strftime('%Y-%m-%d %H:%M')}\n"
                    except:
                        pass
                
                if article.get('description'):
                    news_summary += f"   摘要: {article.get('description', '')[:150]}...\n"
                news_summary += "\n"
        
        sentiment_info = ""
        if news_analysis.get('comprehensive_sentiment'):
            sentiment = news_analysis['comprehensive_sentiment']
            sentiment_info = f"""
市場情緒分析：
- 綜合情緒分數: {sentiment.get('score', 'N/A')}
- 情緒趨勢: {sentiment.get('trend', 'N/A')}
- 分析置信度: {sentiment.get('confidence', 'N/A')}
"""
        
        # 新增風險評估資訊
        risk_info = ""
        if news_analysis.get('risk_analysis'):
            risk = news_analysis['risk_analysis']
            risk_info = f"""
風險評估：
- 波動性風險: {risk.get('volatility_risk', 'N/A')}
- 流動性風險: {risk.get('liquidity_risk', 'N/A')}
- 相關性風險: {risk.get('correlation_risk', 'N/A')}
- 整體風險等級: {risk.get('overall_risk', 'N/A')}
"""
        
        return f"""
請為 {ticker} 股票提供一份全面的投資分析報告。

技術分析數據：
- 綜合評分: {technical_data.get('final_score', 'N/A')}
- RS評級: {technical_data.get('rs_rating', 'N/A')}
- RSI: {technical_data.get('rsi', 'N/A')}
- MACD: {technical_data.get('macd', 'N/A')}
- 形態識別: {technical_data.get('pattern_summary', 'N/A')}
- 市場趨勢: {technical_data.get('market_trend', 'N/A')}
- 建議止損: {technical_data.get('recommended_stop_loss', 'N/A')}
{sentiment_info}{risk_info}{news_summary}

請提供一份約12句話的綜合分析報告，包含以下維度：

**分析維度權重分配**：
- 技術分析 (50%)：RSI、MACD、形態識別等技術指標
- 新聞分析 (20%)：最新新聞對股價的影響
- 市場情緒 (15%)：投資者情緒和市場氛圍
- 風險評估 (15%)：波動性、流動性、相關性風險

**分析報告結構**：
1. **開場總結**：基於技術指標的整體評估
2. **技術分析**：RSI、MACD等指標的含義和信號
3. **形態分析**：VCP或Cup & Handle形態的意義和突破概率
4. **新聞影響**：引用具體新聞標題和對股價的影響
5. **市場情緒**：當前市場對該股票的看法和投資者情緒
6. **風險評估**：波動性、流動性、相關性等風險因素
7. **機會分析**：潛在的上漲機會和催化劑
8. **投資建議**：明確的買入/持有/賣出建議
9. **時機建議**：最佳進場或出場時機
10. **風險管理**：止損建議和風險控制措施
11. **總結**：綜合評估和最終建議

請確保：
- 使用專業但易懂的語言，不要使用任何emoji表情符號
- 在適當的地方引用新聞來源，並使用HTML格式的超連結：<a href="URL" target="_blank" rel="noopener noreferrer">新聞標題</a>
- 提供完整的分析，不要截斷文字
- 每段分析都要有具體的數據支撐
- 所有新聞連結都應該是可點擊的HTML格式，包含rel="noopener noreferrer"安全屬性
- 明確標示各維度的分析結果和權重影響
- 保持專業的投資分析報告風格
- 確保所有引用的新聞連結都是最新且可訪問的
- 在分析中明確提及新聞對股價的潛在影響
"""

    def _build_analysis_prompt(self, ticker: str, technical_data: Dict) -> str:
        """構建分析提示"""
        return f"""
作為一個專業的股票分析師，請使用深度推理來分析 {ticker} 股票。

技術分析數據：
- 綜合評分: {technical_data.get('final_score', 'N/A')}
- RS評級: {technical_data.get('rs_rating', 'N/A')}
- RSI: {technical_data.get('rsi', 'N/A')}
- MACD: {technical_data.get('macd', 'N/A')}
- 形態識別: {technical_data.get('pattern_summary', 'N/A')}
- 市場趨勢: {technical_data.get('market_trend', 'N/A')}
- 建議止損: {technical_data.get('recommended_stop_loss', 'N/A')}

請進行以下深度分析：

1. **技術分析推理**：
   - 分析技術指標的綜合表現
   - 識別關鍵支撐和阻力位
   - 評估趨勢強度

2. **形態分析推理**：
   - 深入分析識別到的形態
   - 評估形態的可靠性和突破概率
   - 預測可能的價格目標

3. **風險評估推理**：
   - 分析當前風險水平
   - 識別潛在風險因素
   - 評估止損建議的合理性

4. **投資建議推理**：
   - 綜合所有因素給出投資建議
   - 評估投資時機
   - 提供具體的操作策略

請以JSON格式返回分析結果，包含：
- "ai_score": AI綜合評分 (0-100)
- "confidence": 分析置信度 (0-100)
- "recommendation": 投資建議
- "reasoning_summary": 推理摘要
- "key_factors": 關鍵因素列表
- "risk_assessment": 風險評估
- "opportunity_assessment": 機會評估
- "timing_advice": 時機建議
"""
    
    def _parse_ai_response(self, content: str) -> Dict:
        """解析AI響應"""
        # 清理內容，移除可能的JSON標記
        cleaned_content = content.strip()
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content.replace('```json', '').replace('```', '').strip()
        elif cleaned_content.startswith('```'):
            cleaned_content = cleaned_content.replace('```', '').strip()
        
        try:
            # 嘗試解析JSON響應
            if cleaned_content.startswith('{'):
                return json.loads(cleaned_content)
            else:
                # 處理純自然語言響應
                return {
                    "ai_score": 75,
                    "confidence": 80,
                    "recommendation": "Hold",
                    "natural_analysis": cleaned_content,  # 完整的自然語言分析
                    "reasoning_summary": cleaned_content[:300] + "..." if len(cleaned_content) > 300 else cleaned_content,
                    "key_factors": ["技術指標分析", "形態識別", "風險評估"],
                    "risk_assessment": "中等風險",
                    "opportunity_assessment": "潛在機會",
                    "timing_advice": "建議觀望"
                }
        except json.JSONDecodeError:
            return {
                "ai_score": 70,
                "confidence": 70,
                "recommendation": "Hold",
                "natural_analysis": cleaned_content,  # 完整的自然語言分析
                "reasoning_summary": cleaned_content,
                "key_factors": [],
                "risk_assessment": "需要進一步分析",
                "opportunity_assessment": "需要進一步分析",
                "timing_advice": "建議謹慎"
            }
    
    def _extract_reasoning_text(self, reasoning_details: List) -> str:
        """提取推理文本"""
        if not reasoning_details:
            return "無推理過程"
        
        reasoning_texts = []
        for detail in reasoning_details:
            if hasattr(detail, 'text'):
                reasoning_texts.append(detail.text)
            elif isinstance(detail, dict) and 'text' in detail:
                reasoning_texts.append(detail['text'])
        
        return "\n".join(reasoning_texts) if reasoning_texts else "推理過程不可用"

class GeminiEnhancedAnalyzer:
    """Gemini增強分析器整合類"""
    
    def __init__(self, openrouter_api_key: str):
        self.gemini_analyzer = GeminiStockAnalyzer(openrouter_api_key)
        self.logger = logging.getLogger(__name__)
    
    async def enhanced_analysis(self, ticker: str, technical_data: Dict) -> Dict:
        """執行Gemini增強分析"""
        try:
            # 執行Gemini推理分析
            gemini_results = await self.gemini_analyzer.analyze_stock_with_reasoning(ticker, technical_data)
            
            if not gemini_results.get('success'):
                return technical_data  # 回退到技術分析
            
            # 融合技術分析和Gemini分析
            enhanced_score = self._fuse_scores(technical_data, gemini_results)
            
            return {
                **technical_data,
                **gemini_results,
                "enhanced_score": enhanced_score,
                "gemini_reasoning": gemini_results.get('reasoning_text', ''),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Gemini增強分析失敗: {e}")
            return technical_data
    
    def _fuse_scores(self, technical_data: Dict, gemini_results: Dict) -> float:
        """融合技術分析和Gemini分析評分"""
        from config import AI_ANALYSIS_WEIGHTS
        
        technical_score = technical_data.get('final_score', 0)
        ai_analysis = gemini_results.get('ai_analysis', {})
        ai_score = ai_analysis.get('ai_score', 0)
        confidence = ai_analysis.get('confidence', 0) / 100
        
        # 多維度融合評分
        technical_weight = AI_ANALYSIS_WEIGHTS["TECHNICAL_ANALYSIS"] / 100
        news_weight = AI_ANALYSIS_WEIGHTS["NEWS_ANALYSIS"] / 100
        sentiment_weight = AI_ANALYSIS_WEIGHTS["MARKET_SENTIMENT"] / 100
        risk_weight = AI_ANALYSIS_WEIGHTS["RISK_ASSESSMENT"] / 100
        
        # 計算各維度分數
        technical_component = technical_score * technical_weight
        news_component = ai_score * news_weight * confidence
        sentiment_component = ai_score * sentiment_weight * confidence
        risk_component = ai_score * risk_weight * confidence
        
        # 融合所有維度
        fused_score = (technical_component + news_component + 
                      sentiment_component + risk_component)
        
        return min(100, max(0, fused_score))
