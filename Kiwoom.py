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
        self.OnReceiveTrData.connect(self.receive_tr_data)
        self.OnReceiveChejanData.connect(self.OnReceiveChejanData)

    def comm_connect(self):
        self.dynamicCall("CommConnect()")
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def event_connect(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("not connected")

        self.login_loop.exit()

    def get_codelist_by_market(self, market):
        func = 'GetCodeListByMarket("%s")' % market
        codes = self.dynamicCall(func)
        return codes.split(';')

    def get_master_code_name(self, code):
        func = 'GetMasterCodeName("%s")' % code
        name = self.dynamicCall(func)
        return name

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

    def receive_tr_data(self, scrno, rqname, trcode, record_name, next, unused0, unused1, unused2, unused3):
        self.remained_data = next
        if rqname == "opt10081_req":
            cnt = self.get_repeat_cnt(trcode, rqname)

            for i in range(cnt):
                date  = self.comm_get_data(trcode, "", rqname, i, "일자")
                open  = self.comm_get_data(trcode, "", rqname, i, "시가")
                high  = self.comm_get_data(trcode, "", rqname, i, "고가")
                low   = self.comm_get_data(trcode, "", rqname, i, "저가")
                end   = self.comm_get_data(trcode, "", rqname, i, "현재가")
                print(date, open, high, low, end)

        self.tr_rq_loop.exit()

    def get_repeat_cnt(self, code, record_name):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", code, record_name)
        return ret

    def SendOrder(self, sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice, sHogaGb, sOrgOrderNo):
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", [sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, nPrice, sHogaGb, sOrgOrderNo])

    def GetChejanData(self, nFid):
        cmd = 'GetChejanData("%s")' % nFid
        ret = self.dynamicCall(cmd)
        return ret

    def OnReceiveChejanData(self, sGubun, nItemCnt, sFidList):
        print("sGubun: ", sGubun)
        print(self.GetChejanData(9203))
        print(self.GetChejanData(302))
        print(self.GetChejanData(900))
        print(self.GetChejanData(901))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Test Code
    kiwoom = Kiwoom()
    kiwoom.comm_connect()

    # opt10081 TR Test Code
    kiwoom.set_input_value("종목코드", "039490")
    kiwoom.set_input_value("기준일자", "20161017")
    kiwoom.set_input_value("수정주가구분", 1)
    kiwoom.comm_rq_data("opt10081_req", "opt10081", 0, "0101")

    while kiwoom.remained_data == '2':
        time.sleep(0.2)
        kiwoom.set_input_value("종목코드", "039490")
        kiwoom.set_input_value("기준일자", "20161017")
        kiwoom.set_input_value("수정주가구분", 1)
        kiwoom.comm_rq_data("opt10081_req", "opt10081", 2, "0101")
