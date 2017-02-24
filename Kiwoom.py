"""
Kiwoom 클래스는 OCX를 통해 API 함수를 호출할 수 있도록 구현되어 있습니다.
OCX 사용을 위해 QAxWidget 클래스를 상속받아서 구현하였으며,
주식(현물) 거래에 필요한 메서드들만 구현하였습니다.

author: Jongyeol Yang
last edit: 2017. 02. 23
"""
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

        # Loop 변수
        # 비동기 방식으로 동작되는 이벤트를 동기화(순서대로 동작) 시킬 때
        self.login_loop = None
        self.request_loop = None
        self.order_loop = None
        self.condition_loop = None

        # 서버구분
        self.server_gubun = None

        # 조건식
        self.condition = None

        # 에러
        self.error = None

        # 주문번호
        self.order_no = ""

        # 조회
        self.inquiry = 0

        # 서버에서 받은 메시지
        self.msg = ""

        # 예수금 d+2
        self.data_opw00001 = 0

        # 보유종목 정보
        self.data_opw00018 = {'accountEvaluation': [], 'stocks': []}

        # signal & slot
        self.OnEventConnect.connect(self.event_connect)
        self.OnReceiveTrData.connect(self.onReceiveTrData)
        self.OnReceiveChejanData.connect(self.onReceiveChejanData)

    def init_opw00018_data(self):
        self.data_opw00018 = {'single': [], 'multi': []}

    ###############################################################
    # 이벤트 정의                                                    #
    ###############################################################

    def event_connect(self, return_code):
        """
        통신 연결 상태 변경시 이벤트

        returnCode가 0이면 로그인 성공
        그 외에는 ReturnCode 클래스 참조.

        :param returnCode: int
        """
        try:
            if returnCode == ReturnCode.OP_ERR_NONE:

                if self.getLoginInfo("GetServerGubun", True):
                    self.msg += "실서버 연결 성공" + "\r\n\r\n"

                else:
                    self.msg += "모의투자서버 연결 성공" + "\r\n\r\n"

            else:
                self.msg += "연결 끊김: 원인 - " + ReturnCode.CAUSE[returnCode] + "\r\n\r\n"

        except Exception as error:
            self.log.error('eventConnect {}'.format(error))

        finally:
            # commConnect() 메서드에 의해 생성된 루프를 종료시킨다.
            # 로그인 후, 통신이 끊길 경우를 대비해서 예외처리함.
            try:
                self.login_loop.exit()
            except AttributeError:
                pass

    def comm_rq_data(self, rqname, code, next, screen_no):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, code, next, screen_no)
        self.tr_rq_loop = QEventLoop()
        self.tr_rq_loop.exec_()

    def onReceiveTrData(self, screen_no, request_name, tr_code, record_name, inquiry, unused0, unused1, unused2, unused3):
        """
        TR 수신 이벤트

        조회요청 응답을 받거나 조회데이터를 수신했을 때 호출됩니다.
        request_name tr_code commRqData()메소드의 매개변수와 매핑되는 값 입니다.
        조회데이터는 이 이벤트 메서드 내부에서 getCommData() 메서드를 이용해서 얻을 수 있습니다.

        :param screen_no: string - 화면번호(4자리)
        :param request_name: string - TR 요청명(commRqData() 메소드 호출시 사용된 requestName)
        :param tr_code: string
        :param record_name: string
        :param inquiry: string - 조회('0': 남은 데이터 없음, '2': 남은 데이터 있음)
        """

        print("receiveTrData 실행: ", screen_no, request_name, tr_code, record_name, inquiry)

        # 주문번호와 주문루프
        self.order_no = self.comm_get_data(tr_code, "", request_name, 0, "주문번호")

        try:
            self.orderLoop.exit()
        except AttributeError:
            pass

        self.remained_data = inquiry
        if request_name == "주식일봉차트조회요청":
            cnt = self.get_repeat_cnt(tr_code, request_name)
            for i in range(cnt):
                date   = self.comm_get_data(tr_code, "", request_name, i, "일자")
                open   = self.comm_get_data(tr_code, "", request_name, i, "시가")
                high   = self.comm_get_data(tr_code, "", request_name, i, "고가")
                low    = self.comm_get_data(tr_code, "", request_name, i, "저가")
                close  = self.comm_get_data(tr_code, "", request_name, i, "현재가")
                volume = self.comm_get_data(tr_code, "", request_name, i, "거래량")

                self.ohlcv['date'].append(date)
                self.ohlcv['open'].append(int(open))
                self.ohlcv['high'].append(int(high))
                self.ohlcv['low'].append(int(low))
                self.ohlcv['close'].append(int(close))
                self.ohlcv['volume'].append(int(volume))

        if request_name == "예수금상세현황요청":
            estimate_day2_deposit = self.comm_get_data(tr_code, "", request_name, 0, "d+2추정예수금")
            estimate_day2_deposit = self.change_format(estimate_day2_deposit)
            self.data_opw00001 = estimate_day2_deposit
            
        if request_name == '계좌평가잔고내역요청':
            # Single Data
            single = []

            total_purchase_price = self.comm_get_data(tr_code, "", request_name, 0, "총매입금액")
            total_purchase_price = self.change_format(total_purchase_price)
            single.append(total_purchase_price)

            total_eval_price = self.comm_get_data(tr_code, "", request_name, 0, "총평가금액")
            total_eval_price = self.change_format(total_eval_price)
            single.append(total_eval_price)

            total_eval_profit_loss_price = self.comm_get_data(tr_code, "", request_name, 0, "총평가손익금액")
            total_eval_profit_loss_price = self.change_format(total_eval_profit_loss_price)
            single.append(total_eval_profit_loss_price)

            total_earning_rate = self.comm_get_data(tr_code, "", request_name, 0, "총수익률(%)")
            total_earning_rate = self.change_format(total_earning_rate)
            single.append(total_earning_rate)

            estimated_deposit = self.comm_get_data(tr_code, "", request_name, 0, "추정예탁자산")
            estimated_deposit = self.change_format(estimated_deposit)
            single.append(estimated_deposit)

            self.data_opw00018['single'] = single

            # Multi Data
            cnt = self.get_repeat_cnt(tr_code, request_name)
            for i in range(cnt):
                data = []

                item_name = self.comm_get_data(tr_code, "", request_name, i, "종목명")
                data.append(item_name)

                quantity = self.comm_get_data(tr_code, "", request_name, i, "보유수량")
                quantity = self.change_format(quantity)
                data.append(quantity)

                purchase_price = self.comm_get_data(tr_code, "", request_name, i, "매입가")
                purchase_price = self.change_format(purchase_price)
                data.append(purchase_price)

                current_price = self.comm_get_data(tr_code, "", request_name, i, "현재가")
                current_price = self.change_format(current_price)
                data.append(current_price)

                eval_profit_loss_price = self.comm_get_data(tr_code, "", request_name, i, "평가손익")
                eval_profit_loss_price = self.change_format(eval_profit_loss_price)
                data.append(eval_profit_loss_price)

                earning_rate = self.comm_get_data(tr_code, "", request_name, i, "수익률(%)")
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

    ###############################################################
    # 메서드 정의: 로그인 관련 메서드                                    #
    ###############################################################

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

    #################################################################
    # 메서드 정의: 조회 관련 메서드                                        #
    # 시세조회, 관심종목 조회, 조건검색 등 이들의 합산 조회 횟수가 1초에 5회까지 허용 #
    #################################################################

    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)


    def comm_get_data(self, code, real_type, field_name, index, item_name):
        """
        데이터 획득 메서드

        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 조회데이터를 얻어오는 메서드입니다.

        :param code: string
        :param real_type: string - TR 요청시 ""(빈문자)로 처리
        :param field_name: string - TR 요청명(commRqData() 메소드 호출시 사용된 field_name)
        :param index: int
        :param item_name: string
        :return: string
        """
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code, real_type,
                               field_name, index, item_name)
        return ret.strip()


    ###############################################################
    # 메서드 정의: 주문과 잔고처리 관련 메서드                              #
    # 1초에 5회까지 주문 허용                                          #
    ###############################################################

    def send_order(self, request_name, screen_no, account_no, order_type, code, qty, price, hoga_type, origin_order_no):
        """
        주식 주문 메서드

        send_order() 메소드 실행시,
        OnReceiveMsg, OnReceiveTrData, OnReceiveChejanData 이벤트가 발생한다.
        이 중, 주문에 대한 결과 데이터를 얻기 위해서는 OnReceiveChejanData 이벤트를 통해서 처리한다.
        OnReceiveTrData 이벤트를 통해서는 주문번호를 얻을 수 있는데, 주문후 이 이벤트에서 주문번호가 ''공백으로 전달되면,
        주문접수 실패를 의미한다.

        :param request_name: string - 주문 요청명(사용자 정의)
        :param screen_no: string - 화면번호(4자리)
        :param account_no: string - 계좌번호(10자리)
        :param order_type: int - 주문유형(1: 신규매수, 2: 신규매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도정정)
        :param code: string - 종목코드
        :param qty: int - 주문수량
        :param price: int - 주문단가
        :param hoga_type: string - 거래구분(00: 지정가, 03: 시장가, 05: 조건부지정가, 06: 최유리지정가, 그외에는 api 문서참조)
        :param origin_order_no: string - 원주문번호(신규주문에는 공백, 정정및 취소주문시 원주문번호르 입력합니다.)
        """
        if not self.getConnectState():
            raise KiwoomConnectError()

        if not (isinstance(request_name, str)
                and isinstance(screen_no, str)
                and isinstance(account_no, str)
                and isinstance(order_type, int)
                and isinstance(code, str)
                and isinstance(qty, int)
                and isinstance(price, int)
                and isinstance(hoga_type, str)
                and isinstance(origin_order_no, str)):

            raise ParameterTypeError()

        return_code = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)", [request_name, screen_no, account_no, order_type, code, qty, price, hoga_type, origin_order_no])

        if return_code != ReturnCode.OP_ERR_NONE:
            raise KiwoomProcessingError("sendOrder(): " + ReturnCode.CAUSE[return_code])

        # receiveTrData() 에서 루프종료
        self.order_loop = QEventLoop()
        self.order_loop.exec_()

    def GetChejanData(self, nFid):
        cmd = 'GetChejanData("%s")' % nFid
        ret = self.dynamicCall(cmd)
        return ret

    def initOHLCRawData(self):
        self.ohlcv = {'date': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}


    def get_master_code_name(self, code):
        """
        종목코드의 한글명을 반환한다.

        :param code: string - 종목코드
        :return: string - 종목코드의 한글명
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not isinstance(code, str):
            raise ParameterTypeError()

        cmd = 'GetMasterCodeName("%s")' % code
        name = self.dynamicCall(cmd)
        return name

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


class ParameterTypeError(Exception):
    """ 파라미터 타입이 일치하지 않을 경우 발생하는 예외 """

    def __init__(self, msg="파라미터 타입이 일치하지 않습니다."):
        self.msg = msg

    def __str__(self):
        return self.msg


class ParameterValueError(Exception):
    """ 파라미터로 사용할 수 없는 값을 사용할 경우 발생하는 예외 """

    def __init__(self, msg="파라미터로 사용할 수 없는 값 입니다."):
        self.msg = msg

    def __str__(self):
        return self.msg


class KiwoomProcessingError(Exception):
    """ 키움에서 처리실패에 관련된 리턴코드를 받았을 경우 발생하는 예외 """

    def __init__(self, msg="처리 실패"):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return self.msg


class KiwoomConnectError(Exception):
    """ 키움서버에 로그인 상태가 아닐 경우 발생하는 예외 """

    def __init__(self, msg="로그인 여부를 확인하십시오"):
        self.msg = msg

    def __str__(self):
        return self.msg


class ReturnCode(object):
    """ 키움 OpenApi+ 함수들이 반환하는 값 """

    OP_ERR_NONE = 0 # 정상처리
    OP_ERR_FAIL = -10   # 실패
    OP_ERR_LOGIN = -100 # 사용자정보교환실패
    OP_ERR_CONNECT = -101   # 서버접속실패
    OP_ERR_VERSION = -102   # 버전처리실패
    OP_ERR_FIREWALL = -103  # 개인방화벽실패
    OP_ERR_MEMORY = -104    # 메모리보호실패
    OP_ERR_INPUT = -105 # 함수입력값오류
    OP_ERR_SOCKET_CLOSED = -106 # 통신연결종료
    OP_ERR_SISE_OVERFLOW = -200 # 시세조회과부하
    OP_ERR_RQ_STRUCT_FAIL = -201    # 전문작성초기화실패
    OP_ERR_RQ_STRING_FAIL = -202    # 전문작성입력값오류
    OP_ERR_NO_DATA = -203   # 데이터없음
    OP_ERR_OVER_MAX_DATA = -204 # 조회가능한종목수초과
    OP_ERR_DATA_RCV_FAIL = -205 # 데이터수신실패
    OP_ERR_OVER_MAX_FID = -206  # 조회가능한FID수초과
    OP_ERR_REAL_CANCEL = -207   # 실시간해제오류
    OP_ERR_ORD_WRONG_INPUT = -300   # 입력값오류
    OP_ERR_ORD_WRONG_ACCTNO = -301  # 계좌비밀번호없음
    OP_ERR_OTHER_ACC_USE = -302 # 타인계좌사용오류
    OP_ERR_MIS_2BILL_EXC = -303 # 주문가격이20억원을초과
    OP_ERR_MIS_5BILL_EXC = -304 # 주문가격이50억원을초과
    OP_ERR_MIS_1PER_EXC = -305  # 주문수량이총발행주수의1%초과오류
    OP_ERR_MIS_3PER_EXC = -306  # 주문수량이총발행주수의3%초과오류
    OP_ERR_SEND_FAIL = -307 # 주문전송실패
    OP_ERR_ORD_OVERFLOW = -308  # 주문전송과부하
    OP_ERR_MIS_300CNT_EXC = -309    # 주문수량300계약초과
    OP_ERR_MIS_500CNT_EXC = -310    # 주문수량500계약초과
    OP_ERR_ORD_WRONG_ACCTINFO = -340    # 계좌정보없음
    OP_ERR_ORD_SYMCODE_EMPTY = -500 # 종목코드없음

    CAUSE = {
        0: '정상처리',
        -10: '실패',
        -100: '사용자정보교환실패',
        -102: '버전처리실패',
        -103: '개인방화벽실패',
        -104: '메모리보호실패',
        -105: '함수입력값오류',
        -106: '통신연결종료',
        -200: '시세조회과부하',
        -201: '전문작성초기화실패',
        -202: '전문작성입력값오류',
        -203: '데이터없음',
        -204: '조회가능한종목수초과',
        -205: '데이터수신실패',
        -206: '조회가능한FID수초과',
        -207: '실시간해제오류',
        -300: '입력값오류',
        -301: '계좌비밀번호없음',
        -302: '타인계좌사용오류',
        -303: '주문가격이20억원을초과',
        -304: '주문가격이50억원을초과',
        -305: '주문수량이총발행주수의1%초과오류',
        -306: '주문수량이총발행주수의3%초과오류',
        -307: '주문전송실패',
        -308: '주문전송과부하',
        -309: '주문수량300계약초과',
        -310: '주문수량500계약초과',
        -340: '계좌정보없음',
        -500: '종목코드없음'
    }


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Test Code
    kiwoom = Kiwoom()
    kiwoom.comm_connect()


    # opw00018
    kiwoom.init_opw00018_data()

    kiwoom.set_input_value("계좌번호", "8086919011")
    kiwoom.set_input_value("비밀번호", "0000")
    kiwoom.comm_rq_data("계좌평가잔고내역요청", "opw00018", 0, "2000")

    while kiwoom.remained_data == '2':
        time.sleep(0.2)
        kiwoom.set_input_value("계좌번호", "8086919011")
        kiwoom.set_input_value("비밀번호", "0000")
        kiwoom.comm_rq_data("계좌평가잔고내역요청", "opw00018", 2, "2000")

    print(kiwoom.data_opw00018['single'])
    print(kiwoom.data_opw00018['multi'])
