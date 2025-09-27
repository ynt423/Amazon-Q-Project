# 🚀 VCP & RS Fusion: AI-Enhanced Stock Analysis System

🎯 **基於 William O'Neil 和 Mark Minervini 成長股分析哲學的智能股票分析系統**

## 📋 系統概述

這是一個集成了 AI 推理能力的專業股票分析系統，結合了傳統技術分析和現代 AI 技術，提供全面的股票分析、形態識別、風險管理和投資建議。

## ✨ 核心功能

### 🧠 AI 增強分析
- **Gemini 2.5 Flash 推理**: 使用 Google 最新的 AI 模型進行深度分析
- **智能投資建議**: 基於技術指標和市場情緒的 AI 建議
- **新聞情緒分析**: 實時新聞數據和情緒分析
- **風險評估**: AI 驅動的風險管理和止損建議

### 📊 技術分析引擎
- **RS Rating 計算**: 相對於 S&P 500 的 6 個月價格表現評級 (1-99)
- **VCP 形態識別**: 檢測 Volatility Contraction Pattern (波動收縮形態)
- **Cup & Handle 識別**: 檢測杯柄突破形態
- **多時間軸分析**: 日線/週線/月線分析

### 🎯 智能信號評分系統
- **綜合評分**: 結合 RS Rating、RSI 和形態識別的 0-100 分評分
- **操作建議**: Strong Buy (≥80) / Hold (60-79) / Avoid (<60)
- **形態獎勵**: VCP (+10分) / Cup & Handle (+8分)

### 📈 可視化平台
- **互動式圖表**: Plotly.js 專業 K 線圖
- **技術指標**: MA20, MA50, 布林帶, RSI, MACD
- **形態報告**: 清晰展示識別結果
- **響應式設計**: Bootstrap 5 現代化界面

## 🛠️ 技術架構

### 後端技術
- **Flask**: Web 框架
- **yfinance**: 股票數據獲取
- **pandas & numpy**: 數據處理和數值計算
- **SQLite**: 數據庫存儲
- **OpenRouter API**: Gemini 2.5 Flash 推理
- **schedule**: 定時任務調度

### 前端技術
- **Bootstrap 5**: UI 框架
- **Plotly.js**: 互動式圖表
- **JavaScript**: 前端邏輯
- **Font Awesome**: 圖標庫

### AI 集成
- **Gemini 2.5 Flash**: 推理和分析
- **新聞 API**: 實時市場新聞
- **情緒分析**: 市場情緒評估
- **風險管理**: AI 驅動的止損建議

## 🚀 快速開始

### 1. 環境設置

```bash
# 克隆項目
git clone <repository-url>
cd Amazon-Q-Project

# 創建虛擬環境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt
```

### 2. API 配置

創建 `.env` 文件並添加您的 API 密鑰：

```env
# OpenRouter API (用於 Gemini 2.5 Flash)
OPENROUTER_API_KEY=your_openrouter_api_key_here
AI_MODEL=google/gemini-2.5-flash-preview-09-2025
AI_ENHANCED=True

# 新聞 API (可選)
NEWS_API_KEY=your_newsapi_key_here
ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here
FINNHUB_KEY=your_finnhub_key_here

# 系統配置
FLASK_DEBUG=True
FLASK_PORT=5001
```

### 3. 啟動應用

```bash
# 啟動主應用
python app.py

# 訪問應用
# 打開瀏覽器訪問: http://localhost:5001
```

### 4. 啟動定時任務 (可選)

```bash
# 在另一個終端中啟動定時掃描任務
python scheduler.py

# 這將自動執行：
# - 每日 09:00: 早盤掃描
# - 每日 16:30: 收盤掃描  
# - 每週一 08:00: 完整掃描
# - 每小時: 狀態檢查
```

## 📊 使用方法

### 基本分析流程
1. **輸入股票代號**: 如 AAPL, TSLA, NVDA
2. **選擇分析模式**:
   - 📈 **生成信號**: 基本技術分析
   - 🧠 **AI分析**: AI 增強分析 + 新聞洞察
3. **查看結果**: 技術指標、形態識別、AI 建議
4. **風險管理**: 點擊「止損建議」獲取風險評估

### 高級功能
- **推薦股票**: 查看今日形態股推薦
- **多時間軸**: 日線/週線/月線分析
- **新聞分析**: 實時新聞和情緒分析
- **AI 洞察**: 基於 AI 的投資建議

## 🔧 API 端點

### 主要端點
- `POST /signal/generate` - 生成技術分析信號
- `POST /api/ai-analysis` - AI 增強分析
- `GET /api/recommended-stocks` - 獲取推薦股票
- `GET /api/stop-loss/<ticker>` - 獲取止損建議
- `GET /api/news/<ticker>` - 獲取新聞分析

