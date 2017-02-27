import sys
import time
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import *

TR_REQ_TIME_INTERVAL = 0.2

app = QApplication(sys.argv)

class KiwoomWrapper:
    def __init__(self, kiwoom):
        self.kiwoom = kiwoom

    def get_data_opt10081(self, code, date):
        self.kiwoom.data_opt10081 = [] * 15
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("기준일자", date)
        self.kiwoom.set_input_value("수정주가구분", 255)
        self.kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 0, "0101")
        while self.kiwoom.inquiry == '2' and True:
            time.sleep(0.2)
            self.kiwoom.set_input_value("종목코드", code)
            self.kiwoom.set_input_value("기준일자", date)
            self.kiwoom.set_input_value("수정주가구분", 255)
            self.kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 2, "0101")
        self.kiwoom.data_opt10081.index = self.kiwoom.data_opt10081.loc[:, '일자']
        return self.kiwoom.data_opt10081.loc[:, ['현재가', '거래량', '거래대금', '시가', '고가', '저가']]

    def get_recent_data_opt10081(self, code, date):
        self.kiwoom.data_opt10081 = [] * 15
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("기준일자", date)
        self.kiwoom.set_input_value("수정주가구분", 255)
        self.kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 0, "0101")
        col_name = ['종목코드', '현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가',
                    '수정주가구분', '수정비율', '대업종구분', '소업종구분', '종목정보', '수정주가이벤트', '전일종가']
        self.kiwoom.data_opt10081 = pd.DataFrame(self.kiwoom.data_opt10081, columns=col_name)
        self.kiwoom.data_opt10081.index = self.kiwoom.data_opt10081.loc[:, '일자']
        return self.kiwoom.data_opt10081.loc[:, ['현재가', '거래량', '거래대금', '시가', '고가', '저가']]

    def get_data_opt10086(self, code, date):
        self.kiwoom.data_opt10086 = [] * 23
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("조회일자", date)
        self.kiwoom.set_input_value("표시구분", 1)
        self.kiwoom.comm_rq_data("일별주가요청", "opt10086", 0, "0101")
        while self.kiwoom.inquiry == '2' and True:
            time.sleep(0.2)
            self.kiwoom.set_input_value("종목코드", code)
            self.kiwoom.set_input_value("조회일자", date)
            self.kiwoom.set_input_value("표시구분", 1)
            self.kiwoom.comm_rq_data("일별주가요청", "opt10086", 2, "0101")
        self.kiwoom.data_opt10086.index = self.kiwoom.data_opt10086.loc[:, '일자']
        return self.kiwoom.data_opt10086

    def get_recent_data_opt10086(self, code, date):
        self.kiwoom.data_opt10086 = [] * 23
        self.kiwoom.set_input_value("종목코드", code)
        self.kiwoom.set_input_value("조회일자", date)
        self.kiwoom.set_input_value("표시구분", 1)
        self.kiwoom.comm_rq_data("일별주가요청", "opt10086", 0, "0101")
        col_name = ['일자', '시가', '고가', '저가', '종가', '전일비', '등락률', '거래량',
                    '금액(백만)', '신용비', '개인', '기관', '외인수량', '외국계', '프로그램',
                    '외인비', '체결강도', '외인보유', '외인비중', '외인순매수', '기관순매수',
                    '개인순매수', '신용잔고율']
        self.kiwoom.data_opt10086 = pd.DataFrame(self.kiwoom.data_opt10086, columns=col_name)
        self.kiwoom.data_opt10086.index = self.kiwoom.data_opt10086.loc[:, '일자']
        for col in self.data_opt10086.columns:
            self.kiwoom.data_opt10086.loc[:, col] = self.kiwoom.data_opt10086.loc[:, col].str.replace('--', '-')
        return self.data_opt10086



