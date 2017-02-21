import sys
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5 import uic
from PyQt5.QtWidgets import *
import Kiwoom
import pandas as pd
import time

MARKET_KOSPI   = 0
MARKET_KOSDAK  = 10

class PyMon:
    def __init__(self):
        self.kiwoom = Kiwoom.Kiwoom()
        self.kiwoom.comm_connect()
        self.get_code_list()

    def get_code_list(self):
        self.kospi_codes = self.kiwoom.get_codelist_by_market(MARKET_KOSPI)
        self.kosdak_codes = self.kiwoom.get_codelist_by_market(MARKET_KOSDAK)

    def get_ohlcv(self, code, start_date):
        # Init data structure
        self.kiwoom.initOHLCRawData()

        # Request TR and get data
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("기준일자", start_date)
        self.kiwoom.set_input_value("수정주가구분", 1)
        self.kiwoom.comm_rq_data("opt10081_req", "opt10081", 0, "0101")
        time.sleep(0.2)

        # DataFrame
        df = pd.DataFrame(self.kiwoom.ohlcv, columns=['open', 'high', 'low', 'close', 'volume'],
                          index=self.kiwoom.ohlcv['date'])
        return df

    def run(self):
        print(self.get_ohlcv("039490", "20160826"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pymon = PyMon()
    pymon.run()
