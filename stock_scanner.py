# stock_scanner.py - 形態股掃描後台任務

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3
import logging
from typing import List, Dict, Tuple
from analyzer import GrowthSignalAnalyzer
import time

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockScanner:
    """股票掃描器 - 定期掃描形態股"""
    
    def __init__(self, db_path: str = "stock_analysis.db"):
        self.db_path = db_path
        self.analyzer = GrowthSignalAnalyzer()
        self.setup_database()
        self.scanned_today = set()  # 今日已掃描股票記錄
        
        # 全球500大企業股票池 (500+ 股票)
        self.popular_stocks = [
            # 美國科技巨頭 (FAANG + 大型科技股)
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL', 'UBER', 'SPOT', 'ORCL', 'CSCO',
            'IBM', 'QCOM', 'TXN', 'AVGO', 'MU', 'AMAT', 'SNOW', 'PLTR', 'CRWD',
            'ZS', 'OKTA', 'NET', 'DDOG', 'MDB', 'TWLO', 'ZM', 'DOCU', 'WDAY',
            'NOW', 'TEAM', 'SPLK', 'ESTC', 'DBX', 'BOX', 'PINS', 'SNAP', 'TWTR',
            
            # 美國金融服務
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'V', 'MA', 'COF',
            'USB', 'PNC', 'TFC', 'BK', 'STT', 'BLK', 'SCHW', 'ICE', 'CME',
            'NDAQ', 'MCO', 'SPGI', 'FIS', 'FISV', 'GPN', 'COIN', 'MSTR',
            
            # 美國醫療保健
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'LLY', 'DHR',
            'BMY', 'AMGN', 'GILD', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'ILMN',
            'ISRG', 'DXCM', 'ZTS', 'EW', 'BSX', 'MDT', 'SYK', 'CVS', 'CI',
            
            # 美國消費品及零售
            'KO', 'PEP', 'WMT', 'PG', 'HD', 'MCD', 'SBUX', 'NKE', 'DIS',
            'CMCSA', 'VZ', 'T', 'CHTR', 'ROKU', 'EBAY', 'ETSY', 'SHOP',
            'TGT', 'LOW', 'COST', 'TJX', 'LULU', 'ULTA', 'RH', 'DECK',
            
            # 美國工業及製造業
            'BA', 'CAT', 'GE', 'HON', 'MMM', 'RTX', 'UPS', 'FDX', 'LMT',
            'NOC', 'GD', 'TDG', 'ETN', 'EMR', 'ITW', 'PH', 'DE', 'CMI',
            
            # 美國能源
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'KMI', 'WMB', 'PSX',
            'VLO', 'MPC', 'HES', 'DVN', 'PXD', 'MRO', 'APA', 'HAL', 'BKR',
            
            # 美國公用事業
            'NEE', 'DUK', 'SO', 'D', 'EXC', 'AEP', 'XEL', 'SRE', 'ES',
            'PEG', 'WEC', 'AWK', 'ED', 'ETR', 'FE', 'AEE', 'PPL', 'CMS',
            
            # 美國房地產 (REITs)
            'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'EXR', 'AVB', 'EQR',
            'MAA', 'UDR', 'CPT', 'ESS', 'BXP', 'SLG', 'KIM', 'REG',
            
            # 美國材料及化學
            'LIN', 'APD', 'SHW', 'DD', 'DOW', 'ECL', 'PPG', 'NEM', 'FCX',
            'SCCO', 'NUE', 'X', 'CLF', 'STLD', 'CMC', 'RS', 'CF', 'MOS',
            
            # 中國概念股 (ADR)
            'BABA', 'JD', 'PDD', 'BIDU', 'NTES', 'BILI', 'TME', 'VIPS',
            'YMM', 'TAL', 'EDU', 'GOTU', 'IQ', 'DIDI', 'XPEV', 'NIO', 'LI',
            
            # 歐洲大型企業 (ADR)
            'ASML', 'SAP', 'NVO', 'NESN', 'RHHBY', 'UL', 'SNY', 'GSK',
            'AZN', 'BP', 'RDS.A', 'RDS.B', 'VOD', 'BT', 'ING', 'DB',
            'CS', 'UBS', 'BCS', 'HSBC', 'RY', 'TD', 'BMO', 'BNS', 'CM',
            
            # 日本企業 (ADR)
            'TM', 'SONY', 'NTT', 'MUFG', 'SMFG', 'MFG', 'HMC', 'FUJIY',
            'KYOCY', 'NTDOY', 'SFM', 'HTHIY', 'TKOMY', 'CANNY',
            
            # 韓國企業
            'TSM', 'LPL', 'KB', 'SHI', 'PKX', 'WF',
            
            # 印度企業 (ADR)
            'INFY', 'WIT', 'HDB', 'IBN', 'INDA', 'MINDX', 'TTM', 'RDY',
            
            # 巴西企業 (ADR)
            'VALE', 'ITUB', 'BBD', 'PBR', 'ABEV', 'SBS', 'UGP',
            
            # 澳洲及加拿大企業
            'BHP', 'RIO', 'SHOP', 'CNQ', 'SU', 'ENB', 'TRP', 'PPL',
            
            # 新興成長股及特殊情況
            'RIVN', 'LCID', 'F', 'GM', 'SPCE', 'MAXR', 'IRDM', 'VSAT',
            'GILT', 'KTOS', 'AJRD', 'HWM', 'LHX', 'LDOS', 'TXT',
            
            # 半導體及技術硬體
            'LRCX', 'KLAC', 'MCHP', 'ADI', 'MRVL', 'SWKS', 'QRVO', 'SLAB',
            'ON', 'MPWR', 'MXIM', 'XLNX', 'ALTR', 'LSCC', 'CRUS', 'RMBS',
            
            # 生物科技及醫療設備
            'TDOC', 'VEEV', 'IQVIA', 'A', 'HOLX', 'ALGN', 'IDXX', 'MTD',
            'TECH', 'BDX', 'BAX', 'ZBH', 'STE', 'RMD', 'PODD', 'NVTA',
            
            # 雲端及軟體服務
            'AMZN', 'MSFT', 'GOOGL', 'CRM', 'ADBE', 'INTU', 'CTXS',
            'VMW', 'PANW', 'FTNT', 'CHKP', 'CYBR', 'FEYE', 'VRNS',
            
            # 電子商務及數位媒體
            'AMZN', 'EBAY', 'ETSY', 'W', 'OSTK', 'GRPN', 'YELP', 'TRIP',
            'EXPE', 'BKNG', 'MAR', 'HLT', 'H', 'WH', 'RCL', 'CCL',
            
            # 食品及飲料
            'KO', 'PEP', 'MDLZ', 'GIS', 'K', 'CPB', 'CAG', 'SJM',
            'HSY', 'MKC', 'CLX', 'CHD', 'CL', 'KMB', 'PG', 'UL',
            
            # 運輸及物流
            'UPS', 'FDX', 'XPO', 'CHRW', 'EXPD', 'JBHT', 'KNX', 'ODFL',
            'SAIA', 'ARCB', 'WERN', 'MATX', 'HUBG', 'LSTR', 'GXO',
            
            # 零售及消費服務
            'WMT', 'TGT', 'COST', 'HD', 'LOW', 'TJX', 'ROST', 'DG',
            'DLTR', 'BBY', 'GPS', 'M', 'JWN', 'KSS', 'DSW', 'FL',
            
            # 金融科技 (FinTech)
            'SQ', 'PYPL', 'AFRM', 'SOFI', 'LC', 'UPST', 'HOOD', 'COIN',
            'NU', 'PAGS', 'STNE', 'MELI', 'SE', 'GRAB', 'DIDI',
            
            # 旅遊及休閒
            'DIS', 'NFLX', 'CMCSA', 'T', 'VZ', 'CHTR', 'DISH', 'SIRI',
            'LYV', 'MSG', 'MSGS', 'VIAC', 'DISCA', 'DISCK', 'FOX', 'FOXA'
        ]
    
    def setup_database(self):
        """設置資料庫表格"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 創建形態股表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                confidence_score REAL,
                detection_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                price_at_detection REAL,
                stop_loss_price REAL,
                risk_score REAL,
                analysis_data TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # 創建掃描歷史表格
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_stocks_scanned INTEGER,
                patterns_found INTEGER,
                scan_duration REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("資料庫表格設置完成")
    
    def scan_single_stock(self, ticker: str) -> Dict:
        """掃描單一股票"""
        try:
            logger.info(f"掃描股票: {ticker}")
            
            # 獲取股票數據
            stock_data = self.analyzer.get_stock_data(ticker, period="1y")
            if stock_data is None or len(stock_data) < 60:
                return {"ticker": ticker, "patterns": [], "error": "數據不足"}
            
            patterns_found = []
            
            # 檢測基本 VCP 形態
            basic_vcp_detected, basic_vcp_status, basic_vcp_stop_loss = self.analyzer.detect_vcp_pattern(stock_data)
            
            # 檢測增強 VCP 形態
            enhanced_vcp_detected, enhanced_vcp_status, enhanced_vcp_details = self.analyzer.detect_enhanced_vcp(stock_data)
            
            # 檢測KC形態
            kc_data = self.analyzer.calculate_keltner_channels(stock_data)
            kc_signal, kc_score, kc_strategy = self.analyzer.analyze_keltner_signals(stock_data, kc_data)
            
            # 計算綜合信心度
            confidence_factors = {
                'vcp_basic': 20 if basic_vcp_detected else 0,
                'vcp_enhanced': enhanced_vcp_details.get('score', 0) * 0.3 if enhanced_vcp_detected else 0,
                'kc_signal': kc_score * 0.25 if kc_score > 60 else 0,
                'kc_strategy_bonus': 15 if kc_strategy in ['strong_bullish', 'consolidation_bullish'] else 0
            }
            
            # 如果任一VCP檢測成功，就加入推薦
            if basic_vcp_detected or enhanced_vcp_detected:
                # 新的信心度計算
                base_confidence = sum(confidence_factors.values())
                
                if enhanced_vcp_detected:
                    status = enhanced_vcp_status
                    if basic_vcp_detected:
                        status = f"{basic_vcp_status} + {enhanced_vcp_status}"
                        base_confidence += 10  # 雙重VCP獎勵
                else:
                    status = basic_vcp_status
                
                # KC策略增強
                if kc_strategy == 'strong_bullish':
                    status += " + KC強勢突破"
                    base_confidence += 10
                elif kc_strategy == 'consolidation_bullish':
                    status += " + KC整理待突破"
                    base_confidence += 5
                
                final_confidence = min(95, max(50, base_confidence))
                
                patterns_found.append({
                    "type": "VCP",
                    "confidence": final_confidence,
                    "status": status,
                    "details": dict({
                        'kc_strategy': kc_strategy,
                        'kc_score': kc_score,
                        'confidence_breakdown': confidence_factors
                    }, **(enhanced_vcp_details if enhanced_vcp_detected else {}))
                })
            
            # 檢測 Cup & Handle 形態
            cup_handle_detected, cup_handle_status = self.analyzer.detect_cup_handle_pattern(stock_data)
            if cup_handle_detected:
                # 新的Cup & Handle信心度計算
                base_cup_confidence = 60
                if "突破在即" in cup_handle_status:
                    base_cup_confidence = 75
                elif "形成" in cup_handle_status:
                    base_cup_confidence = 65
                
                # KC增強
                if kc_strategy == 'strong_bullish':
                    base_cup_confidence += 15
                    cup_handle_status += " + KC強勢突破"
                elif kc_strategy == 'consolidation_bullish':
                    base_cup_confidence += 10
                    cup_handle_status += " + KC整理待突破"
                
                final_cup_confidence = min(90, base_cup_confidence)
                    
                patterns_found.append({
                    "type": "Cup_Handle",
                    "confidence": final_cup_confidence,
                    "status": cup_handle_status,
                    "details": {
                        'kc_strategy': kc_strategy,
                        'kc_score': kc_score
                    }
                })
            
            # 純KC形態（無VCP或Cup&Handle時）
            elif kc_strategy in ['strong_bullish', 'consolidation_bullish', 'oversold_opportunity']:
                kc_confidence = kc_score * 0.8  # KC單獨信心度較低
                
                patterns_found.append({
                    "type": "KC",
                    "confidence": min(80, max(50, kc_confidence)),
                    "status": kc_signal,
                    "details": {
                        'kc_strategy': kc_strategy,
                        'kc_score': kc_score
                    }
                })
            
            # 計算風險評分和止損點
            risk_assessment = self.calculate_risk_assessment(stock_data)
            
            return {
                "ticker": ticker,
                "patterns": patterns_found,
                "risk_assessment": risk_assessment,
                "current_price": stock_data['Close'].iloc[-1],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"掃描 {ticker} 時發生錯誤: {e}")
            return {"ticker": ticker, "patterns": [], "error": str(e)}
    
    def calculate_risk_assessment(self, stock_data: pd.DataFrame) -> Dict:
        """計算風險評估"""
        try:
            current_price = stock_data['Close'].iloc[-1]
            
            # 計算最近20日的最低點作為支撐
            recent_low = stock_data['Low'].tail(20).min()
            
            # 計算止損點 (支撐位下方5%)
            stop_loss = recent_low * 0.95
            
            # 計算風險評分 (基於波動率)
            returns = stock_data['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 年化波動率
            
            # 風險等級
            if volatility < 0.2:
                risk_level = "低"
                risk_score = 1
            elif volatility < 0.4:
                risk_level = "中"
                risk_score = 2
            else:
                risk_level = "高"
                risk_score = 3
            
            return {
                "stop_loss_price": round(stop_loss, 2),
                "support_level": round(recent_low, 2),
                "risk_level": risk_level,
                "risk_score": risk_score,
                "volatility": round(volatility, 3),
                "max_loss_percentage": round((current_price - stop_loss) / current_price * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"風險評估計算錯誤: {e}")
            return {
                "stop_loss_price": 0,
                "support_level": 0,
                "risk_level": "未知",
                "risk_score": 3,
                "volatility": 0,
                "max_loss_percentage": 0
            }
    
    def batch_scan_stocks(self, stock_list: List[str] = None, max_stocks: int = 50) -> Dict:
        """批次掃描股票 - 動態選擇"""
        if stock_list is None:
            # 動態選擇股票：隨機選擇 + 熱門股票
            stock_list = self.get_dynamic_stock_list(max_stocks)
        
        start_time = time.time()
        results = {
            "scan_date": datetime.now().isoformat(),
            "total_scanned": len(stock_list),
            "patterns_found": 0,
            "pattern_stocks": [],
            "scan_duration": 0
        }
        
        logger.info(f"開始批次掃描 {len(stock_list)} 支股票")
        
        for i, ticker in enumerate(stock_list):
            try:
                # 掃描單一股票
                scan_result = self.scan_single_stock(ticker)
                
                if scan_result.get("success") and scan_result.get("patterns"):
                    # 儲存到資料庫 (只儲存符合範選條件的)
                    if self.meets_swing_trading_criteria(scan_result):
                        self.save_pattern_stock(scan_result)
                        results["pattern_stocks"].append(scan_result)
                        results["patterns_found"] += len(scan_result["patterns"])
                    else:
                        logger.debug(f"跳過 {scan_result['ticker']}: 不符合 Swing Trading 範選條件")
                
                # 進度顯示
                if (i + 1) % 10 == 0:
                    logger.info(f"已掃描 {i + 1}/{len(stock_list)} 支股票")
                
                # 避免過於頻繁的API請求
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"掃描 {ticker} 失敗: {e}")
                continue
        
        results["scan_duration"] = round(time.time() - start_time, 2)
        
        # 儲存掃描歷史
        self.save_scan_history(results)
        
        # 更新Google Sheets
        self.update_google_sheets(results)
        
        qualified_stocks = len(results["pattern_stocks"])
        total_patterns = results["patterns_found"]
        
        logger.info(f"✅ 掃描完成: 符合範選 {qualified_stocks} 支股票，{total_patterns} 個形態")
        logger.info(f"🎯 Swing Trading 範選率: {qualified_stocks/len(stock_list)*100:.1f}%")
        
        return results
    
    def update_google_sheets(self, results: Dict):
        """更新Google Sheets"""
        try:
            from google_sheets_integration import update_sheets_with_scan_results
            success = update_sheets_with_scan_results(results)
            if success:
                logger.info("✅ Google Sheets更新成功")
            else:
                logger.info("📊 Google Sheets整合未啟用或更新失敗")
        except ImportError:
            logger.info("📊 Google Sheets整合模組未安裝")
        except Exception as e:
            logger.warning(f"⚠️ Google Sheets更新錯誤: {e}")
    
    def meets_swing_trading_criteria(self, scan_result: Dict) -> bool:
        """檢查是否符合 Swing Trading 範選條件"""
        try:
            ticker = scan_result["ticker"]
            current_price = scan_result["current_price"]
            patterns = scan_result["patterns"]
            risk_assessment = scan_result["risk_assessment"]
            
            # 範選條件 1: 價格範圍 ($5-$500)
            if current_price < 5 or current_price > 500:
                return False
            
            # 範選條件 2: 最高信心度闾值 (70%+)
            max_confidence = max([p["confidence"] for p in patterns], default=0)
            if max_confidence < 70:
                return False
            
            # 範選條件 3: 風險控制 (最大損失 ≤10%)
            if risk_assessment["max_loss_percentage"] > 10:
                return False
            
            # 範選條件 4: 波動率範圍 (15%-60%)
            volatility = risk_assessment["volatility"]
            if volatility < 0.15 or volatility > 0.60:
                return False
            
            # 範選條件 5: 形態品質範選
            has_quality_pattern = False
            for pattern in patterns:
                pattern_type = pattern["type"]
                confidence = pattern["confidence"]
                details = pattern.get("details", {})
                
                # VCP 形態: 高信心度 + KC 支持
                if pattern_type == "VCP" and confidence >= 75:
                    kc_strategy = details.get("kc_strategy", "")
                    if kc_strategy in ["strong_bullish", "consolidation_bullish"]:
                        has_quality_pattern = True
                        break
                
                # Cup & Handle: 中高信心度
                elif pattern_type == "Cup_Handle" and confidence >= 70:
                    has_quality_pattern = True
                    break
                
                # KC 獨立形態: 高信心度 + 強勢信號
                elif pattern_type == "KC" and confidence >= 75:
                    kc_strategy = details.get("kc_strategy", "")
                    if kc_strategy == "strong_bullish":
                        has_quality_pattern = True
                        break
            
            if not has_quality_pattern:
                return False
            
            # 範選條件 6: 排除問題股票
            problem_tickers = ["SQ", "NKLA", "RIDE", "WKHS"]  # 已知問題股票
            if ticker in problem_tickers:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"範選條件檢查錯誤 {ticker}: {e}")
            return False
    
    def save_pattern_stock(self, scan_result: Dict):
        """儲存符合範選條件的形態股到資料庫"""
        # 先檢查是否符合 Swing Trading 範選條件
        if not self.meets_swing_trading_criteria(scan_result):
            logger.debug(f"股票 {scan_result['ticker']} 不符合 Swing Trading 範選條件，跳過")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        ticker = scan_result["ticker"]
        current_price = scan_result["current_price"]
        risk_assessment = scan_result["risk_assessment"]
        
        for pattern in scan_result["patterns"]:
            cursor.execute('''
                INSERT INTO pattern_stocks 
                (ticker, pattern_type, confidence_score, price_at_detection, 
                 stop_loss_price, risk_score, analysis_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                ticker,
                pattern["type"],
                pattern["confidence"],
                current_price,
                risk_assessment["stop_loss_price"],
                risk_assessment["risk_score"],
                str(pattern["details"])
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 符合範選: {ticker} - 信心度: {max([p['confidence'] for p in scan_result['patterns']]):.1f}%")
    
    def save_scan_history(self, results: Dict):
        """儲存掃描歷史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scan_history 
            (total_stocks_scanned, patterns_found, scan_duration)
            VALUES (?, ?, ?)
        ''', (
            results["total_scanned"],
            results["patterns_found"],
            results["scan_duration"]
        ))
        
        conn.commit()
        conn.close()
    
    def get_recommended_stocks(self, limit: int = 10) -> List[Dict]:
        """獲取推薦股票，合併同一股票的多個形態，避免重複"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ticker, pattern_type, confidence_score, price_at_detection,
                   stop_loss_price, risk_score, detection_date
            FROM pattern_stocks 
            WHERE is_active = 1 
            ORDER BY ticker, confidence_score DESC, detection_date DESC
        ''')
        
        # 合併同一股票的多個形態
        stock_patterns = {}
        for row in cursor.fetchall():
            ticker = row[0]
            if ticker not in stock_patterns:
                stock_patterns[ticker] = {
                    "ticker": ticker,
                    "pattern_types": set(),  # 使用set去重
                    "confidence_score": row[2],
                    "current_price": row[3],
                    "stop_loss_price": row[4],
                    "risk_score": row[5],
                    "detection_date": row[6]
                }
            stock_patterns[ticker]["pattern_types"].add(row[1])
            # 使用最高信心度
            if row[2] > stock_patterns[ticker]["confidence_score"]:
                stock_patterns[ticker]["confidence_score"] = row[2]
        
        # 轉換為結果格式
        results = []
        for ticker, data in stock_patterns.items():
            # 將set轉為排序列表
            pattern_types = sorted(list(data["pattern_types"]))
            results.append({
                "ticker": data["ticker"],
                "pattern_types": pattern_types,  # 傳遞列表而非字串
                "confidence_score": data["confidence_score"],
                "current_price": data["current_price"],
                "stop_loss_price": data["stop_loss_price"],
                "risk_score": data["risk_score"],
                "detection_date": data["detection_date"]
            })
        
        # 按信心度排序並去重
        results.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        # 確保不重複 - 只保留最高信心度的記錄
        seen_tickers = set()
        unique_results = []
        for result in results:
            if result["ticker"] not in seen_tickers:
                unique_results.append(result)
                seen_tickers.add(result["ticker"])
        
        conn.close()
        return unique_results[:limit]
    
    def get_dynamic_stock_list(self, max_stocks: int = 150) -> List[str]:
        """動態選擇股票列表 - 全球500大企業版"""
        import random
        
        total_available = len(self.popular_stocks)
        logger.info(f"🌍 可用股票池: {total_available} 支全球企業")
        
        # 分層選股策略 - 確保使用全部500支股票
        if max_stocks <= 50:
            # 小量掃描: 優先熱門股票
            priority_stocks = self.popular_stocks[:30]
            remaining_stocks = self.popular_stocks[30:150]
            random_stocks = random.sample(remaining_stocks, min(max_stocks - 30, len(remaining_stocks)))
            selected_stocks = priority_stocks + random_stocks
        
        elif max_stocks <= 100:
            # 中量掃描: 平衡選股
            priority_stocks = self.popular_stocks[:50]  # 前50支熱門
            remaining_stocks = self.popular_stocks[50:300]
            random_stocks = random.sample(remaining_stocks, min(max_stocks - 50, len(remaining_stocks)))
            selected_stocks = priority_stocks + random_stocks
        
        else:
            # 大量掃描: 全面覆蓋全球500大企業
            priority_stocks = self.popular_stocks[:80]  # 前80支熱門
            
            # 分類選股: 確保各地區各行業都有覆蓋
            us_tech = self.popular_stocks[80:150]        # 美國科技股
            us_finance = self.popular_stocks[150:200]    # 美國金融股
            us_healthcare = self.popular_stocks[200:250] # 美國醫療股
            international = self.popular_stocks[250:400] # 國際企業
            emerging = self.popular_stocks[400:]         # 新興市場
            
            # 按比例選擇，確保全球覆蓋
            remaining_slots = max_stocks - 80
            us_tech_count = min(20, len(us_tech))
            us_finance_count = min(15, len(us_finance))
            us_healthcare_count = min(15, len(us_healthcare))
            international_count = min(20, len(international))
            emerging_count = min(remaining_slots - us_tech_count - us_finance_count - us_healthcare_count - international_count, len(emerging))
            
            selected_stocks = priority_stocks + \
                            random.sample(us_tech, us_tech_count) + \
                            random.sample(us_finance, us_finance_count) + \
                            random.sample(us_healthcare, us_healthcare_count) + \
                            random.sample(international, international_count) + \
                            random.sample(emerging, max(0, emerging_count))
        
        # 打亂順序以避免偏差
        random.shuffle(selected_stocks)
        
        # 過濾已掃描的股票
        unscanned_stocks = [s for s in selected_stocks if s not in self.scanned_today]
        
        # 如果未掃描股票不足，從全部500支中選擇
        if len(unscanned_stocks) < max_stocks * 0.8:
            all_unscanned = [s for s in self.popular_stocks if s not in self.scanned_today]
            if len(all_unscanned) >= max_stocks:
                unscanned_stocks = random.sample(all_unscanned, max_stocks)
            else:
                unscanned_stocks = all_unscanned
        
        final_list = unscanned_stocks[:max_stocks]
        logger.info(f"🎯 選擇 {len(final_list)} 支未掃描股票 (今日已掃描: {len(self.scanned_today)}/總池: {total_available})")
        
        return final_list
    
    def cleanup_old_patterns(self, days: int = 7):
        """清理舊的形態記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pattern_stocks 
            SET is_active = 0 
            WHERE detection_date < datetime('now', '-{} days')
        '''.format(days))
        
        conn.commit()
        conn.close()
        logger.info(f"清理了 {days} 天前的形態記錄")

# 定時任務函數
def run_daily_scan():
    """每日掃描任務"""
    scanner = StockScanner()
    
    # 清理舊記錄
    scanner.cleanup_old_patterns()
    
    # 執行掃描
    results = scanner.batch_scan_stocks()
    
    logger.info(f"每日掃描完成: {results}")
    return results

if __name__ == "__main__":
    # 測試掃描器
    scanner = StockScanner()
    results = scanner.batch_scan_stocks(scanner.popular_stocks[:5])  # 測試前5支股票
    print("掃描結果:", results)
