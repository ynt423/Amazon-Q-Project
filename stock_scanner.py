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
        
        # 擴大的股票掃描池 (200+ 股票)
        self.popular_stocks = [
            # 科技巨頭 (FAANG + 其他)
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL', 'UBER', 'SPOT', 'SQ',
            'ORCL', 'CSCO', 'IBM', 'QCOM', 'TXN', 'AVGO', 'MU', 'AMAT',
            'SNOW', 'PLTR', 'CRWD', 'ZS', 'OKTA', 'NET', 'DDOG', 'MDB',
            'TWLO', 'ZM', 'DOCU', 'WDAY', 'NOW', 'TEAM', 'SPLK', 'ESTC',
            
            # 金融股
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'V', 'MA',
            'COF', 'USB', 'PNC', 'TFC', 'BK', 'STT', 'BLK', 'SCHW',
            'ICE', 'CME', 'NDAQ', 'MCO', 'SPGI', 'FIS', 'FISV', 'GPN',
            
            # 醫療保健股
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'LLY',
            'DHR', 'BMY', 'AMGN', 'GILD', 'BIIB', 'REGN', 'VRTX', 'MRNA',
            'ILMN', 'ISRG', 'DXCM', 'ZTS', 'EW', 'BSX', 'MDT', 'SYK',
            
            # 消費股
            'KO', 'PEP', 'WMT', 'PG', 'HD', 'MCD', 'SBUX', 'NKE',
            'DIS', 'CMCSA', 'VZ', 'T', 'CHTR', 'NFLX', 'ROKU', 'SPOT',
            'AMZN', 'EBAY', 'ETSY', 'SHOP', 'SQ', 'PYPL', 'V', 'MA',
            
            # 工業股
            'BA', 'CAT', 'GE', 'HON', 'MMM', 'RTX', 'UPS', 'FDX',
            'LMT', 'NOC', 'GD', 'TDG', 'ETN', 'EMR', 'ITW', 'PH',
            
            # 能源股
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'OXY', 'KMI', 'WMB',
            'PSX', 'VLO', 'MPC', 'HES', 'DVN', 'PXD', 'MRO', 'APA',
            
            # 公用事業股
            'NEE', 'DUK', 'SO', 'D', 'EXC', 'AEP', 'XEL', 'SRE',
            'ES', 'PEG', 'WEC', 'AWK', 'ED', 'ETR', 'FE', 'AEE',
            
            # 房地產股
            'AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'EXR', 'AVB', 'EQR',
            'MAA', 'UDR', 'CPT', 'ESS', 'BXP', 'SLG', 'KIM', 'REG',
            
            # 材料股
            'LIN', 'APD', 'SHW', 'DD', 'DOW', 'ECL', 'PPG', 'NEM',
            'FCX', 'SCCO', 'NUE', 'X', 'CLF', 'STLD', 'CMC', 'RS',
            
            # 通信股
            'VZ', 'T', 'TMUS', 'CHTR', 'CMCSA', 'DIS', 'NFLX', 'ROKU',
            'SPOT', 'P', 'SIRI', 'LBRDK', 'LBRDA', 'FWONK', 'FWONA', 'LSXMK',
            
            # 中概股
            'BABA', 'JD', 'PDD', 'BIDU', 'NTES', 'WB', 'BILI', 'TME',
            'VIPS', 'YMM', 'TAL', 'EDU', 'GOTU', 'COE', 'IQ', 'WB',
            
            # 新興成長股
            'ROKU', 'ZM', 'DOCU', 'SNOW', 'PLTR', 'CRWD', 'ZS', 'OKTA',
            'NET', 'DDOG', 'MDB', 'TWLO', 'WDAY', 'NOW', 'TEAM', 'SPLK',
            'ESTC', 'DBX', 'BOX', 'WORK', 'SLACK', 'PINS', 'SNAP', 'TWTR',
            
            # 生物科技股
            'GILD', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'ILMN', 'ISRG', 'DXCM',
            'ZTS', 'EW', 'BSX', 'MDT', 'SYK', 'ABBV', 'LLY', 'JNJ',
            
            # 半導體股
            'NVDA', 'AMD', 'INTC', 'QCOM', 'TXN', 'AVGO', 'MU', 'AMAT',
            'LRCX', 'KLAC', 'MCHP', 'ADI', 'MRVL', 'SWKS', 'QRVO', 'SLAB',
            
            # 電動車股
            'TSLA', 'NIO', 'XPEV', 'LI', 'RIVN', 'LCID', 'F', 'GM',
            'FORD', 'RIDE', 'WKHS', 'GOEV', 'HYLN', 'NKLA', 'RIDE', 'ARVL',
            
            # 太空股
            'SPCE', 'MAXR', 'IRDM', 'VSAT', 'GILT', 'KTOS', 'AJRD', 'LMT',
            'NOC', 'RTX', 'BA', 'HWM', 'TDG', 'LHX', 'LDOS', 'TXT',
            
            # 加密貨幣相關
            'COIN', 'MSTR', 'SQ', 'PYPL', 'V', 'MA', 'JPM', 'BAC',
            'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK', 'ICE', 'CME'
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
            
            # 如果任一VCP檢測成功，就加入推薦
            if basic_vcp_detected or enhanced_vcp_detected:
                # 動態計算信心度
                if enhanced_vcp_detected:
                    confidence_score = enhanced_vcp_details.get('score', 60)
                    status = enhanced_vcp_status
                    if basic_vcp_detected:
                        status = f"{basic_vcp_status} + {enhanced_vcp_status}"
                        confidence_score = max(confidence_score, 75)
                else:
                    confidence_score = 70  # 基本VCP信心度
                    status = basic_vcp_status
                
                patterns_found.append({
                    "type": "VCP",
                    "confidence": confidence_score,
                    "status": status,
                    "details": enhanced_vcp_details if enhanced_vcp_detected else {}
                })
            
            # 檢測 Cup & Handle 形態
            cup_handle_detected, cup_handle_status = self.analyzer.detect_cup_handle_pattern(stock_data)
            if cup_handle_detected:
                # 根據形態狀態計算信心度
                if "突破在即" in cup_handle_status:
                    cup_confidence = 85
                elif "形成" in cup_handle_status:
                    cup_confidence = 75
                else:
                    cup_confidence = 65
                    
                patterns_found.append({
                    "type": "Cup_Handle",
                    "confidence": cup_confidence,
                    "status": cup_handle_status,
                    "details": {}
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
                    # 儲存到資料庫
                    self.save_pattern_stock(scan_result)
                    results["pattern_stocks"].append(scan_result)
                    results["patterns_found"] += len(scan_result["patterns"])
                
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
        
        logger.info(f"掃描完成: 找到 {results['patterns_found']} 個形態")
        return results
    
    def save_pattern_stock(self, scan_result: Dict):
        """儲存形態股到資料庫"""
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
        """獲取推薦股票，合併同一股票的多個形態"""
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
        
        # 按信心度排序並限制數量
        results.sort(key=lambda x: x["confidence_score"], reverse=True)
        
        conn.close()
        return results[:limit]
    
    def get_dynamic_stock_list(self, max_stocks: int = 50) -> List[str]:
        """動態選擇股票列表"""
        import random
        
        # 確保熱門股票優先 (前20支)
        priority_stocks = self.popular_stocks[:20]
        
        # 從剩餘股票中隨機選擇
        remaining_stocks = self.popular_stocks[20:]
        random_stocks = random.sample(remaining_stocks, min(max_stocks - 20, len(remaining_stocks)))
        
        # 合併並打亂順序
        selected_stocks = priority_stocks + random_stocks
        random.shuffle(selected_stocks)
        
        logger.info(f"動態選擇了 {len(selected_stocks)} 支股票進行掃描")
        return selected_stocks[:max_stocks]
    
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
