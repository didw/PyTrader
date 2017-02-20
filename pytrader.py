import sys
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5 import uic
from Kiwoom import *

form_class = uic.loadUiType("pytrader.ui")[0]

class MyWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()

        # Get Account Number
        accouns_num = int(self.kiwoom.GetLoginInfo("ACCOUNT_CNT"))
        accounts = self.kiwoom.GetLoginInfo("ACCNO")
        accounts_list = accounts.split(';')[0:accouns_num]
        self.comboBox.addItems(accounts_list)

        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)

        self.lineEdit.textChanged.connect(self.code_changed)

        self.pushButton.clicked.connect(self.send_order)

    def timeout(self):
        current_time = QTime.currentTime()
        text_time = current_time.toString("hh:mm:ss")
        time_msg = "현재시간: " + text_time

        state = self.kiwoom.GetConnectState()
        if state == 1:
            state_msg = "서버 연결 중"
        else:
            state_msg = "서버 미 연결 중"

        self.statusbar.showMessage(state_msg + " | " + time_msg)

    def code_changed(self):
        code = self.lineEdit.text()
        code_name = self.kiwoom.GetMasterCodeName(code)
        self.lineEdit_2.setText(code_name)

    def send_order(self):
        order_type_lookup = {'신규매수': 1, '신규매도': 2, '매수취소': 3, '매도취소': 4}
        hoga_lookup = {'지정가': "00", '시장가': "03"}

        account = self.comboBox.currentText()
        order_type = self.comboBox_2.currentText()
        code = self.lineEdit.text()
        hoga = self.comboBox_3.currentText()
        num = self.spinBox.value()
        price = self.spinBox_2.value()
        self.kiwoom.SendOrder("SendOrder_req", "0101", account, order_type_lookup[order_type], code, num, price, hoga_lookup[hoga], "")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()
