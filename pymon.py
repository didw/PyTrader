import sys
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5 import uic
from PyQt5.QtWidgets import *
import test_kiwoom
import pandas as pd
import time
import datetime
import webreader

MARKET_KOSPI   = 0
MARKET_KOSDAK  = 10

class PyMon:
    def __init__(self):
        self.kiwoom = test_kiwoom.Kiwoom()
        self.kiwoom.comm_connect()
        self.get_code_list()

    def get_code_list(self):
        self.kospi_codes = self.kiwoom.get_codelist_by_market(MARKET_KOSPI)
        self.kosdak_codes = self.kiwoom.get_codelist_by_market(MARKET_KOSDAK)

    def get_ohlcv(self, code, start_date):
        # Init data structure
        self.kiwoom.initOHLCRawData()

        # Request TR and get data
        data = self.kiwoom.get_opt10081(code, start_date)
        # DataFrame
        col_name = ['종목코드', '현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가',
                    '수정주가구분', '수정비율', '대업종구분', '소업종구분', '종목정보', '수정주가이벤트', '전일종가']
        df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'],
                          index=self.kiwoom.ohlcv['date'])
        return df

    def check_speedy_rising_volume(self, code):
        today = datetime.datetime.today().strftime("%Y%m%d")
        df = self.get_ohlcv(code, today)
        volumes = df['volume']

        sum_vol20 = 0
        avg_vol20 = 0

        # Check small trading days
        if len(volumes) < 21:
            return False

        # Accumulation
        for i, vol in enumerate(volumes):
            if i == 0:
                today_vol = vol
            elif i >= 1 and i <= 20:
                sum_vol20 += vol
            elif i >= 21:
                break

        #  Average and decision
        avg_vol20 = sum_vol20 / 20;
        if today_vol > avg_vol20 * 10:
            return True
        return False

    def update_buy_list(self, buy_list):
        f = open("buy_list.txt", "wt")
        for code in buy_list:
            f.writelines("매수;%s;시장가;10;0;매수전\n" % (code))
        f.close()

    def calculate_estimated_dividend_to_treasury(self, code):
        dividend_yield = webreader.get_estimated_dividend_yield(code)

        if pd.isnull(dividend_yield):
            dividend_yield = webreader.get_dividend_yield(code)

        dividend_yield = float(dividend_yield)
        current_3year_treasury = float(webreader.get_current_3year_treasury())
        estimated_dividend_to_treasury = dividend_yield / current_3year_treasury
        return estimated_dividend_to_treasury

    def get_min_max_dividend_to_treasury(self, code):
        previous_dividend_yield = webreader.get_previous_dividend_yield(code)
        three_years_treasury = webreader.get_3year_treasury()

        now = datetime.datetime.now()
        cur_year = now.year
        previous_dividend_to_treasury = {}

        for year in range(cur_year-5, cur_year):
            if year in previous_dividend_yield.keys() and year in three_years_treasury.keys():
                ratio = float(previous_dividend_yield[year]) / float(three_years_treasury[year])
                previous_dividend_to_treasury[year] = ratio

        print(previous_dividend_to_treasury)
        min_ratio = min(previous_dividend_to_treasury.values())
        max_ratio = max(previous_dividend_to_treasury.values())

        return min_ratio, max_ratio

    def buy_check_by_dividend_algorithm(self, code):
        estimated_dividend_to_treasury = self.calculate_estimated_dividend_to_treasury(code)
        (min_ratio, max_ratio) = self.get_min_max_dividend_to_treasury(code)

        if estimated_dividend_to_treasury > max_ratio:
            return 1, estimated_dividend_to_treasury
        else:
            return 0, estimated_dividend_to_treasury

    def run_dividend(self):
        buy_list = []

        for code in self.kospi_codes[0:50]:
            time.sleep(0.5)
            ret = self.buy_check_by_dividend_algorithm(code)
            if ret[0] == 1:
                buy_list.append((code, ret[1]))

        sorted_list = sorted(buy_list, key=lambda code:code[1], reverse=True)

        # Buy list
        buy_list = []
        for i in range(0, 5):
            code = sorted_list[i][0]
            buy_list.append(code)

        self.update_buy_list(buy_list)

    def run(self):
        buy_list = []
        num = len(self.kosdak_codes)
        for i, code in enumerate(self.kosdak_codes):
            print(i, ":", num)
            if self.check_speedy_rising_volume(code):
                print("급등주: %s, %s" % (code, self.kiwoom.get_master_code_name(code)))
                buy_list.append(code)
        self.update_buy_list(buy_list)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pymon = PyMon()
    #pymon.run()
    #print(pymon.calculate_estimated_dividend_to_treasury('058470'))
    #print(pymon.get_min_max_dividend_to_treasury('058470'))
    #print(pymon.buy_check_by_dividend_algorithm('058470'))
    pymon.run_dividend()
