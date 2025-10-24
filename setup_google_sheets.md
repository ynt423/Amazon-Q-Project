# Google Sheets 整合設置指南

## 🔧 設置步驟

### 1. 創建 Google Cloud Project
1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 創建新項目或選擇現有項目
3. 啟用 Google Sheets API 和 Google Drive API

### 2. 創建服務帳戶
1. 在 Google Cloud Console 中，前往 "IAM & Admin" > "Service Accounts"
2. 點擊 "Create Service Account"
3. 填寫服務帳戶詳細信息
4. 授予 "Editor" 角色
5. 創建並下載 JSON 密鑰文件

### 3. 配置憑證文件
1. 將下載的 JSON 文件重命名為 `service_account.json`
2. 將文件放置在項目根目錄
3. 確保文件包含在 `.gitignore` 中以保護隱私

### 4. 共享 Google Sheets
1. 打開目標 Google Sheets: https://docs.google.com/spreadsheets/d/1UsoATZK0FS7909hRdf8g8oPQ4_sHCRFLoX3GnkRzEJU/edit
2. 點擊右上角的 "Share" 按鈕
3. 添加服務帳戶的電子郵件地址（從 service_account.json 中的 client_email）
4. 授予 "Editor" 權限

### 5. 安裝依賴
```bash
pip install gspread google-auth google-auth-oauthlib google-auth-httplib2
```

## 📊 工作表結構

### Scanner Results 工作表
包含以下欄位：
- 更新時間
- 股票代號
- 當前價格
- 形態類型 (VCP, Cup & Handle, KC)
- 信心度
- 突破位
- 支撐位
- 建議止損
- 風險等級
- 波動率
- RS評級
- RSI
- MACD
- KC策略
- KC評分
- 形態狀態
- 最大損失%
- 交易量確認
- 市場趨勢
- 備註

### Scan Summary 工作表
包含掃描摘要信息：
- 掃描時間
- 總掃描股票數
- 發現形態數
- 掃描耗時
- 形態分布統計

## 🔒 安全注意事項

1. **保護憑證文件**
   - 絕不將 `service_account.json` 提交到版本控制
   - 使用環境變量存儲敏感信息
   - 定期輪換服務帳戶密鑰

2. **權限管理**
   - 僅授予必要的最小權限
   - 定期審查服務帳戶權限
   - 監控 API 使用情況

## 🚀 使用方法

掃描完成後，系統會自動：
1. 更新 "Scanner Results" 工作表
2. 創建或更新 "Scan Summary" 工作表
3. 應用格式化和顏色編碼
4. 記錄操作日誌

## 🛠️ 故障排除

### 常見問題：

1. **憑證錯誤**
   - 檢查 `service_account.json` 文件路徑
   - 確認服務帳戶有正確權限

2. **工作表訪問錯誤**
   - 確認已共享工作表給服務帳戶
   - 檢查工作表 ID 是否正確

3. **API 配額限制**
   - 檢查 Google Cloud Console 中的 API 使用情況
   - 考慮增加請求間隔

## 📈 功能特色

- **自動格式化**: 標題行、交替行顏色、數字格式
- **實時更新**: 每次掃描後自動更新
- **詳細數據**: 包含所有重要的技術分析指標
- **摘要統計**: 提供掃描結果概覽
- **錯誤處理**: 完善的異常處理和日誌記錄