### 使用示例
```bash
# 技術分析
curl -X POST http://localhost:5001/signal/generate \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "period": "1y"}'

# AI 分析
curl -X POST http://localhost:5001/api/ai-analysis \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "period": "1y"}'
```

## 📈 評分算法

### 基礎分數計算
```
基礎分數 = Σ(各項指標分數 × 權重)
```

### 權重分配
- RS Rating: 20%
- RSI Score: 15%  
- MACD Score: 15%
- BB Score: 10%
- Volume OK: 10%
- Pattern Bonus: 10%
- Trend Filter: 20%

### 形態獎勵
- VCP 形態檢測成功: +10 分
- Cup & Handle 形態檢測成功: +8 分

### 最終評分
```
最終分數 = min(100, 基礎分數 + 形態獎勵)
```

## 🎯 核心算法

### RS Rating 計算
- 計算股票與 S&P 500 在過去 6 個月的相對表現
- 轉換為 1-99 的評級分數
- 分數越高表示相對表現越強

### VCP 形態識別
- 檢查近 3 個月內價格波動的收縮趨勢
- 識別波動率是否呈現遞減模式
- 判斷是否處於潛在突破階段

### Cup & Handle 識別
- 分析近 6 個月的價格走勢
- 檢測 U 形底部形成
- 確認右側整理區域 (Handle)

## 🔑 API 密鑰設置

### OpenRouter API (必需)
1. 訪問 https://openrouter.ai/
2. 註冊帳戶並獲取 API key
3. 在 `.env` 文件中設置 `OPENROUTER_API_KEY`

### 新聞 API (可選)
- **NewsAPI**: https://newsapi.org/ (1000 請求/天)
- **Alpha Vantage**: https://www.alphavantage.co/ (5 請求/分鐘)
- **Finnhub**: https://finnhub.io/ (60 請求/分鐘)

## 🛠️ 故障排除

### 常見問題

#### 1. 端口被佔用
```bash
# 檢查端口使用情況
lsof -i :5001

# 停止佔用端口的程序
pkill -f "python app.py"
```

#### 2. API 密鑰問題
```bash
# 檢查環境變數
echo $OPENROUTER_API_KEY

# 測試 API 連接
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('API Key:', os.getenv('OPENROUTER_API_KEY', 'Not found'))
"
```

#### 3. 依賴缺失
```bash
# 重新安裝依賴
pip install -r requirements.txt
```

#### 4. 數據庫錯誤
```bash
# 刪除舊數據庫重新創建
rm stock_analysis.db
python -c "from stock_scanner import StockScanner; StockScanner()"
```

## 📊 系統特色

### 專業級分析
- 基於 William O'Neil 和 Mark Minervini 理論
- 專業技術指標計算
- 形態識別算法
- AI 驅動的風險管理

### 用戶體驗
- 直觀的界面設計
- 一鍵快速分析
- 實時數據更新
- 響應式設計

### 性能優化
- 數據緩存機制
- 異步處理
- 定時任務調度
- 數據庫優化

## 🎨 界面功能

### 主要界面
- **推薦股票區域**: 顯示今日形態股
- **分析輸入**: 股票代號輸入和時間軸選擇
- **結果展示**: 技術指標、形態識別、AI 分析
- **互動圖表**: 專業 K 線圖和技術指標
- **風險管理**: 止損建議和風險評估

### AI 分析結果
- **AI 評分**: 基於 AI 的綜合評分
- **置信度**: AI 分析的置信度
- **投資建議**: AI 生成的投資建議
- **新聞洞察**: 最新新聞和情緒分析
- **時機建議**: AI 的進場時機建議

## 📞 技術支援

### 系統狀態檢查
```bash
# 檢查所有服務狀態
ps aux | grep python

# 檢查端口狀態
netstat -an | grep :5001
```

### 重啟服務
```bash
# 完全重啟
pkill -f python
source venv/bin/activate
python app.py
```

## 🚀 性能優化

### 緩存策略
- 股票數據緩存 5 分鐘
- 分析結果緩存
- 新聞數據緩存
- 減少 API 請求

### 數據庫優化
- 定期清理舊記錄
- 索引優化查詢
- 備份重要數據

## 📈 適用場景

- 成長股篩選和分析
- 技術形態識別
- 投資決策輔助
- 股票教育和學習
- 量化交易策略開發
- AI 驅動的投資研究

## ⚠️ 免責聲明

本工具僅供教育和研究用途，不構成投資建議。投資有風險，請謹慎決策。

---

**🎉 祝您使用愉快！**

如有問題，請檢查日誌文件或重新啟動服務。