#!/usr/bin/env python3
# system_status.py - 系統狀態檢查腳本

import os
import sys
from datetime import datetime

def check_system_status():
    """檢查系統整體狀態"""
    print("🔍 StockVision Pro 系統狀態檢查")
    print("=" * 60)
    
    status = {
        "core_files": True,
        "dependencies": True,
        "database": True,
        "google_sheets": False,
        "ai_integration": False
    }
    
    # 1. 檢查核心文件
    print("1. 核心文件檢查...")
    core_files = [
        "app.py", "analyzer.py", "stock_scanner.py", 
        "config.py", "requirements.txt", ".env"
    ]
    
    for file in core_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - 缺失")
            status["core_files"] = False
    
    # 2. 檢查依賴包
    print("\n2. 依賴包檢查...")
    dependencies = [
        ("flask", "Flask"),
        ("pandas", "pandas"),
        ("yfinance", "yfinance"),
        ("requests", "requests"),
        ("python-dotenv", "dotenv")
    ]
    
    for package, import_name in dependencies:
        try:
            __import__(import_name.lower() if import_name != "dotenv" else "dotenv")
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - 未安裝")
            status["dependencies"] = False
    
    # 3. 檢查數據庫
    print("\n3. 數據庫檢查...")
    if os.path.exists("stock_analysis.db"):
        print("   ✅ stock_analysis.db 存在")
        
        # 檢查數據庫內容
        try:
            import sqlite3
            conn = sqlite3.connect("stock_analysis.db")
            cursor = conn.cursor()
            
            # 檢查推薦股票數量
            cursor.execute("SELECT COUNT(*) FROM pattern_stocks WHERE is_active = 1")
            pattern_count = cursor.fetchone()[0]
            print(f"   📊 活躍形態股票: {pattern_count} 支")
            
            # 檢查最近掃描時間
            cursor.execute("SELECT MAX(scan_date) FROM scan_history")
            last_scan = cursor.fetchone()[0]
            if last_scan:
                print(f"   🕐 最近掃描時間: {last_scan}")
            else:
                print("   ⚠️ 尚未執行過掃描")
            
            conn.close()
            status["database"] = True
            
        except Exception as e:
            print(f"   ❌ 數據庫讀取錯誤: {e}")
            status["database"] = False
    else:
        print("   ⚠️ stock_analysis.db 不存在，首次運行時會自動創建")
    
    # 4. 檢查 Google Sheets 整合
    print("\n4. Google Sheets 整合檢查...")
    try:
        # 檢查依賴包
        import gspread
        from google.oauth2.service_account import Credentials
        print("   ✅ Google Sheets 依賴包已安裝")
        
        # 檢查憑證文件
        if os.path.exists("service_account.json"):
            print("   ✅ service_account.json 存在")
            
            # 測試客戶端初始化
            try:
                from google_sheets_integration import GoogleSheetsUpdater
                updater = GoogleSheetsUpdater()
                if updater.is_enabled:
                    print("   ✅ Google Sheets 客戶端初始化成功")
                    print(f"   🔗 目標工作表: https://docs.google.com/spreadsheets/d/{updater.spreadsheet_id}")
                    status["google_sheets"] = True
                else:
                    print("   ❌ Google Sheets 客戶端初始化失敗")
            except Exception as e:
                print(f"   ❌ Google Sheets 測試失敗: {e}")
        else:
            print("   ⚠️ service_account.json 不存在")
            print("   💡 執行 python test_google_sheets.py 進行設置")
            
    except ImportError:
        print("   ⚠️ Google Sheets 依賴包未安裝")
        print("   💡 執行: pip install gspread google-auth")
    
    # 5. 檢查 AI 整合
    print("\n5. AI 整合檢查...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if api_key and api_key != 'your_openrouter_api_key_here':
            print("   ✅ OpenRouter API 密鑰已設置")
            
            # 測試 AI 分析器
            try:
                from gemini_analyzer import GeminiEnhancedAnalyzer
                analyzer = GeminiEnhancedAnalyzer(api_key)
                print("   ✅ Gemini AI 分析器初始化成功")
                status["ai_integration"] = True
            except Exception as e:
                print(f"   ❌ AI 分析器初始化失敗: {e}")
        else:
            print("   ⚠️ OpenRouter API 密鑰未設置")
            print("   💡 在 .env 文件中設置 OPENROUTER_API_KEY")
            
    except Exception as e:
        print(f"   ❌ AI 整合檢查失敗: {e}")
    
    # 6. 系統狀態總結
    print("\n" + "=" * 60)
    print("📋 系統狀態總結")
    print("=" * 60)
    
    total_checks = len(status)
    passed_checks = sum(status.values())
    
    for component, is_ok in status.items():
        status_icon = "✅" if is_ok else "❌"
        component_name = {
            "core_files": "核心文件",
            "dependencies": "基礎依賴",
            "database": "數據庫",
            "google_sheets": "Google Sheets",
            "ai_integration": "AI 整合"
        }[component]
        
        print(f"{status_icon} {component_name}")
    
    print(f"\n📊 整體狀態: {passed_checks}/{total_checks} 項檢查通過")
    
    if passed_checks >= 3:  # 核心功能正常
        print("🎉 系統核心功能正常，可以啟動應用！")
        print("\n🚀 啟動命令:")
        print("   python app.py")
        
        if not status["google_sheets"]:
            print("\n💡 可選功能:")
            print("   - 執行 python test_google_sheets.py 設置 Google Sheets 整合")
        
        if not status["ai_integration"]:
            print("   - 在 .env 文件中設置 OPENROUTER_API_KEY 啟用 AI 功能")
            
        return True
    else:
        print("❌ 系統存在關鍵問題，請修復後再啟動")
        return False

def main():
    """主函數"""
    try:
        success = check_system_status()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 檢查被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 檢查過程中發生錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()