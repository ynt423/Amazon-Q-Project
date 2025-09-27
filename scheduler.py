# scheduler.py - 定時任務調度器

import schedule
import time
import logging
from datetime import datetime
from stock_scanner import StockScanner, run_daily_scan

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class StockScheduler:
    """股票掃描定時任務調度器"""
    
    def __init__(self):
        self.scanner = StockScanner()
        self.setup_schedule()
    
    def setup_schedule(self):
        """設置定時任務"""
        # 每日早上 9:00 掃描 (美股開盤前)
        schedule.every().day.at("09:00").do(self.daily_morning_scan)
        
        # 每日下午 16:30 掃描 (美股收盤後)
        schedule.every().day.at("16:30").do(self.daily_evening_scan)
        
        # 每週一早上 8:00 進行完整掃描
        schedule.every().monday.at("08:00").do(self.weekly_full_scan)
        
        # 每小時檢查一次是否有新的推薦股票
        schedule.every().hour.do(self.hourly_check)
        
        logger.info("定時任務設置完成")
        logger.info("- 每日 09:00: 早盤掃描")
        logger.info("- 每日 16:30: 收盤掃描")
        logger.info("- 每週一 08:00: 完整掃描")
        logger.info("- 每小時: 狀態檢查")
    
    def daily_morning_scan(self):
        """每日早盤掃描"""
        logger.info("開始每日早盤掃描...")
        try:
            # 掃描熱門股票
            results = self.scanner.batch_scan_stocks()
            logger.info(f"早盤掃描完成: 找到 {results['patterns_found']} 個形態")
        except Exception as e:
            logger.error(f"早盤掃描失敗: {e}")
    
    def daily_evening_scan(self):
        """每日收盤掃描"""
        logger.info("開始每日收盤掃描...")
        try:
            # 掃描熱門股票
            results = self.scanner.batch_scan_stocks()
            logger.info(f"收盤掃描完成: 找到 {results['patterns_found']} 個形態")
        except Exception as e:
            logger.error(f"收盤掃描失敗: {e}")
    
    def weekly_full_scan(self):
        """每週完整掃描"""
        logger.info("開始每週完整掃描...")
        try:
            # 清理舊記錄
            self.scanner.cleanup_old_patterns(days=7)
            
            # 完整掃描所有股票
            results = self.scanner.batch_scan_stocks()
            logger.info(f"週掃描完成: 掃描 {results['total_scanned']} 支股票，找到 {results['patterns_found']} 個形態")
        except Exception as e:
            logger.error(f"週掃描失敗: {e}")
    
    def hourly_check(self):
        """每小時檢查"""
        try:
            # 檢查推薦股票數量
            recommended = self.scanner.get_recommended_stocks(limit=1)
            logger.info(f"當前推薦股票數量: {len(recommended)}")
            
            # 如果推薦股票太少，觸發額外掃描
            if len(recommended) < 3:
                logger.info("推薦股票不足，觸發額外掃描...")
                self.scanner.batch_scan_stocks(self.scanner.popular_stocks[:20])
                
        except Exception as e:
            logger.error(f"每小時檢查失敗: {e}")
    
    def run_scheduler(self):
        """運行調度器"""
        logger.info("股票掃描調度器啟動...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分鐘檢查一次
            except KeyboardInterrupt:
                logger.info("調度器停止")
                break
            except Exception as e:
                logger.error(f"調度器錯誤: {e}")
                time.sleep(60)

def run_manual_scan():
    """手動執行掃描 (用於測試)"""
    logger.info("執行手動掃描...")
    scanner = StockScanner()
    
    # 測試掃描前10支股票
    test_stocks = scanner.popular_stocks[:10]
    results = scanner.batch_scan_stocks(test_stocks)
    
    logger.info(f"手動掃描完成: {results}")
    return results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        # 手動掃描模式
        run_manual_scan()
    else:
        # 定時任務模式
        scheduler = StockScheduler()
        scheduler.run_scheduler()
