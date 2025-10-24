# 🎯 Google Sheets 選股清單整合 - 快速設置指南

## ✅ 當前狀態
- ✅ Google Sheets 整合模組已完成
- ✅ 自動更新功能已實現
- ✅ 前端連結按鈕已添加
- ⚠️ 需要設置 Google API 憑證

## 🚀 快速設置步驟

### 1. 創建 Google Cloud 項目
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 創建新項目或選擇現有項目
3. 啟用以下 API：
   - Google Sheets API
   - Google Drive API

### 2. 創建服務帳戶
1. 在 Google Cloud Console 中，前往 "IAM & Admin" > "Service Accounts"
2. 點擊 "Create Service Account"
3. 填寫服務帳戶名稱（例如：stockvision-sheets）
4. 授予 "Editor" 角色
5. 創建並下載 JSON 密鑰文件

### 3. 配置憑證文件
```bash
# 將下載的 JSON 文件重命名並移動到項目根目錄
mv ~/Downloads/your-service-account-key.json ./service_account.json
```

### 4. 共享 Google Sheets
1. 打開目標 Google Sheets：
   https://docs.google.com/spreadsheets/d/1UsoATZK0FS7909hRdf8g8oPQ4_sHCRFLoX3GnkRzEJU/edit
2. 點擊右上角的 "Share" 按鈕
3. 添加服務帳戶的電子郵件地址（從 service_account.json 中的 client_email）
4. 授予 "Editor" 權限

### 5. 測試整合
```bash
# 重新啟動應用
python app.py

# 檢查日誌中的 Google Sheets 狀態
# 應該看到：✅ Google Sheets客戶端設置成功
```

## 📊 功能特色

### 自動更新的數據欄位
- **更新時間**: 掃描執行時間
- **股票代號**: 股票符號
- **當前價格**: 實時股價
- **形態類型**: VCP, Cup & Handle, KC
- **信心度**: 0-95% 信心評分
- **突破位**: 預期突破價格
- **支撐位**: 關鍵支撐位
- **建議止損**: 風險控制點
- **風險等級**: 低/中/高風險
- **波動率**: 年化波動率
- **RS評級**: 相對強度評級
- **RSI**: 相對強弱指標
- **MACD**: 趨勢指標
- **KC策略**: 肯特納通道策略
- **KC評分**: KC指標評分
- **形態狀態**: 形態詳細描述
- **最大損失%**: 風險百分比
- **交易量確認**: 成交量驗證
- **市場趨勢**: 大盤趨勢狀態
- **備註**: 額外信息

### 雙工作表結構
1. **Scanner Results**: 詳細的掃描數據
2. **Scan Summary**: 掃描摘要統計

### 自動格式化
- 標題行藍色背景
- 交替行顏色
- 貨幣格式化
- 百分比格式化
- 自動調整列寬

## 🔧 故障排除

### 常見問題

#### 1. 憑證文件不存在
```
⚠️ Google Sheets憑證文件不存在: service_account.json
```
**解決方案**: 按照步驟 2-3 創建並配置憑證文件

#### 2. 權限錯誤
```
❌ Google Sheets客戶端設置失敗: 403 Forbidden
```
**解決方案**: 確認已將服務帳戶電子郵件添加到 Google Sheets 共享列表

#### 3. API 未啟用
```
❌ Google Sheets客戶端設置失敗: API not enabled
```
**解決方案**: 在 Google Cloud Console 中啟用 Google Sheets API 和 Google Drive API

### 檢查設置狀態
```python
# 在 Python 中測試
from google_sheets_integration import GoogleSheetsUpdater
updater = GoogleSheetsUpdater()
print(f"Google Sheets 整合狀態: {'✅ 已啟用' if updater.is_enabled else '❌ 未啟用'}")
```

## 📈 使用方法

### 自動更新
- 每次執行 `python app.py` 時自動掃描並更新 Google Sheets
- 手動觸發掃描也會自動更新

### 手動觸發
```python
from stock_scanner import StockScanner
scanner = StockScanner()
results = scanner.batch_scan_stocks(max_stocks=20)
# Google Sheets 會自動更新
```

### 查看結果
1. 點擊前端的 "查看選股清單" 按鈕
2. 或直接訪問：https://docs.google.com/spreadsheets/d/1UsoATZK0FS7909hRdf8g8oPQ4_sHCRFLoX3GnkRzEJU/edit

## 🔒 安全注意事項

1. **保護憑證文件**
   - `service_account.json` 已添加到 `.gitignore`
   - 絕不將憑證文件提交到版本控制

2. **權限管理**
   - 僅授予必要的最小權限
   - 定期審查服務帳戶權限

3. **API 配額**
   - Google Sheets API 有使用限制
   - 系統已實現適當的錯誤處理

## 🎉 完成！

設置完成後，您將看到：
- ✅ 自動更新的選股清單
- 📊 詳細的技術分析數據
- 📈 實時的形態識別結果
- 🛡️ 完整的風險管理信息

如有問題，請檢查日誌文件或重新執行設置步驟。