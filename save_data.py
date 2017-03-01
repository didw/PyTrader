import sys
from PyQt5.QtWidgets import QApplication
from pykiwoom.kiwoom import *
from pykiwoom.wrapper import *
import numpy as np
import pandas as pd
import sqlite3
import datetime

MARKET_KOSPI   = 0
MARKET_KOSDAK  = 10

class DailyData:
    def __init__(self):
        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()
        self.wrapper = KiwoomWrapper(self.kiwoom)
        self.get_code_list()

    def get_code_list(self):
        self.kospi_codes = self.kiwoom.get_codelist_by_market(MARKET_KOSPI)
        self.kosdak_codes = self.kiwoom.get_codelist_by_market(MARKET_KOSDAK)

    def save_all_data(self):
        today = datetime.date.today().strftime("%Y%m%d")
        #today = datetime.date(2011,9,1).strftime("%Y%m%d")
        print(today, len(self.kosdak_codes), len(self.kospi_codes))
        for code in self.kospi_codes[1200:]:
            print("get data of %s" % code)
            self.save_table(code, today)
        for code in self.kosdak_codes:
            print("get data of %s" % code)
            self.save_table(code, today)

    def save_table(self, code, date):
        data_81 = self.wrapper.get_data_opt10081(code, date)
        data_86 = self.wrapper.get_data_opt10086(code, date)
        col_86 = ['전일비', '등락률', '금액(백만)', '신용비', '개인', '기관', '외인수량', '외국계', '프로그램',
                  '외인비', '체결강도', '외인보유', '외인비중', '외인순매수', '기관순매수', '개인순매수', '신용잔고율']
        data = pd.concat([data_81, data_86.loc[:, col_86]], axis=1)
        con = sqlite3.connect("stock.db")
        try:
            data = data.loc[data.index > self.kiwoom.start_date.strftime("%Y%m%d")]
            orig_data = pd.read_sql("SELECT * FROM '%s'" % code, con, index_col='일자')
            end_date = max(orig_data.index[0], orig_data.index[-1])
            data = data.loc[data.index > end_date]
            data = pd.concat([orig_data, data], axis=0)
        except pd.io.sql.DatabaseError as e:
            print(e)
            pass
        finally:
            data.index.name = '일자'
            if len(data) != 0:
                data.to_sql(code, con, if_exists='replace')


if __name__ == '__main__':
    app = QApplication(sys.argv)

    daily_data = DailyData()
    daily_data.save_all_data()


