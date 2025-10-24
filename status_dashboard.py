#!/usr/bin/env python3
# status_dashboard.py - 系統狀態面板

import os
import sqlite3
from datetime import datetime, timedelta

def show_status_dashboard():
    """顯示系統狀態面板"""
    print("📊 StockVision Pro 狀態面板")
    print("=" * 60)
    print(f"🕐 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 系統組件狀態
    print("🔧 系統組件狀態:")
    
    # 核心文件
    core_status = "✅" if all(os.path.exists(f) for f in ["app.py", "analyzer.py", "stock_scanner.py"]) else "❌"
    print(f"   {core_status} 核心文件")
    
    # Google Sheets
    sheets_status = "✅" if os.path.exists("service_account.json") else "⚠️"
    print(f"   {sheets_status} Google Sheets 整合")
    
    # AI 功能
    from dotenv import load_dotenv
    load_dotenv()
    ai_status = "✅" if os.getenv('OPENROUTER_API_KEY') and os.getenv('OPENROUTER_API_KEY') != 'your_openrouter_api_key_here' else "⚠️"
    print(f"   {ai_status} AI 分析功能")
    
    # 2. 數據庫狀態
    print("\n📊 數據庫狀態:")
    if os.path.exists("stock_analysis.db"):
        try:
            conn = sqlite3.connect("stock_analysis.db")
            cursor = conn.cursor()
            
            # 活躍形態股票
            cursor.execute("SELECT COUNT(*) FROM pattern_stocks WHERE is_active = 1")
            active_patterns = cursor.fetchone()[0]
            print(f"   📈 活躍形態股票: {active_patterns} 支")
            
            # 最近掃描
            cursor.execute("SELECT MAX(scan_date), total_stocks_scanned, patterns_found FROM scan_history")
            last_scan_data = cursor.fetchone()
            if last_scan_data[0]:
                last_scan_time = datetime.fromisoformat(last_scan_data[0].replace('Z', '+00:00'))
                time_diff = datetime.now() - last_scan_time.replace(tzinfo=None)
                
                if time_diff < timedelta(hours=1):
                    time_ago = f"{int(time_diff.total_seconds() // 60)} 分鐘前"
                elif time_diff < timedelta(days=1):
                    time_ago = f"{int(time_diff.total_seconds() // 3600)} 小時前"
                else:
                    time_ago = f"{time_diff.days} 天前"
                
                print(f"   🕐 最近掃描: {time_ago}")
                print(f"   📊 掃描結果: {last_scan_data[1]} 支股票，{last_scan_data[2]} 個形態")
            else:
                print("   ⚠️ 尚未執行掃描")
            
            # 形態分布
            cursor.execute("""
                SELECT pattern_type, COUNT(*) 
                FROM pattern_stocks 
                WHERE is_active = 1 
                GROUP BY pattern_type
            """)
            patterns = cursor.fetchall()
            if patterns:
                print("   📋 形態分布:")
                for pattern_type, count in patterns:
                    pattern_name = {"VCP": "VCP形態", "Cup_Handle": "Cup & Handle", "KC": "KC形態"}.get(pattern_type, pattern_type)
                    print(f"      • {pattern_name}: {count} 支")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ 數據庫讀取錯誤: {e}")
    else:
        print("   ⚠️ 數據庫文件不存在")
    
    # 3. Google Sheets 狀態
    print("\n📊 Google Sheets 狀態:")
    if os.path.exists("service_account.json"):
        try:
            from google_sheets_integration import GoogleSheetsUpdater
            updater = GoogleSheetsUpdater()
            if updater.is_enabled:
                print("   ✅ 整合已啟用")
                print(f"   🔗 工作表連結: https://docs.google.com/spreadsheets/d/{updater.spreadsheet_id}")
            else:
                print("   ❌ 整合設置失敗")
        except Exception as e:
            print(f"   ❌ 整合測試失敗: {e}")
    else:
        print("   ⚠️ 憑證文件不存在")
        print("   💡 執行 python setup_credentials.py 進行設置")
    
    # 4. 快速操作
    print("\n🚀 快速操作:")
    print("   • 啟動應用: python app.py")
    print("   • 測試 Google Sheets: python test_google_sheets.py")
    print("   • 系統檢查: python system_status.py")
    print("   • 設置憑證: python setup_credentials.py")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    show_status_dashboard()