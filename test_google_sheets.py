#!/usr/bin/env python3
# test_google_sheets.py - Google Sheets 整合測試腳本

import os
import sys
from datetime import datetime

def test_google_sheets_integration():
    """測試 Google Sheets 整合功能"""
    print("🧪 Google Sheets 整合測試")
    print("=" * 50)
    
    # 1. 檢查憑證文件
    print("1. 檢查憑證文件...")
    credentials_path = "service_account.json"
    if os.path.exists(credentials_path):
        print(f"   ✅ 憑證文件存在: {credentials_path}")
        
        # 檢查文件大小
        file_size = os.path.getsize(credentials_path)
        if file_size > 100:  # 正常的憑證文件應該大於100字節
            print(f"   ✅ 憑證文件大小正常: {file_size} 字節")
        else:
            print(f"   ⚠️ 憑證文件可能不完整: {file_size} 字節")
    else:
        print(f"   ❌ 憑證文件不存在: {credentials_path}")
        print("   💡 請按照 GOOGLE_SHEETS_SETUP.md 指南設置憑證")
        return False
    
    # 2. 檢查依賴包
    print("\n2. 檢查依賴包...")
    try:
        import gspread
        print(f"   ✅ gspread 已安裝: {gspread.__version__}")
    except ImportError:
        print("   ❌ gspread 未安裝")
        print("   💡 執行: pip install gspread")
        return False
    
    try:
        from google.oauth2.service_account import Credentials
        print("   ✅ google-auth 已安裝")
    except ImportError:
        print("   ❌ google-auth 未安裝")
        print("   💡 執行: pip install google-auth")
        return False
    
    # 3. 測試 Google Sheets 客戶端
    print("\n3. 測試 Google Sheets 客戶端...")
    try:
        from google_sheets_integration import GoogleSheetsUpdater
        updater = GoogleSheetsUpdater()
        
        if updater.is_enabled:
            print("   ✅ Google Sheets 客戶端初始化成功")
            print(f"   📊 目標工作表 ID: {updater.spreadsheet_id}")
            print(f"   📋 工作表名稱: {updater.worksheet_name}")
        else:
            print("   ❌ Google Sheets 客戶端初始化失敗")
            print("   💡 請檢查憑證文件和 API 權限")
            return False
            
    except Exception as e:
        print(f"   ❌ Google Sheets 客戶端測試失敗: {e}")
        return False
    
    # 4. 測試模擬數據更新
    print("\n4. 測試模擬數據更新...")
    try:
        # 創建模擬掃描結果
        mock_results = {
            "scan_date": datetime.now().isoformat(),
            "total_scanned": 5,
            "patterns_found": 2,
            "scan_duration": 10.5,
            "pattern_stocks": [
                {
                    "ticker": "TEST1",
                    "current_price": 150.25,
                    "patterns": [
                        {
                            "type": "VCP",
                            "confidence": 85.5,
                            "status": "測試VCP形態",
                            "details": {
                                "kc_strategy": "strong_bullish",
                                "kc_score": 78
                            }
                        }
                    ],
                    "risk_assessment": {
                        "stop_loss_price": 140.50,
                        "support_level": 145.00,
                        "risk_score": 2,
                        "volatility": 0.25,
                        "max_loss_percentage": 6.5
                    }
                },
                {
                    "ticker": "TEST2", 
                    "current_price": 85.75,
                    "patterns": [
                        {
                            "type": "Cup_Handle",
                            "confidence": 72.0,
                            "status": "測試Cup & Handle形態",
                            "details": {
                                "kc_strategy": "consolidation_bullish",
                                "kc_score": 65
                            }
                        }
                    ],
                    "risk_assessment": {
                        "stop_loss_price": 80.00,
                        "support_level": 82.50,
                        "risk_score": 1,
                        "volatility": 0.18,
                        "max_loss_percentage": 6.7
                    }
                }
            ]
        }
        
        # 嘗試更新 Google Sheets
        success = updater.update_scanner_results(mock_results)
        
        if success:
            print("   ✅ 模擬數據更新成功")
            print("   🔗 查看結果: https://docs.google.com/spreadsheets/d/1UsoATZK0FS7909hRdf8g8oPQ4_sHCRFLoX3GnkRzEJU/edit")
            
            # 嘗試創建摘要工作表
            summary_success = updater.add_summary_sheet(mock_results)
            if summary_success:
                print("   ✅ 摘要工作表創建成功")
            else:
                print("   ⚠️ 摘要工作表創建失敗（可能已存在）")
                
        else:
            print("   ❌ 模擬數據更新失敗")
            print("   💡 請檢查 Google Sheets 共享權限")
            return False
            
    except Exception as e:
        print(f"   ❌ 模擬數據更新測試失敗: {e}")
        return False
    
    # 5. 測試完成
    print("\n" + "=" * 50)
    print("🎉 Google Sheets 整合測試完成！")
    print("✅ 所有測試通過，系統已準備就緒")
    print("\n📋 下一步:")
    print("   1. 執行 python app.py 啟動應用")
    print("   2. 點擊前端的 '查看選股清單' 按鈕")
    print("   3. 查看自動更新的股票分析數據")
    
    return True

def main():
    """主函數"""
    try:
        success = test_google_sheets_integration()
        if success:
            sys.exit(0)
        else:
            print("\n❌ 測試失敗，請按照提示修復問題")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試過程中發生未預期錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()