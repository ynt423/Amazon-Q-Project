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
        
        # 熱門股票列表
        self.popular_stocks = [
            # S&P 500 主要股票
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
            'AMD', 'INTC', 'CRM', 'ADBE', 'PYPL', 'UBER', 'SPOT', 'SQ',
            'NFLX', 'DIS', 'BABA', 'JD', 'PDD', 'BIDU', 'NTES', 'WB',
            # 科技股
            'ORCL', 'CSCO', 'IBM', 'QCOM', 'TXN', 'AVGO', 'MU', 'AMAT',
            # 金融股
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'V', 'MA',
            # 醫療股
            'JNJ', 'PFE', 'UNH', 'ABBV', 'MRK', 'TMO', 'ABT', 'LLY',
            # 消費股
            'KO', 'PEP', 'WMT', 'PG', 'JNJ', 'HD', 'MCD', 'SBUX'
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
            
            # 檢測 VCP 形態
            vcp_detected, vcp_status, vcp_details = self.analyzer.detect_enhanced_vcp(stock_data)
            if vcp_detected:
                patterns_found.append({
                    "type": "VCP",
                    "confidence": vcp_details.get('score', 0),
                    "status": vcp_status,
                    "details": vcp_details
                })
            
            # 檢測 Cup & Handle 形態
            cup_handle_detected, cup_handle_status = self.analyzer.detect_cup_handle_pattern(stock_data)
            if cup_handle_detected:
                patterns_found.append({
                    "type": "Cup_Handle",
                    "confidence": 85,  # 預設信心度
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
    
    def batch_scan_stocks(self, stock_list: List[str] = None) -> Dict:
        """批次掃描股票"""
        if stock_list is None:
            stock_list = self.popular_stocks
        
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
        """獲取推薦股票"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ticker, pattern_type, confidence_score, price_at_detection,
                   stop_loss_price, risk_score, detection_date
            FROM pattern_stocks 
            WHERE is_active = 1 
            ORDER BY confidence_score DESC, detection_date DESC
            LIMIT ?
        ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "ticker": row[0],
                "pattern_type": row[1],
                "confidence_score": row[2],
                "current_price": row[3],
                "stop_loss_price": row[4],
                "risk_score": row[5],
                "detection_date": row[6]
            })
        
        conn.close()
        return results
    
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
