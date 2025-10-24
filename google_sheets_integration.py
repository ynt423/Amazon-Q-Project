# google_sheets_integration.py - Google Sheets 整合模組

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)

class GoogleSheetsUpdater:
    """Google Sheets 更新器"""
    
    def __init__(self, credentials_path=None):
        self.credentials_path = credentials_path or "service_account.json"
        self.spreadsheet_id = "1UsoATZK0FS7909hRdf8g8oPQ4_sHCRFLoX3GnkRzEJU"
        self.worksheet_name = "Scanner Results"
        self.client = None
        self.is_enabled = False
        self.setup_client()
    
    def setup_client(self):
        """設置Google Sheets客戶端"""
        try:
            # 檢查憑證文件是否存在
            if not os.path.exists(self.credentials_path):
                logger.warning(f"Google Sheets憑證文件不存在: {self.credentials_path}")
                logger.info("請按照 setup_google_sheets.md 指南設置 Google Sheets 整合")
                self.client = None
                self.is_enabled = False
                return
            
            # 定義權限範圍
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # 創建憑證和客戶端
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            self.client = gspread.authorize(creds)
            self.is_enabled = True
            logger.info("✅ Google Sheets客戶端設置成功")
                
        except Exception as e:
            logger.error(f"❌ Google Sheets客戶端設置失敗: {e}")
            logger.info("提示: 請檢查 service_account.json 文件是否正確配置")
            self.client = None
            self.is_enabled = False
    
    def update_scanner_results(self, scan_results):
        """更新掃描結果到Google Sheets"""
        if not self.is_enabled or not self.client:
            logger.info("📊 Google Sheets整合未啟用，跳過更新")
            return False
        
        try:
            # 打開試算表
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # 嘗試獲取工作表，如果不存在則創建
            try:
                worksheet = spreadsheet.worksheet(self.worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=self.worksheet_name, rows=1000, cols=20)
            
            # 準備數據
            data = self.prepare_sheet_data(scan_results)
            
            # 清空現有數據
            worksheet.clear()
            
            # 設置標題行 - 更專業和易讀
            headers = [
                "📅 更新時間", "📈 股票代號", "💰 當前價格", "🎯 形態類型", "💪 信號強度(0-100)", 
                "🚀 突破位", "💵 建議買入點", "🛡️ 支撐位", "⛔ 建議止損", "⚠️ 風險等級", 
                "📊 年化波動率(%)", "🏆 RS評級", "📈 RSI", "📊 MACD信號", "🔄 KC策略", 
                "📊 KC評分", "📋 形態狀態", "💸 最大損失(%)", "📊 成交量狀態", "🌊 市場趨勢", "📝 交易建議"
            ]
            
            # 更新數據
            all_data = [headers] + data
            worksheet.update('A1', all_data)
            
            # 格式化工作表
            self.format_worksheet(worksheet, len(data))
            
            logger.info(f"✅ 成功更新 {len(data)} 筆掃描結果到Google Sheets")
            logger.info(f"🔗 查看結果: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新Google Sheets失敗: {e}")
            return False
    
    def prepare_sheet_data(self, scan_results):
        """準備工作表數據 - 使用完整網站分析結果"""
        data = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for stock_result in scan_results.get('pattern_stocks', []):
            ticker = stock_result['ticker']
            
            # 獲取完整網站分析結果
            try:
                from analyzer import GrowthSignalAnalyzer
                analyzer = GrowthSignalAnalyzer()
                full_analysis = analyzer.generate_signal(ticker, period="1y")
                
                if not full_analysis.get('success'):
                    continue
                
                # 使用網站分析的所有數據
                current_price = full_analysis.get('current_price', stock_result['current_price'])
                final_score = full_analysis.get('final_score', 0)  # 信號強度
                breakout_price = full_analysis.get('breakout_price', 'N/A')
                rs_rating = full_analysis.get('rs_rating', 'N/A')
                rsi = full_analysis.get('rsi', 'N/A')
                macd = full_analysis.get('macd', 'N/A')
                kc_strategy = full_analysis.get('kc_strategy', 'N/A')
                kc_score = full_analysis.get('kc_score', 'N/A')
                market_trend = full_analysis.get('market_trend', 'N/A')
                volume_ok = full_analysis.get('volume_ok', False)
                
                # 計算缺失的數值
                # 1. 支撐位 - 使用最近20日最低點
                stock_data = analyzer.get_stock_data(ticker, period="1y")
                if stock_data is not None and len(stock_data) >= 20:
                    support_level = stock_data['Low'].tail(20).min()
                    
                    # 2. 年化波動率
                    returns = stock_data['Close'].pct_change().dropna()
                    volatility = returns.std() * (252 ** 0.5) if len(returns) > 0 else 0
                    
                    # 3. 建議止損點 (支撐位下方3%)
                    recommended_stop_loss = support_level * 0.97
                else:
                    support_level = current_price * 0.95  # 備用計算
                    volatility = 0.25  # 預設波動率
                    recommended_stop_loss = support_level * 0.97
                
                # 計算風險管理指標 - 使用買入點作為基準
                if isinstance(recommended_stop_loss, (int, float)) and recommended_stop_loss > 0:
                    if isinstance(breakout_price, (int, float)):
                        buy_point_calc = breakout_price * 1.01
                        max_loss_pct = (buy_point_calc - recommended_stop_loss) / buy_point_calc * 100
                    else:
                        buy_point_calc = current_price * 1.02
                        max_loss_pct = (buy_point_calc - recommended_stop_loss) / buy_point_calc * 100
                else:
                    max_loss_pct = 5.0  # 預設風險百分比
                
                # 合併多個形態到同一行
                pattern_types = []
                pattern_statuses = []
                for pattern in stock_result['patterns']:
                    pattern_types.append(pattern['type'].replace('_', '&'))
                    pattern_statuses.append(pattern['status'])
                
                combined_patterns = ' + '.join(pattern_types)
                combined_status = ' | '.join(pattern_statuses)
                
                # 計算建議買入點
                if isinstance(breakout_price, (int, float)):
                    buy_point = breakout_price * 1.01
                    buy_point_str = f"${buy_point:.2f}"
                else:
                    buy_point = current_price * 1.02
                    buy_point_str = f"${buy_point:.2f} (估算)"
                
                # 風險等級
                if max_loss_pct <= 7:
                    risk_level = "低風險"
                elif max_loss_pct <= 10:
                    risk_level = "中風險"
                else:
                    risk_level = "高風險"
                
                row_data = [
                    current_time,
                    ticker,
                    f"${current_price:.2f}" if isinstance(current_price, (int, float)) else 'N/A',
                    combined_patterns,
                    f"{final_score:.0f}",  # 信號強度
                    f"${breakout_price:.2f}" if isinstance(breakout_price, (int, float)) else '待確認',
                    buy_point_str,
                    f"${support_level:.2f}" if isinstance(support_level, (int, float)) else f"${current_price*0.95:.2f}",  # 確保有支撐位數值
                    f"${recommended_stop_loss:.2f}" if isinstance(recommended_stop_loss, (int, float)) else f"${support_level*0.97:.2f}",  # 確保有止損數值
                    risk_level,
                    f"{volatility*100:.1f}" if isinstance(volatility, (int, float)) and volatility > 0 else '25.0',  # 確保有波動率數值
                    f"{rs_rating}/99" if rs_rating != 'N/A' else '待計算',
                    f"{rsi:.1f}" if isinstance(rsi, (int, float)) else str(rsi),
                    str(macd) if macd != 'N/A' else '中性',
                    kc_strategy.replace('_', ' ').title() if kc_strategy != 'N/A' else '無信號',
                    f"{kc_score:.0f}/100" if isinstance(kc_score, (int, float)) else '待評估',
                    combined_status,
                    f"{max_loss_pct:.1f}" if max_loss_pct > 0 else '5.0',  # 確保有最大損失數值
                    "✅ 充足" if volume_ok else "⚠️ 不足",
                    str(market_trend) if market_trend != 'N/A' else '中性',
                    f"💡 買入: {buy_point_str} | 止損: ${recommended_stop_loss:.2f} | 風險: {max_loss_pct:.1f}%" if isinstance(recommended_stop_loss, (int, float)) else f"💡 買入: {buy_point_str} | 止損: ${support_level*0.97:.2f} | 風險: {max_loss_pct:.1f}%"
                ]
                
                data.append(row_data)
                
            except Exception as e:
                logger.error(f"獲取 {ticker} 完整分析失敗: {e}")
                continue
        
        return data
    
    def format_worksheet(self, worksheet, data_rows):
        """格式化工作表"""
        try:
            # 設置標題行格式 - 更專業的藍色主題
            worksheet.format('A1:T1', {
                'backgroundColor': {'red': 0.1, 'green': 0.3, 'blue': 0.7},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'fontSize': 11},
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            })
            
            # 設置數據行格式
            if data_rows > 0:
                # 交替行顏色和條件格式
                for i in range(2, data_rows + 2, 2):
                    worksheet.format(f'A{i}:T{i}', {
                        'backgroundColor': {'red': 0.97, 'green': 0.98, 'blue': 1.0}
                    })
                
                # 高信心度股票突出顯示 (假設信心度在E列)
                worksheet.format(f'A2:T{data_rows + 1}', {
                    'textFormat': {'fontSize': 10}
                })
                
                # 價格列格式 (美元)
                worksheet.format(f'C2:C{data_rows + 1}', {'numberFormat': {'type': 'CURRENCY', 'pattern': '"$"#,##0.00'}})
                worksheet.format(f'F2:I{data_rows + 1}', {'numberFormat': {'type': 'CURRENCY', 'pattern': '"$"#,##0.00'}})  # 包含買入點
                
                # 百分比列格式
                worksheet.format(f'E2:E{data_rows + 1}', {'numberFormat': {'type': 'NUMBER', 'pattern': '0.0"%"'}})
                worksheet.format(f'K2:K{data_rows + 1}', {'numberFormat': {'type': 'NUMBER', 'pattern': '0.0"%"'}})
                worksheet.format(f'R2:R{data_rows + 1}', {'numberFormat': {'type': 'NUMBER', 'pattern': '0.0"%"'}})
                
                # 條件格式 - 信心度顏色編碼
                worksheet.format(f'E2:E{data_rows + 1}', {
                    'backgroundColor': {'red': 0.9, 'green': 1.0, 'blue': 0.9}  # 淺綠色背景
                })
                
                # 建議買入點突出顯示 (G列)
                worksheet.format(f'G2:G{data_rows + 1}', {
                    'backgroundColor': {'red': 1.0, 'green': 0.95, 'blue': 0.8},  # 淺橙色背景
                    'textFormat': {'bold': True}
                })
                
                # 風險等級顏色編碼 (J列)
                worksheet.format(f'J2:J{data_rows + 1}', {
                    'textFormat': {'bold': True}
                })
            
            # 手動設置列寬以獲得更好的顯示效果
            column_widths = {
                0: 150,   # 更新時間
                1: 80,    # 股票代號
                2: 100,   # 當前價格
                3: 120,   # 形態類型
                4: 80,    # 信心度
                5: 100,   # 突破位
                6: 120,   # 建議買入點 (新增)
                7: 100,   # 支撐位
                8: 100,   # 建議止損
                9: 140,   # 風險等級
                10: 100,  # 波動率
                11: 80,   # RS評級
                12: 60,   # RSI
                13: 100,  # MACD
                14: 120,  # KC策略
                15: 80,   # KC評分
                16: 200,  # 形態狀態
                17: 80,   # 最大損失%
                18: 100,  # 成交量狀態
                19: 100,  # 市場趨勢
                20: 280   # 交易建議 (更寬)
            }
            
            for col_index, width in column_widths.items():
                if col_index < 26:  # A-Z
                    col_letter = chr(65 + col_index)
                else:  # AA, AB, etc.
                    col_letter = chr(64 + col_index // 26) + chr(65 + col_index % 26)
                worksheet.update_dimension_properties(f'{col_letter}:{col_letter}', 
                                                    {'pixelSize': width})
            
        except Exception as e:
            logger.warning(f"格式化工作表失敗: {e}")
    
    def add_summary_sheet(self, scan_results):
        """添加摘要工作表"""
        if not self.client:
            return False
        
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            # 創建或更新摘要工作表
            summary_name = "Scan Summary"
            try:
                summary_sheet = spreadsheet.worksheet(summary_name)
            except gspread.WorksheetNotFound:
                summary_sheet = spreadsheet.add_worksheet(title=summary_name, rows=100, cols=10)
            
            # 準備摘要數據
            summary_data = [
                ["📊 StockVision Pro 掃描摘要", ""],
                ["🕐 掃描時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["📈 總掃描股票", scan_results.get('total_scanned', 0)],
                ["🎯 發現形態數", scan_results.get('patterns_found', 0)],
                ["⏱️ 掃描耗時", f"{scan_results.get('scan_duration', 0):.1f}秒"],
                ["📊 平均每股耗時", f"{scan_results.get('scan_duration', 0)/max(scan_results.get('total_scanned', 1), 1):.2f}秒"],
                ["", ""],
                ["🎯 形態分布統計", ""],
                ["🔥 VCP 形態", 0],
                ["🏆 Cup & Handle 形態", 0],
                ["📊 KC 形態", 0],
                ["", ""],
                ["🎯 Swing Trading 範選條件", ""],
                ["• 價格範圍", "$5 - $500"],
                ["• 信心度闾值", "≥70%"],
                ["• 最大損失上限", "≤10%"],
                ["• 波動率範圍", "15% - 60%"],
                ["• 形態品質要求", "VCP 75%+ | C&H 70%+ | KC 75%+"],
                ["", ""],
                ["💡 操作指引", ""],
                ["• 信心度 ≥80%", "🔥 強烈推薦"],
                ["• 信心度 70-79%", "👀 值得關注"],
                ["• 最大損失 ≤7%", "✅ 風險可控"]
            ]
            
            # 統計形態分布
            pattern_counts = {"VCP": 0, "Cup_Handle": 0, "KC": 0}
            for stock in scan_results.get('pattern_stocks', []):
                for pattern in stock['patterns']:
                    pattern_type = pattern['type']
                    if pattern_type in pattern_counts:
                        pattern_counts[pattern_type] += 1
            
            summary_data[7][1] = pattern_counts["VCP"]
            summary_data[8][1] = pattern_counts["Cup_Handle"]
            summary_data[9][1] = pattern_counts["KC"]
            
            # 更新摘要工作表
            summary_sheet.clear()
            summary_sheet.update('A1', summary_data)
            
            # 格式化摘要工作表
            summary_sheet.format('A1:B1', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 1.0},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
            return True
            
        except Exception as e:
            logger.error(f"創建摘要工作表失敗: {e}")
            return False

# 使用示例
def update_sheets_with_scan_results(scan_results):
    """更新Google Sheets的便捷函數"""
    updater = GoogleSheetsUpdater()
    success = updater.update_scanner_results(scan_results)
    if success:
        updater.add_summary_sheet(scan_results)
    return success