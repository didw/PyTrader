import sys
import time
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import *
import sqlite3

TR_REQ_TIME_INTERVAL = 4

app = QApplication(sys.argv)

class KiwoomWrapper:
    def __init__(self, kiwoom):
        self.kiwoom = kiwoom

    def get_data_opt10081(self, code, date='20161231'):
        try:
            data = pd.read_hdf("../data/hdf/%s.hdf" % code, 'day').sort_index()
            start = str(data.index[-2])
        except (FileNotFoundError, IndexError)  as e:
            start = "20010101"
        print("get 81 data from %s" % start)
        self.kiwoom.start_date = datetime.strptime(start, "%Y%m%d")
        self.kiwoom.data_opt10081 = [] * 15
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("기준일자", date)
        self.kiwoom.set_input_value("수정주가구분", 255)
        self.kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 0, "0101")
        while self.kiwoom.inquiry == '2':
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.kiwoom.set_input_value("종목코드", code)
            self.kiwoom.set_input_value("기준일자", date)
            self.kiwoom.set_input_value("수정주가구분", 255)
            self.kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 2, "0101")
        self.kiwoom.data_opt10081.index = self.kiwoom.data_opt10081.loc[:, '일자']
        return self.kiwoom.data_opt10081.loc[:, ['현재가', '거래량', '거래대금', '시가', '고가', '저가']]

    def get_data_opt10086(self, code, date):
        try:
            data = pd.read_hdf("../data/hdf/%s.hdf" % code, 'day').sort_index()
            start = str(data.index[-2])
        except (FileNotFoundError, IndexError) as e:
            start = "20010101"
        print("get 86 data from %s" % start)
        self.kiwoom.start_date = datetime.strptime(start, "%Y%m%d")
        self.kiwoom.data_opt10086 = [] * 23
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("조회일자", date)
        self.kiwoom.set_input_value("표시구분", 1)
        self.kiwoom.comm_rq_data("일별주가요청", "opt10086", 0, "0101")
        while self.kiwoom.inquiry == '2':
            time.sleep(TR_REQ_TIME_INTERVAL)
            self.kiwoom.set_input_value("종목코드", code)
            self.kiwoom.set_input_value("조회일자", date)
            self.kiwoom.set_input_value("표시구분", 1)
            self.kiwoom.comm_rq_data("일별주가요청", "opt10086", 2, "0101")
        self.kiwoom.data_opt10086.index = self.kiwoom.data_opt10086.loc[:, '일자']
        return self.kiwoom.data_opt10086

if __name__ == '__main__':
    from pykiwoom.kiwoom import Kiwoom
    kiwoom = Kiwoom()
    kiwoom_wrapper = KiwoomWrapper(kiwoom)
    kiwoom_wrapper.get_data_opt10081('000660', "20161231")
