#!/usr/bin/env python3
# setup_credentials.py - 快速憑證設置助手

import os
import json

def create_service_account_template():
    """創建服務帳戶憑證模板"""
    template = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id", 
        "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
        "client_email": "your-service-account@your-project-id.iam.gserviceaccount.com",
        "client_id": "your-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com"
    }
    
    with open("service_account_template.json", "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print("✅ 已創建 service_account_template.json 模板文件")

def setup_google_sheets():
    """Google Sheets 設置指南"""
    print("🔧 Google Sheets 快速設置指南")
    print("=" * 50)
    
    # 檢查是否已有憑證
    if os.path.exists("service_account.json"):
        print("✅ service_account.json 已存在")
        return True
    
    print("📋 設置步驟:")
    print("1. 前往 Google Cloud Console: https://console.cloud.google.com/")
    print("2. 創建新項目或選擇現有項目")
    print("3. 啟用 Google Sheets API 和 Google Drive API")
    print("4. 創建服務帳戶:")
    print("   - 前往 IAM & Admin > Service Accounts")
    print("   - 點擊 Create Service Account")
    print("   - 填寫名稱: stockvision-sheets")
    print("   - 授予 Editor 角色")
    print("   - 創建並下載 JSON 密鑰")
    print("5. 將下載的 JSON 文件重命名為 service_account.json")
    print("6. 共享 Google Sheets 給服務帳戶:")
    print("   - 打開: https://docs.google.com/spreadsheets/d/1UsoATZK0FS7909hRdf8g8oPQ4_sHCRFLoX3GnkRzEJU/edit")
    print("   - 點擊 Share 按鈕")
    print("   - 添加服務帳戶的 client_email")
    print("   - 授予 Editor 權限")
    
    # 創建模板文件
    create_service_account_template()
    
    print("\n💡 提示:")
    print("- 可以參考 service_account_template.json 的格式")
    print("- 設置完成後執行: python test_google_sheets.py")
    
    return False

def main():
    """主函數"""
    print("🚀 StockVision Pro 憑證設置助手")
    print("=" * 50)
    
    # Google Sheets 設置
    sheets_ready = setup_google_sheets()
    
    print("\n" + "=" * 50)
    if sheets_ready:
        print("🎉 Google Sheets 憑證已配置！")
        print("執行測試: python test_google_sheets.py")
    else:
        print("📝 請按照上述步驟設置 Google Sheets 憑證")
    
    print("\n🚀 啟動應用: python app.py")

if __name__ == "__main__":
    main()