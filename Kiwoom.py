import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
import time

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        self.OnEventConnect.connect(self.event_connect)
        self.OnReceiveTrData.connect(self.onReceiveTrData)
        self.OnReceiveChejanData.connect(self.onReceiveChejanData)

    def init_opw00018_data(self):
        self.data_opw00018 = {'single': [], 'multi': []}

    def event_connect(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("not connected")
        self.login_loop.exit()

    def onReceiveTrData(self, scrno, rqname, trcode, record_name, next, unused0, unused1, unused2, unused3):
        self.remained_data = next
        if rqname == "opt10081_req":
            cnt = self.get_repeat_cnt(trcode, rqname)
            for i in range(cnt):
                date   = self.comm_get_data(trcode, "", rqname, i, "일자")
                open   = self.comm_get_data(trcode, "", rqname, i, "시가")
                high   = self.comm_get_data(trcode, "", rqname, i, "고가")
                low    = self.comm_get_data(trcode, "", rqname, i, "저가")
                close  = self.comm_get_data(trcode, "", rqname, i, "현재가")
                volume = self.comm_get_data(trcode, "", rqname, i, "거래량")

                self.ohlcv['date'].append(date)
                self.ohlcv['open'].append(int(open))
                self.ohlcv['high'].append(int(high))
                self.ohlcv['low'].append(int(low))
                self.ohlcv['close'].append(int(close))
                self.ohlcv['volume'].append(int(volume))

        if rqname == "opw00001_req":
            estimate_day2_deposit = self.comm_get_data(trcode, "", rqname, 0, "d+2추정예수금")
            estimate_day2_deposit = self.change_format(estimate_day2_deposit)
            self.data_opw00001 = estimate_day2_deposit
        if rqname == 'opw00018_req':
            # Single Data
            single = []

            total_purchase_price = self.comm_get_data(trcode, "", rqname, 0, "총매입금액")
            total_purchase_price = self.change_format(total_purchase_price)
            single.append(total_purchase_price)

            total_eval_price = self.comm_get_data(trcode, "", rqname, 0, "총평가금액")
            total_eval_price = self.change_format(total_eval_price)
            single.append(total_eval_price)

            total_eval_profit_loss_price = self.comm_get_data(trcode, "", rqname, 0, "총평가손익금액")
            total_eval_profit_loss_price = self.change_format(total_eval_profit_loss_price)
            single.append(total_eval_profit_loss_price)

            total_earning_rate = self.comm_get_data(trcode, "", rqname, 0, "총수익률(%)")
            total_earning_rate = self.change_format(total_earning_rate)
            single.append(total_earning_rate)

            estimated_deposit = self.comm_get_data(trcode, "", rqname, 0, "추정예탁자산")
            estimated_deposit = self.change_format(estimated_deposit)
            single.append(estimated_deposit)

            self.data_opw00018['single'] = single

            # Multi Data
            cnt = self.get_repeat_cnt(trcode, rqname)
            for i in range(cnt):
                data = []

                item_name = self.comm_get_data(trcode, "", rqname, i, "종목명")
                data.append(item_name)

                quantity = self.comm_get_data(trcode, "", rqname, i, "보유수량")
                quantity = self.change_format(quantity)
                data.append(quantity)

                purchase_price = self.comm_get_data(trcode, "", rqname, i, "매입가")
                purchase_price = self.change_format(purchase_price)
                data.append(purchase_price)

                current_price = self.comm_get_data(trcode, "", rqname, i, "현재가")
                current_price = self.change_format(current_price)
                data.append(current_price)

                eval_profit_loss_price = self.comm_get_data(trcode, "", rqname, i, "평가손익")
                eval_profit_loss_price = self.change_format(eval_profit_loss_price)
                data.append(eval_profit_loss_price)

                earning_rate = self.comm_get_data(trcode, "", rqname, i, "수익률(%)")
                earning_rate = self.change_format(earning_rate, 2)
                data.append(earning_rate)

                self.data_opw00018['multi'].append(data)
        try:
            self.tr_rq_loop.exit()
        except AttributeError:
            pass

    def onReceiveChejanData(self, sGubun, nItemCnt, sFidList):
        print("sGubun: ", sGubun)
        print(self.GetChejanData(9203))
        print(self.GetChejanData(302))
        print(self.GetChejanData(900))
        print(self.GetChejanData(901))

    def get_repeat_cnt(self, code, record_name):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", code, record_name)
        return ret

    def get_codelist_by_market(self, market):
        func = 'GetCodeListByMarket("%s")' % market
        codes = self.dynamicCall(func)
        return codes.split(';')


    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def getConnectState(self):
        ret = self.dynamicCall("GetConnectState()")
        return ret

    def GetLoginInfo(self, sTag):
        cmd = 'GetLoginInfo("%s")' % sTag
        ret = self.dynamicCall(cmd)
        return ret

    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, rqname, code, next, screen_no):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, code, next, screen_no)
        self.tr_rq_loop = QEventLoop()
        self.tr_rq_loop.exec_()

    def comm_get_data(self, code, real_type, field_name, index, item_name):
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code, real_type,
                               field_name, index, item_name)
        return ret.strip()

    def GetChejanData(self, nFid):
        cmd = 'GetChejanData("%s")' % nFid
        ret = self.dynamicCall(cmd)
        return ret

    def sendOrder(self, sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice, sHogaGb, sOrgOrderNo):
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", [sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice, sHogaGb, sOrgOrderNo])

    def initOHLCRawData(self):
        self.ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}

    def change_format(self, data, percent=0):
        is_minus = False
        if data.startswith('-'):
            is_minus = True
        strip_str = data.lstrip('-0')
        if strip_str == '':
            if percent == 1:
                return '0.00'
            else:
                return '0'
        if percent == 1:
            strip_data = int(strip_str)
            strip_data = strip_data / 100
            form = format(strip_data, ',.2f')
        elif percent == 2:
            strip_data = float(strip_str)
            form = format(strip_data, ',.2f')
        else:
            strip_data = int(strip_str)
            form = format(strip_data, ',d')
        if form.startswith('.'):
            form = '0' + form
        if is_minus:
            form = '-' + form
        return form

    def get_master_code_name(self, code):
        func = 'GetMasterCodeName("%s")' % code
        name = self.dynamicCall(func)
        return name


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Test Code
    kiwoom = Kiwoom()
    kiwoom.comm_connect()


    # opw00018
    kiwoom.init_opw00018_data()

    kiwoom.set_input_value("계좌번호", "8086919011")
    kiwoom.set_input_value("비밀번호", "0000")
    kiwoom.comm_rq_data("opw00018_req", "opw00018", 0, "2000")

    while kiwoom.remained_data == '2':
        time.sleep(0.2)
        kiwoom.set_input_value("계좌번호", "8086919011")
        kiwoom.set_input_value("비밀번호", "0000")
        kiwoom.comm_rq_data("opw00018_req", "opw00018", 2, "2000")

    print(kiwoom.data_opw00018['single'])
    print(kiwoom.data_opw00018['multi'])
