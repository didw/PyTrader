"""
QtDesigner로 만든 UI와 해당 UI의 위젯에서 발생하는 이벤트를 컨트롤하는 클래스

author: Jongyeol Yang
last edit: 2017. 02. 23
"""


import sys, time
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5 import uic
from Kiwoom import Kiwoom, ParameterTypeError, ParameterValueError, KiwoomProcessingError, KiwoomConnectError
import codecs

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
        self.accountComboBox.addItems(accounts_list)

        # 메인 타이머
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)

        # 잔고 및 보유종목 조회 타이머
        self.inquiryTimer = QTimer(self)
        self.inquiryTimer.start(1000 * 10)
        self.inquiryTimer.timeout.connect(self.timeout2)

        self.codeLineEdit.textChanged.connect(self.set_code_name)
        self.orderBtn.clicked.connect(self.send_order)
        self.inquiryBtn.clicked.connect(self.inquiry_balance)

        self.load_buy_sell_list()
        self.conduct_buy_sell()

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

    def timeout2(self):
        if self.checkBox.isChecked() == True:
            self.inquiry_balance()
            self.load_buy_sell_list()

    def set_code_name(self):
        """ 종목코드에 해당하는 한글명을 codeNameLineEdit에 설정한다. """
        code = self.codeLineEdit.text()
        code_name = self.kiwoom.get_master_code_name(code)
        self.codeNameLineEdit.setText(code_name)

    def send_order(self):
        """ 키움서버로 주문정보를 전송한다. """
        order_type_table = {'신규매수': 1, '신규매도': 2, '매수취소': 3, '매도취소': 4}
        hoga_type_table = {'지정가': "00", '시장가': "03"}

        account = self.accountComboBox.currentText()
        order_type = order_type_table[self.orderTypeComboBox.currentText()]
        code = self.codeLineEdit.text()
        hoga_type = hoga_type_table[self.hogaTypeComboBox.currentText()]
        qty = self.qtySpinBox.value()
        price = self.priceSpinBox.value()
		
        try:
            self.kiwoom.SendOrder("수동주문", "0101", account, order_type, code, qty, price, hoga_type, "")
        except (ParameterTypeError, KiwoomProcessingError) as e:
            self.showDialog('Critical', e)

    def inquiry_balance(self):
        """ 예수금상세현황과 계좌평가잔고내역을 요청후 테이블에 출력한다. """

        self.inquiryTimer.stop()
        try:
            self.kiwoom.init_opw00018_data()
            # 계좌평가잔고내역요청 - opw00018 은 한번에 20개의 종목정보를 반환
            self.kiwoom.set_input_value("계좌번호", self.accountComboBox.currentText())
            self.kiwoom.set_input_value("비밀번호", "0000")
            self.kiwoom.comm_rq_data("계좌평가잔고내역요청", "opw00018", 0, "2000")
            while self.kiwoom.remained_data == '2':
                time.sleep(0.2)
                self.kiwoom.set_input_value("계좌번호", self.accountComboBox.currentText())
                self.kiwoom.set_input_value("비밀번호", "0000")
                self.kiwoom.comm_rq_data("계좌평가잔고내역요청", "opw00018", 2, "2000")
            # 예수금상세현황요청
            self.kiwoom.set_input_value("계좌번호", self.accountComboBox.currentText())
            self.kiwoom.set_input_value("비밀번호", "0000")
            self.kiwoom.comm_rq_data("예수금상세현황요청", "opw00001", 0, "2000")
        except (ParameterTypeError, ParameterValueError, KiwoomProcessingError) as e:
            self.showDialog('Critical', e)

        # accountEvaluationTable 테이블에 정보 출력

        item = QTableWidgetItem(self.kiwoom.data_opw00001)
        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.tableWidget.setItem(0, 0, item)

        for i in range(1, 6):
            item = QTableWidgetItem(self.kiwoom.data_opw00018['single'][i-1])
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.tableWidget.setItem(0, i, item)

        self.tableWidget.resizeRowsToContents()

        # Item list
        item_count = len(self.kiwoom.data_opw00018['multi'])
        self.stocksTable.setRowCount(item_count)

        for j in range(item_count):
            row = self.kiwoom.data_opw00018['multi'][j]
            for i in range(len(row)):
                item = QTableWidgetItem(row[i])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                self.stocksTable.setItem(j, i, item)

        self.stocksTable.resizeRowsToContents()
        # inquiryTimer 재시작
        self.inquiryTimer.start(1000 * 10)

    def load_buy_sell_list(self):
        f = open("buy_list.txt", "rt")
        buy_list = f.readlines()
        f.close()

        f = open("sell_list.txt", "rt")
        sell_list = f.readlines()
        f.close()

        row_count = len(buy_list) + len(sell_list)
        self.tableWidget_3.setRowCount(row_count)

        # buy list
        for j in range(len(buy_list)):
            row_data = buy_list[j]
            split_row_data = row_data.split(';')
            for i in range(len(split_row_data)):
                if i == 1:
                    name = self.kiwoom.GetMasterCodeName(split_row_data[i].rstrip())
                    item = QTableWidgetItem(name)
                else:
                    item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.tableWidget_3.setItem(j, i, item)

        # sell list
        for j in range(len(sell_list)):
            row_data = sell_list[j]
            split_row_data = row_data.split(';')
            for i in range(len(split_row_data)):
                if i == 1:
                    name = self.kiwoom.GetMasterCodeName(split_row_data[i].rstrip())
                    item = QTableWidgetItem(name)
                else:
                    item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.tableWidget_3.setItem(len(buy_list) + j, i, item)

        self.tableWidget_3.resizeRowsToContents()

    def conduct_buy_sell(self):
        hoga_lookup = {'지정가': "00", '시장가': "03"}

        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        f.close()

        f = open("sell_list.txt", 'rt')
        sell_list = f.readlines()
        f.close()

        account = self.accountComboBox.currentText()

        # 주문하기
        buyResult = []
        sellResult = []

        # buy list
        for row_data in buy_list:
            split_row_data = row_data.split(';')
            code    = split_row_data[1]
            hoga    = split_row_data[2]
            num     = split_row_data[3]
            price   = split_row_data[4]

            if split_row_data[-1].rstrip() == '매수전':
                self.kiwoom.sendOrder("수동주문", "0101", account, 1, code, num, price, hoga_lookup[hoga], "")

                # 주문 접수시
                if self.kiwoom.orderNo:
                    buyResult += automatedStocks[i].replace("매수전", "매수주문완료")
                    self.kiwoom.orderNo = ""
                # 주문 미접수시
                else:
                    buyResult += automatedStocks[i]

        # sell list
        for row_data in sell_list:
            split_row_data = row_data.split(';')
            hoga    = split_row_data[2]
            code    = split_row_data[1]
            num     = split_row_data[3]
            price   = split_row_data[4]

            if split_row_data[-1].rstrip() == '매도전':
                self.kiwoom.sendOrder("수동주문", "0101", account, 2, code, num, price, hoga_lookup[hoga], "")

                # 주문 접수시
                if self.kiwoom.orderNo:
                    sellResult += automatedStocks[i].replace("매도전", "매도주문완료")
                    self.kiwoom.orderNo = ""
                # 주문 미접수시
                else:
                    sellResult += automatedStocks[i]

        # 잔고및 보유종목 디스플레이 갱신
        self.inquiry_balance()

        # file update
        f = open("buy_list.txt", 'wt')
        for row_data in buy_list:
            f.write(row_data)
        f.close()

        # file update
        f = open("sell_list.txt", 'wt')
        for row_data in sell_list:
            f.write(row_data)
        f.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()
