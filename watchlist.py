import sqlite3
import time
from datetime import datetime

class Watchlist:
    def __init__(self, db_path='watchlist.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化數據庫"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                added_time REAL NOT NULL,
                notes TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_stock(self, ticker, notes=''):
        """添加股票到收藏"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO watchlist (ticker, added_time, notes) VALUES (?, ?, ?)',
                (ticker.upper(), time.time(), notes)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # 已存在
        finally:
            conn.close()
    
    def remove_stock(self, ticker):
        """移除股票"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM watchlist WHERE ticker = ?', (ticker.upper(),))
        removed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return removed
    
    def get_watchlist(self):
        """獲取收藏列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ticker, added_time, notes FROM watchlist ORDER BY added_time DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'ticker': row[0],
            'added_time': datetime.fromtimestamp(row[1]).strftime('%Y-%m-%d %H:%M'),
            'notes': row[2]
        } for row in rows]