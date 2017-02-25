import sys
from PyQt5.QtWidgets import QApplication
from Kiwoom import Kiwoom, ParameterTypeError, ParameterValueError, KiwoomProcessingError, KiwoomConnectError
import numpy as np
import sqlite3


class StockData:
    def __init__(self):
        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()

    def save_table(self, code, date):
        data = self.kiwoom.get_data_opt10081(code, date)
        con = sqlite3.connect("stock.db")
        data.to_sql(code, con, if_exists='replace')

if __name__ == '__main__':
    app = QApplication(sys.argv)

    stock_data = StockData()
    stock_data.save_table("035420", "20170101")

