"""
Kiwoom 클래스는 OCX를 통해 API 함수를 호출할 수 있도록 구현되어 있습니다.
OCX 사용을 위해 QAxWidget 클래스를 상속받아서 구현하였으며,
주식(현물) 거래에 필요한 메서드들만 구현하였습니다.

author: Jongyeol Yang
last edit: 2017. 02. 23
"""
import sys
import logging
import logging.config
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop
from PyQt5.QtWidgets import QApplication
from pandas import DataFrame
import time
import numpy as np
from datetime import datetime

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
        self.data_opw00018 = {'account_evaluation': [], 'stocks': []}

        # 주가상세정보
        self.data_opt10081 = [] * 15
        self.data_opt10086 = [] * 23

        # signal & slot
        self.OnEventConnect.connect(self.event_connect)
        self.OnReceiveTrData.connect(self.on_receive_tr_data)
        self.OnReceiveChejanData.connect(self.on_receive_chejan_data)
        self.OnReceiveRealData.connect(self.receive_real_data)
        self.OnReceiveMsg.connect(self.receive_msg)
        self.OnReceiveConditionVer.connect(self.receive_condition_ver)
        self.OnReceiveTrCondition.connect(self.receive_tr_condition)
        self.OnReceiveRealCondition.connect(self.receive_real_condition)

        # 로깅용 설정파일
        logging.config.fileConfig('logging.conf')
        self.log = logging.getLogger('Kiwoom')

    ###############################################################
    # 로깅용 메서드 정의                                               #
    ###############################################################

    def logger(origin):
        def wrapper(*args, **kwargs):
            args[0].log.debug('{} args - {}, kwargs - {}'.format(origin.__name__, args, kwargs))
            return origin(*args, **kwargs)

        return wrapper

    ###############################################################
    # 이벤트 정의                                                    #
    ###############################################################

    def event_connect(self, return_code):
        """
        통신 연결 상태 변경시 이벤트

        return_code 0이면 로그인 성공
        그 외에는 ReturnCode 클래스 참조.

        :param return_code: int
        """
        try:
            if return_code == ReturnCode.OP_ERR_NONE:
                if self.get_login_info("GetServerGubun", True):
                    self.msg += "실서버 연결 성공" + "\r\n\r\n"
                else:
                    self.msg += "모의투자서버 연결 성공" + "\r\n\r\n"
            else:
                self.msg += "연결 끊김: 원인 - " + ReturnCode.CAUSE[return_code] + "\r\n\r\n"
        except Exception as error:
            self.log.error('eventConnect {}'.format(error))
        finally:
            # commConnect() 메서드에 의해 생성된 루프를 종료시킨다.
            # 로그인 후, 통신이 끊길 경우를 대비해서 예외처리함.
            try:
                self.login_loop.exit()
            except AttributeError:
                pass

    def receive_msg(self, screen_no, request_name, tr_code, msg):
        """
        수신 메시지 이벤트

        서버로 어떤 요청을 했을 때(로그인, 주문, 조회 등), 그 요청에 대한 처리내용을 전달해준다.

        :param screen_no: string - 화면번호(4자리, 사용자 정의, 서버에 조회나 주문을 요청할 때 이 요청을 구별하기 위한 키값)
        :param request_name: string - TR 요청명(사용자 정의)
        :param tr_code: string
        :param msg: string - 서버로 부터의 메시지
        """

        if request_name == "서버구분":

            if msg.find('모의투자') < 0:
                self.server_gubun = 1

            else:
                self.server_gubun = 0

            try:
                self.order_loop.exit()
            except AttributeError:
                pass
            finally:
                return

        self.msg += request_name + ": " + msg + "\r\n\r\n"

    def on_receive_tr_data(self, screen_no, request_name, tr_code, record_name, inquiry, unused0, unused1, unused2,
                           unused3):
        """
        TR 수신 이벤트

        조회요청 응답을 받거나 조회데이터를 수신했을 때 호출됩니다.
        request_name tr_code comm_rq_data()메소드의 매개변수와 매핑되는 값 입니다.
        조회데이터는 이 이벤트 메서드 내부에서 comm_get_data() 메서드를 이용해서 얻을 수 있습니다.

        :param screen_no: string - 화면번호(4자리)
        :param request_name: string - TR 요청명(comm_rq_data() 메소드 호출시 사용된 requestName)
        :param tr_code: string
        :param record_name: string
        :param inquiry: string - 조회('0': 남은 데이터 없음, '2': 남은 데이터 있음)
        """

        print("on_receive_tr_data 실행: screen_no: %s, request_name: %s, tr_code: %s, record_name: %s, inquiry: %s" % (
            screen_no, request_name, tr_code, record_name, inquiry))

        # 주문번호와 주문루프
        self.order_no = self.comm_get_data(tr_code, "", request_name, 0, "주문번호")

        try:
            self.order_loop.exit()
        except AttributeError:
            pass

        self.inquiry = inquiry

        if request_name == "관심종목정보요청":
            data = self.get_comm_data_ex(tr_code, "관심종목정보")

            """ commGetData
            cnt = self.getRepeatCnt(trCode, requestName)

            for i in range(cnt):
                data = self.commGetData(trCode, "", requestName, i, "종목명")
                print(data)
            """

        if request_name == "주식일봉차트조회요청":
            data = self.get_comm_data_ex(tr_code, "주식일봉차트조회")
            if data is not None:
                data = list(map(lambda x: list(map(lambda y: y.replace('+','').replace('--','-'), x)), np.array(data)[:,1:8].tolist()))
                data = list(map(lambda x: list(map(lambda y: int(y) if y != '' else 0, x)), data))
                self.data_opt10081.extend(data)
                date = str(data[0][3])
                dt = datetime.strptime(date, "%Y%m%d")
                if dt <= self.start_date:
                    self.inquiry = 0
            if inquiry == "0" or self.inquiry == 0:
                col_name = ['현재가', '거래량', '거래대금', '일자', '시가', '고가', '저가']
                self.data_opt10081 = DataFrame(self.data_opt10081, columns=col_name)

        if request_name == "일별주가요청":
            data = self.get_comm_data_ex(tr_code, "일별주가요청")
            if data is not None:
                data = list(map(lambda x: list(map(lambda y: y.replace('+','').replace('--','-'), x)), data))
                data = list(map(lambda x: list(map(lambda y: float(y) if y != '' else 0, x)), data))
                self.data_opt10086.extend(data)
                date = str(int(data[0][0]))
                dt = datetime.strptime(date, "%Y%m%d")
                if dt <= self.start_date:
                    self.inquiry = 0
            if inquiry == "0" or self.inquiry == 0:
                col_name = ['일자', '시가', '고가', '저가', '종가', '전일비', '등락률', '거래량', '금액(백만)', '신용비', '개인',
                            '기관', '외인수량', '외국계', '프로그램', '외인비', '체결강도', '외인보유', '외인비중', '외인순매수',
                            '기관순매수', '개인순매수', '신용잔고율']
                self.data_opt10086 = DataFrame(self.data_opt10086, columns=col_name)

        if request_name == "예수금상세현황요청":
            estimate_day2_deposit = self.comm_get_data(tr_code, "", request_name, 0, "d+2추정예수금")
            estimate_day2_deposit = self.change_format(estimate_day2_deposit)
            self.data_opw00001 = estimate_day2_deposit

        if request_name == '계좌평가잔고내역요청':
            # 계좌 평가 정보
            account_evaluation = []
            key_list = ["총매입금액", "총평가금액", "총평가손익금액", "총수익률(%)", "추정예탁자산"]

            for key in key_list:
                value = self.comm_get_data(tr_code, "", request_name, 0, key)

                if key.startswith("총수익률"):
                    value = self.change_format(value, 1)
                else:
                    value = self.change_format(value)
                account_evaluation.append(value)
            self.data_opw00018['account_evaluation'] = account_evaluation

            # 보유 종목 정보
            cnt = self.get_repeat_cnt(tr_code, request_name)
            key_list = ["종목명", "보유수량", "매입가", "현재가", "평가손익", "수익률(%)", "종목번호"]
            for i in range(cnt):
                stock = []
                for key in key_list:
                    value = self.comm_get_data(tr_code, "", request_name, i, key)
                    if key.startswith("수익률"):
                        value = self.change_format(value, 2)
                    elif key != "종목명" and key != "종목번호":
                        value = self.change_format(value)
                    stock.append(value)
                self.data_opw00018['stocks'].append(stock)
        try:
            self.request_loop.exit()
        except AttributeError:
            pass

    def receive_real_data(self, code, real_type, real_data):
        """
        실시간 데이터 수신 이벤트

        실시간 데이터를 수신할 때 마다 호출되며,
        set_real_reg() 메서드로 등록한 실시간 데이터도 이 이벤트 메서드에 전달됩니다.
        get_comm_real_data() 메서드를 이용해서 실시간 데이터를 얻을 수 있습니다.

        :param code: string - 종목코드
        :param real_type: string - 실시간 타입(KOA의 실시간 목록 참조)
        :param real_data: string - 실시간 데이터 전문
        """

        try:
            self.log.debug("[receiveRealData]")
            self.log.debug("({})".format(real_type))

            if real_type not in RealType.REALTYPE:
                return

            data = []

            if code != "":
                data.append(code)
                codeOrNot = code
            else:
                codeOrNot = real_type

            for fid in sorted(RealType.REALTYPE[real_type].keys()):
                value = self.get_comm_real_data(codeOrNot, fid)
                data.append(value)

            # TODO: DB에 저장
            self.log.debug(data)

        except Exception as e:
            self.log.error('{}'.format(e))

    def on_receive_chejan_data(self, gubun, item_cnt, fid_list):
        print("gubun: ", gubun)
        print(self.GetChejanData(9203))
        print(self.GetChejanData(302))
        print(self.GetChejanData(900))
        print(self.GetChejanData(901))

    def get_codelist_by_market(self, market):
        func = 'GetCodeListByMarket("%s")' % market
        codes = self.dynamicCall(func)
        return codes.split(';')

    ###############################################################
    # 메서드 정의: 로그인 관련 메서드                                    #
    ###############################################################

    def comm_connect(self):
        """
        로그인을 시도합니다.

        수동 로그인일 경우, 로그인창을 출력해서 로그인을 시도.
        자동 로그인일 경우, 로그인창 출력없이 로그인 시도.
        """
        self.dynamicCall("CommConnect()")
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def get_connect_state(self):
        """
        현재 접속상태를 반환합니다.

        반환되는 접속상태는 아래와 같습니다.
        0: 미연결, 1: 연결

        :return: int
        """
        ret = self.dynamicCall("GetConnectState()")
        return ret

    def get_login_info(self, tag, is_connect_state=False):
        """
        사용자의 tag에 해당하는 정보를 반환한다.

        tag에 올 수 있는 값은 아래와 같다.
        ACCOUNT_CNT: 전체 계좌의 개수를 반환한다.
        ACCNO: 전체 계좌 목록을 반환한다. 계좌별 구분은 ;(세미콜론) 이다.
        USER_ID: 사용자 ID를 반환한다.
        USER_NAME: 사용자명을 반환한다.
        GetServerGubun: 접속서버 구분을 반환합니다.(0: 모의투자, 그외: 실서버)

        :param tag: string
        :param is_connect_state: bool - 접속상태을 확인할 필요가 없는 경우 True로 설정.
        :return: string
        """
        if not is_connect_state:
            if not self.get_connect_state():
                raise KiwoomConnectError()

        if not isinstance(tag, str):
            raise ParameterTypeError()

        if tag not in ['ACCOUNT_CNT', 'ACCNO', 'USER_ID', 'USER_NAME', 'GetServerGubun']:
            raise ParameterValueError()

        cmd = 'GetLoginInfo("%s")' % tag
        info = self.dynamicCall(cmd)

        if tag == 'GetServerGubun' and info == "":
            if self.server_gubun == None:
                account_list = self.get_login_info("ACCNO").split(';')
                self.send_order("서버구분", "0102", account_list[0], 1, "066570", 0, 0, "05", "")
            info = self.server_gubun
        return info

    #################################################################
    # 메서드 정의: 조회 관련 메서드                                        #
    # 시세조회, 관심종목 조회, 조건검색 등 이들의 합산 조회 횟수가 1초에 5회까지 허용 #
    #################################################################

    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value)

    def comm_rq_data(self, request_name, tr_code, inquiry, screen_no):
        """
        키움서버에 TR 요청을 한다.

        조회요청메서드이며 빈번하게 조회요청시, 시세과부하 에러값 -200이 리턴된다.

        :param request_name: string - TR 요청명(사용자 정의)
        :param tr_code: string
        :param inquiry: int - 조회(0: 조회, 2: 남은 데이터 이어서 요청)
        :param screen_no: string - 화면번호(4자리)
        """

        if not self.get_connect_state():
            raise KiwoomConnectError()

        if not (isinstance(request_name, str)
                and isinstance(tr_code, str)
                and isinstance(inquiry, int)
                and isinstance(screen_no, str)):
            raise ParameterTypeError()

        return_code = self.dynamicCall("CommRqData(QString, QString, int, QString)", request_name, tr_code, inquiry,
                                       screen_no)

        if return_code != ReturnCode.OP_ERR_NONE:
            raise KiwoomProcessingError("comm_rq_data(): " + ReturnCode.CAUSE[return_code])

        # 루프 생성: receive_tr_data() 메서드에서 루프를 종료시킨다.
        self.request_loop = QEventLoop()
        self.request_loop.exec_()

    def comm_get_data(self, code, real_type, field_name, index, item_name):
        """
        데이터 획득 메서드

        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 조회데이터를 얻어오는 메서드입니다.

        :param code: string
        :param real_type: string - TR 요청시 ""(빈문자)로 처리
        :param field_name: string - TR 요청명(comm_rq_data() 메소드 호출시 사용된 field_name)
        :param index: int
        :param item_name: string - 수신 데이터에서 얻고자 하는 값의 키(출력항목이름)
        :return: string
        """
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code, real_type,
                               field_name, index, item_name)
        return ret.strip()

    def get_repeat_cnt(self, tr_code, request_name):
        """
        서버로 부터 전달받은 데이터의 갯수를 리턴합니다.(멀티데이터의 갯수)

        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.

        키움 OpenApi+에서는 데이터를 싱글데이터와 멀티데이터로 구분합니다.
        싱글데이터란, 서버로 부터 전달받은 데이터 내에서, 중복되는 키(항목이름)가 하나도 없을 경우.
        예를들면, 데이터가 '종목코드', '종목명', '상장일', '상장주식수' 처럼 키(항목이름)가 중복되지 않는 경우를 말합니다.
        반면 멀티데이터란, 서버로 부터 전달받은 데이터 내에서, 일정 간격으로 키(항목이름)가 반복될 경우를 말합니다.
        예를들면, 10일간의 일봉데이터를 요청할 경우 '종목코드', '일자', '시가', '고가', '저가' 이러한 항목이 10번 반복되는 경우입니다.
        이러한 멀티데이터의 경우 반복 횟수(=데이터의 갯수)만큼, 루프를 돌면서 처리하기 위해 이 메서드를 이용하여 멀티데이터의 갯수를 얻을 수 있습니다.

        :param tr_code: string
        :param request_name: string - TR 요청명(comm_rq_data() 메소드 호출시 사용된 request_name)
        :return: int
        """
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", tr_code, request_name)
        return ret

    def get_comm_data_ex(self, tr_code, multi_data_name):
        """
        멀티데이터 획득 메서드

        receiveTrData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.

        :param tr_code: string
        :param multi_data_name: string - KOA에 명시된 멀티데이터명
        :return: list - 중첩리스트
        """

        if not (isinstance(tr_code, str)
                and isinstance(multi_data_name, str)):
            raise ParameterTypeError()

        data = self.dynamicCall("GetCommDataEx(QString, QString)", tr_code, multi_data_name)
        return data

    def commKwRqData(self, codes, inquiry, codeCount, requestName, screenNo, typeFlag=0):
        """
        복수종목조회 메서드(관심종목조회 메서드라고도 함).

        이 메서드는 setInputValue() 메서드를 이용하여, 사전에 필요한 값을 지정하지 않는다.
        단지, 메서드의 매개변수에서 직접 종목코드를 지정하여 호출하며,
        데이터 수신은 receiveTrData() 이벤트에서 아래 명시한 항목들을 1회 수신하며,
        이후 receiveRealData() 이벤트를 통해 실시간 데이터를 얻을 수 있다.

        복수종목조회 TR 코드는 OPTKWFID 이며, 요청 성공시 아래 항목들의 정보를 얻을 수 있다.

        종목코드, 종목명, 현재가, 기준가, 전일대비, 전일대비기호, 등락율, 거래량, 거래대금,
        체결량, 체결강도, 전일거래량대비, 매도호가, 매수호가, 매도1~5차호가, 매수1~5차호가,
        상한가, 하한가, 시가, 고가, 저가, 종가, 체결시간, 예상체결가, 예상체결량, 자본금,
        액면가, 시가총액, 주식수, 호가시간, 일자, 우선매도잔량, 우선매수잔량,우선매도건수,
        우선매수건수, 총매도잔량, 총매수잔량, 총매도건수, 총매수건수, 패리티, 기어링, 손익분기,
        잔본지지, ELW행사가, 전환비율, ELW만기일, 미결제약정, 미결제전일대비, 이론가,
        내재변동성, 델타, 감마, 쎄타, 베가, 로

        :param codes: string - 한번에 100종목까지 조회가능하며 종목코드사이에 세미콜론(;)으로 구분.
        :param inquiry: int - api 문서는 bool 타입이지만, int로 처리(0: 조회, 1: 남은 데이터 이어서 조회)
        :param codeCount: int - codes에 지정한 종목의 갯수.
        :param requestName: string
        :param screenNo: string
        :param typeFlag: int - 주식과 선물옵션 구분(0: 주식, 3: 선물옵션), 주의: 매개변수의 위치를 맨 뒤로 이동함.
        :return: list - 중첩 리스트 [[종목코드, 종목명 ... 종목 정보], [종목코드, 종목명 ... 종목 정보]]
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not (isinstance(codes, str)
                and isinstance(inquiry, int)
                and isinstance(codeCount, int)
                and isinstance(requestName, str)
                and isinstance(screenNo, str)
                and isinstance(typeFlag, int)):
            raise ParameterTypeError()

        returnCode = self.dynamicCall("CommKwRqData(QString, QBoolean, int, int, QString, QString)",
                                      codes, inquiry, codeCount, typeFlag, requestName, screenNo)

        if returnCode != ReturnCode.OP_ERR_NONE:
            raise KiwoomProcessingError("commKwRqData(): " + ReturnCode.CAUSE[returnCode])

        # 루프 생성: receiveTrData() 메서드에서 루프를 종료시킨다.
        self.requestLoop = QEventLoop()
        self.requestLoop.exec_()

    ###############################################################
    # 메서드 정의: 실시간 데이터 처리 관련 메서드                           #
    ###############################################################

    def disconnect_real_data(self, screen_no):
        """
        해당 화면번호로 설정한 모든 실시간 데이터 요청을 제거합니다.

        화면을 종료할 때 반드시 이 메서드를 호출해야 합니다.

        :param screen_no: string
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not isinstance(screen_no, str):
            raise ParameterTypeError()

        self.dynamicCall("DisconnectRealData(QString)", screen_no)

    def get_comm_real_data(self, code, fid):
        """
        실시간 데이터 획득 메서드

        이 메서드는 반드시 receiveRealData() 이벤트 메서드가 호출될 때, 그 안에서 사용해야 합니다.

        :param code: string - 종목코드
        :param fid: - 실시간 타입에 포함된 fid
        :return: string - fid에 해당하는 데이터
        """

        if not (isinstance(code, str)
                and isinstance(fid, int)):
            raise ParameterTypeError()

        value = self.dynamicCall("GetCommRealData(QString, int)", code, fid)

        return value

    def set_real_reg(self, screen_no, codes, fids, real_reg_type):
        """
        실시간 데이터 요청 메서드

        종목코드와 fid 리스트를 이용해서 실시간 데이터를 요청하는 메서드입니다.
        한번에 등록 가능한 종목과 fid 갯수는 100종목, 100개의 fid 입니다.
        실시간등록타입을 0으로 설정하면, 첫 실시간 데이터 요청을 의미하며
        실시간등록타입을 1로 설정하면, 추가등록을 의미합니다.

        실시간 데이터는 실시간 타입 단위로 receiveRealData() 이벤트로 전달되기 때문에,
        이 메서드에서 지정하지 않은 fid 일지라도, 실시간 타입에 포함되어 있다면, 데이터 수신이 가능하다.

        :param screen_no: string
        :param codes: string - 종목코드 리스트(종목코드;종목코드;...)
        :param fids: string - fid 리스트(fid;fid;...)
        :param real_reg_type: string - 실시간등록타입(0: 첫 등록, 1: 추가 등록)
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not (isinstance(screen_no, str)
                and isinstance(codes, str)
                and isinstance(fids, str)
                and isinstance(real_reg_type, str)):
            raise ParameterTypeError()

        self.dynamicCall("SetRealReg(QString, QString, QString, QString)",
                         screen_no, codes, fids, real_reg_type)

    def set_real_remove(self, screen_no, code):
        """
        실시간 데이터 중지 메서드

        set_real_reg() 메서드로 등록한 종목만, 이 메서드를 통해 실시간 데이터 받기를 중지 시킬 수 있습니다.

        :param screen_no: string - 화면번호 또는 ALL 키워드 사용가능
        :param code: string - 종목코드 또는 ALL 키워드 사용가능
        """

        if not self.getConnectState():
            raise KiwoomConnectError()

        if not (isinstance(screen_no, str)
                and isinstance(code, str)):
            raise ParameterTypeError()

        self.dynamicCall("SetRealRemove(QString, QString)", screen_no, code)

    ###############################################################
    # 메서드 정의: 조건검색 관련 메서드와 이벤트                            #
    ###############################################################

    def receive_condition_ver(self, receive, msg):
        """
        getConditionLoad() 메서드의 조건식 목록 요청에 대한 응답 이벤트

        :param receive: int - 응답결과(1: 성공, 나머지 실패)
        :param msg: string - 메세지
        """

        try:
            if not receive:
                return

            self.condition = self.get_condition_name_list()
            print("조건식 개수: ", len(self.condition))

            for key in self.condition.keys():
                print("조건식: ", key, ": ", self.condition[key])
                print("key type: ", type(key))

        except Exception as e:
            print(e)

        finally:
            self.condition_loop.exit()

    def receive_tr_condition(self, screen_no, codes, condition_name, condition_index, inquiry):
        """
        (1회성, 실시간) 종목 조건검색 요청시 발생되는 이벤트

        :param screen_no: string
        :param codes: string - 종목코드 목록(각 종목은 세미콜론으로 구분됨)
        :param condition_name: string - 조건식 이름
        :param condition_index: int - 조건식 인덱스
        :param inquiry: int - 조회구분(0: 남은데이터 없음, 2: 남은데이터 있음)
        """

        print("[receive_tr_condition]")

        try:
            if codes == "":
                return

            code_list = codes.split(';')
            del code_list[-1]

            print(code_list)
            print("종목개수: ", len(code_list))

        finally:
            self.condition_loop.exit()

    def receive_real_condition(self, code, event, condition_name, condition_index):
        """
        실시간 종목 조건검색 요청시 발생되는 이벤트

        :param code: string - 종목코드
        :param event: string - 이벤트종류("I": 종목편입, "D": 종목이탈)
        :param condition_name: string - 조건식 이름
        :param condition_index: string - 조건식 인덱스(여기서만 인덱스가 string 타입으로 전달됨)
        """

        print("[receive_real_condition]")

        print("종목코드: ", code)
        print("이벤트: ", "종목편입" if event == "I" else "종목이탈")

    def get_condition_load(self):
        """ 조건식 목록 요청 메서드 """

        if not self.get_connect_state():
            raise KiwoomConnectError()

        is_load = self.dynamicCall("GetConditionLoad()")

        # 요청 실패시
        if not is_load:
            raise KiwoomProcessingError("getConditionLoad(): 조건식 요청 실패")

        # receiveConditionVer() 이벤트 메서드에서 루프 종료
        self.condition_loop = QEventLoop()
        self.condition_loop.exec_()

    def get_condition_name_list(self):
        """
        조건식 획득 메서드

        조건식을 딕셔너리 형태로 반환합니다.
        이 메서드는 반드시 receiveConditionVer() 이벤트 메서드안에서 사용해야 합니다.

        :return: dict - {인덱스:조건명, 인덱스:조건명, ...}
        """

        data = self.dynamicCall("get_condition_name_list()")

        if data == "":
            raise KiwoomProcessingError("get_condition_name_list(): 사용자 조건식이 없습니다.")

        conditionList = data.split(';')
        del conditionList[-1]

        condition_dictionary = {}

        for condition in conditionList:
            key, value = condition.split('^')
            condition_dictionary[int(key)] = value

        return condition_dictionary

    def send_condition(self, screen_no, condition_name, condition_index, is_real_time):
        """
        종목 조건검색 요청 메서드

        이 메서드로 얻고자 하는 것은 해당 조건에 맞는 종목코드이다.
        해당 종목에 대한 상세정보는 set_real_reg() 메서드로 요청할 수 있다.
        요청이 실패하는 경우는, 해당 조건식이 없거나, 조건명과 인덱스가 맞지 않거나, 조회 횟수를 초과하는 경우 발생한다.

        조건검색에 대한 결과는
        1회성 조회의 경우, receiveTrCondition() 이벤트로 결과값이 전달되며
        실시간 조회의 경우, receiveTrCondition()과 receiveRealCondition() 이벤트로 결과값이 전달된다.

        :param screen_no: string
        :param condition_name: string - 조건식 이름
        :param condition_index: int - 조건식 인덱스
        :param is_real_time: int - 조건검색 조회구분(0: 1회성 조회, 1: 실시간 조회)
        """

        if not self.get_connect_state():
            raise KiwoomConnectError()

        if not (isinstance(screen_no, str)
                and isinstance(condition_name, str)
                and isinstance(condition_index, int)
                and isinstance(is_real_time, int)):
            raise ParameterTypeError()

        is_request = self.dynamicCall("SendCondition(QString, QString, int, int",
                                      screen_no, condition_name, condition_index, is_real_time)

        if not is_request:
            raise KiwoomProcessingError("sendCondition(): 조건검색 요청 실패")

        # receiveTrCondition() 이벤트 메서드에서 루프 종료
        self.condition_loop = QEventLoop()
        self.condition_loop.exec_()

    def send_condition_stop(self, screen_no, condition_name, condition_index):
        """ 종목 조건검색 중지 메서드 """

        if not self.get_connect_state():
            raise KiwoomConnectError()

        if not (isinstance(screen_no, str)
                and isinstance(condition_name, str)
                and isinstance(condition_index, int)):
            raise ParameterTypeError()

        self.dynamicCall("SendConditionStop(QString, QString, int)", screen_no, condition_name, condition_index)

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
        if not self.get_connect_state():
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

        return_code = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                       [request_name, screen_no, account_no, order_type, code, qty, price, hoga_type,
                                        origin_order_no])

        if return_code != ReturnCode.OP_ERR_NONE:
            raise KiwoomProcessingError("send_order(): " + ReturnCode.CAUSE[return_code])

        # receiveTrData() 에서 루프종료
        self.order_loop = QEventLoop()
        self.order_loop.exec_()

    def GetChejanData(self, nFid):
        cmd = 'GetChejanData("%s")' % nFid
        ret = self.dynamicCall(cmd)
        return ret

    ###############################################################
    # 기타 메서드 정의                                                #
    ###############################################################

    def get_code_list(self, *market):
        """
        여러 시장의 종목코드를 List 형태로 반환하는 헬퍼 메서드.

        :param market: Tuple - 여러 개의 문자열을 매개변수로 받아 Tuple로 처리한다.
        :return: List
        """
        code_list = []
        for m in market:
            tmp_list = self.get_codelist_by_market(m)
            code_list += tmp_list
        return code_list

    def get_master_code_name(self, code):
        """
        종목코드의 한글명을 반환한다.

        :param code: string - 종목코드
        :return: string - 종목코드의 한글명
        """

        if not self.get_connect_state():
            raise KiwoomConnectError()

        if not isinstance(code, str):
            raise ParameterTypeError()

        cmd = 'GetMasterCodeName("%s")' % code
        name = self.dynamicCall(cmd)
        return name

    def change_format(self, data, percent=0):
        if percent == 0:
            d = int(data)
            format_data = '{:-,d}'.format(d)
        elif percent == 1:
            f = float(data)
            f -= 100
            format_data = '{:-,.2f}'.format(f)
        elif percent == 2:
            f = float(data)
            format_data = '{:-,.2f}'.format(f)
        return format_data

    def opw_data_reset(self):
        """ 잔고 및 보유종목 데이터 초기화 """
        self.data_opw00001 = 0
        self.data_opw00018 = {'account_evaluation': [], 'stocks': []}


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

    OP_ERR_NONE = 0  # 정상처리
    OP_ERR_FAIL = -10  # 실패
    OP_ERR_LOGIN = -100  # 사용자정보교환실패
    OP_ERR_CONNECT = -101  # 서버접속실패
    OP_ERR_VERSION = -102  # 버전처리실패
    OP_ERR_FIREWALL = -103  # 개인방화벽실패
    OP_ERR_MEMORY = -104  # 메모리보호실패
    OP_ERR_INPUT = -105  # 함수입력값오류
    OP_ERR_SOCKET_CLOSED = -106  # 통신연결종료
    OP_ERR_SISE_OVERFLOW = -200  # 시세조회과부하
    OP_ERR_RQ_STRUCT_FAIL = -201  # 전문작성초기화실패
    OP_ERR_RQ_STRING_FAIL = -202  # 전문작성입력값오류
    OP_ERR_NO_DATA = -203  # 데이터없음
    OP_ERR_OVER_MAX_DATA = -204  # 조회가능한종목수초과
    OP_ERR_DATA_RCV_FAIL = -205  # 데이터수신실패
    OP_ERR_OVER_MAX_FID = -206  # 조회가능한FID수초과
    OP_ERR_REAL_CANCEL = -207  # 실시간해제오류
    OP_ERR_ORD_WRONG_INPUT = -300  # 입력값오류
    OP_ERR_ORD_WRONG_ACCTNO = -301  # 계좌비밀번호없음
    OP_ERR_OTHER_ACC_USE = -302  # 타인계좌사용오류
    OP_ERR_MIS_2BILL_EXC = -303  # 주문가격이20억원을초과
    OP_ERR_MIS_5BILL_EXC = -304  # 주문가격이50억원을초과
    OP_ERR_MIS_1PER_EXC = -305  # 주문수량이총발행주수의1%초과오류
    OP_ERR_MIS_3PER_EXC = -306  # 주문수량이총발행주수의3%초과오류
    OP_ERR_SEND_FAIL = -307  # 주문전송실패
    OP_ERR_ORD_OVERFLOW = -308  # 주문전송과부하
    OP_ERR_MIS_300CNT_EXC = -309  # 주문수량300계약초과
    OP_ERR_MIS_500CNT_EXC = -310  # 주문수량500계약초과
    OP_ERR_ORD_WRONG_ACCTINFO = -340  # 계좌정보없음
    OP_ERR_ORD_SYMCODE_EMPTY = -500  # 종목코드없음

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


class FidList(object):
    """ receiveChejanData() 이벤트 메서드로 전달되는 FID 목록 """

    CHEJAN = {
        9201: '계좌번호',
        9203: '주문번호',
        9205: '관리자사번',
        9001: '종목코드',
        912: '주문업무분류',
        913: '주문상태',
        302: '종목명',
        900: '주문수량',
        901: '주문가격',
        902: '미체결수량',
        903: '체결누계금액',
        904: '원주문번호',
        905: '주문구분',
        906: '매매구분',
        907: '매도수구분',
        908: '주문/체결시간',
        909: '체결번호',
        910: '체결가',
        911: '체결량',
        10: '현재가',
        27: '(최우선)매도호가',
        28: '(최우선)매수호가',
        914: '단위체결가',
        915: '단위체결량',
        938: '당일매매수수료',
        939: '당일매매세금',
        919: '거부사유',
        920: '화면번호',
        921: '921',
        922: '922',
        923: '923',
        949: '949',
        10010: '10010',
        917: '신용구분',
        916: '대출일',
        930: '보유수량',
        931: '매입단가',
        932: '총매입가',
        933: '주문가능수량',
        945: '당일순매수수량',
        946: '매도/매수구분',
        950: '당일총매도손일',
        951: '예수금',
        307: '기준가',
        8019: '손익율',
        957: '신용금액',
        958: '신용이자',
        959: '담보대출수량',
        924: '924',
        918: '만기일',
        990: '당일실현손익(유가)',
        991: '당일신현손익률(유가)',
        992: '당일실현손익(신용)',
        993: '당일실현손익률(신용)',
        397: '파생상품거래단위',
        305: '상한가',
        306: '하한가'
    }


class RealType(object):
    REALTYPE = {
        '주식시세': {
            10: '현재가',
            11: '전일대비',
            12: '등락율',
            27: '최우선매도호가',
            28: '최우선매수호가',
            13: '누적거래량',
            14: '누적거래대금',
            16: '시가',
            17: '고가',
            18: '저가',
            25: '전일대비기호',
            26: '전일거래량대비',
            29: '거래대금증감',
            30: '거일거래량대비',
            31: '거래회전율',
            32: '거래비용',
            311: '시가총액(억)'
        },

        '주식체결': {
            20: '체결시간(HHMMSS)',
            10: '체결가',
            11: '전일대비',
            12: '등락율',
            27: '최우선매도호가',
            28: '최우선매수호가',
            15: '체결량',
            13: '누적체결량',
            14: '누적거래대금',
            16: '시가',
            17: '고가',
            18: '저가',
            25: '전일대비기호',
            26: '전일거래량대비',
            29: '거래대금증감',
            30: '전일거래량대비',
            31: '거래회전율',
            32: '거래비용',
            228: '체결강도',
            311: '시가총액(억)',
            290: '장구분',
            691: 'KO접근도'
        },

        '주식호가잔량': {
            21: '호가시간',
            41: '매도호가1',
            61: '매도호가수량1',
            81: '매도호가직전대비1',
            51: '매수호가1',
            71: '매수호가수량1',
            91: '매수호가직전대비1',
            42: '매도호가2',
            62: '매도호가수량2',
            82: '매도호가직전대비2',
            52: '매수호가2',
            72: '매수호가수량2',
            92: '매수호가직전대비2',
            43: '매도호가3',
            63: '매도호가수량3',
            83: '매도호가직전대비3',
            53: '매수호가3',
            73: '매수호가수량3',
            93: '매수호가직전대비3',
            44: '매도호가4',
            64: '매도호가수량4',
            84: '매도호가직전대비4',
            54: '매수호가4',
            74: '매수호가수량4',
            94: '매수호가직전대비4',
            45: '매도호가5',
            65: '매도호가수량5',
            85: '매도호가직전대비5',
            55: '매수호가5',
            75: '매수호가수량5',
            95: '매수호가직전대비5',
            46: '매도호가6',
            66: '매도호가수량6',
            86: '매도호가직전대비6',
            56: '매수호가6',
            76: '매수호가수량6',
            96: '매수호가직전대비6',
            47: '매도호가7',
            67: '매도호가수량7',
            87: '매도호가직전대비7',
            57: '매수호가7',
            77: '매수호가수량7',
            97: '매수호가직전대비7',
            48: '매도호가8',
            68: '매도호가수량8',
            88: '매도호가직전대비8',
            58: '매수호가8',
            78: '매수호가수량8',
            98: '매수호가직전대비8',
            49: '매도호가9',
            69: '매도호가수량9',
            89: '매도호가직전대비9',
            59: '매수호가9',
            79: '매수호가수량9',
            99: '매수호가직전대비9',
            50: '매도호가10',
            70: '매도호가수량10',
            90: '매도호가직전대비10',
            60: '매수호가10',
            80: '매수호가수량10',
            100: '매수호가직전대비10',
            121: '매도호가총잔량',
            122: '매도호가총잔량직전대비',
            125: '매수호가총잔량',
            126: '매수호가총잔량직전대비',
            23: '예상체결가',
            24: '예상체결수량',
            128: '순매수잔량(총매수잔량-총매도잔량)',
            129: '매수비율',
            138: '순매도잔량(총매도잔량-총매수잔량)',
            139: '매도비율',
            200: '예상체결가전일종가대비',
            201: '예상체결가전일종가대비등락율',
            238: '예상체결가전일종가대비기호',
            291: '예상체결가',
            292: '예상체결량',
            293: '예상체결가전일대비기호',
            294: '예상체결가전일대비',
            295: '예상체결가전일대비등락율',
            13: '누적거래량',
            299: '전일거래량대비예상체결률',
            215: '장운영구분'
        },

        '장시작시간': {
            215: '장운영구분(0:장시작전, 2:장종료전, 3:장시작, 4,8:장종료, 9:장마감)',
            20: '시간(HHMMSS)',
            214: '장시작예상잔여시간'
        },

        '업종지수': {
            20: '체결시간',
            10: '현재가',
            11: '전일대비',
            12: '등락율',
            15: '거래량',
            13: '누적거래량',
            14: '누적거래대금',
            16: '시가',
            17: '고가',
            18: '저가',
            25: '전일대비기호',
            26: '전일거래량대비(계약,주)'
        },

        '업종등락': {
            20: '체결시간',
            252: '상승종목수',
            251: '상한종목수',
            253: '보합종목수',
            255: '하락종목수',
            254: '하한종목수',
            13: '누적거래량',
            14: '누적거래대금',
            10: '현재가',
            11: '전일대비',
            12: '등락율',
            256: '거래형성종목수',
            257: '거래형성비율',
            25: '전일대비기호'
        },

        '주문체결': {
            9201: '계좌번호',
            9203: '주문번호',
            9205: '관리자사번',
            9001: '종목코드',
            912: '주문분류(jj:주식주문)',
            913: '주문상태(10:원주문, 11:정정주문, 12:취소주문, 20:주문확인, 21:정정확인, 22:취소확인, 90,92:주문거부)',
            302: '종목명',
            900: '주문수량',
            901: '주문가격',
            902: '미체결수량',
            903: '체결누계금액',
            904: '원주문번호',
            905: '주문구분(+:현금매수, -:현금매도)',
            906: '매매구분(보통, 시장가등)',
            907: '매도수구분(1:매도, 2:매수)',
            908: '체결시간(HHMMSS)',
            909: '체결번호',
            910: '체결가',
            911: '체결량',
            10: '체결가',
            27: '최우선매도호가',
            28: '최우선매수호가',
            914: '단위체결가',
            915: '단위체결량',
            938: '당일매매수수료',
            939: '당일매매세금'
        },

        '잔고': {
            9201: '계좌번호',
            9001: '종목코드',
            302: '종목명',
            10: '현재가',
            930: '보유수량',
            931: '매입단가',
            932: '총매입가',
            933: '주문가능수량',
            945: '당일순매수량',
            946: '매도매수구분',
            950: '당일총매도손익',
            951: '예수금',
            27: '최우선매도호가',
            28: '최우선매수호가',
            307: '기준가',
            8019: '손익율'
        },

        '주식시간외호가': {
            21: '호가시간(HHMMSS)',
            131: '시간외매도호가총잔량',
            132: '시간외매도호가총잔량직전대비',
            135: '시간외매수호가총잔량',
            136: '시간외매수호가총잔량직전대비'
        }
    }


def test_to_get_account():
    kiwoom.set_input_value("계좌번호", "8086919011")
    kiwoom.set_input_value("비밀번호", "0000")
    kiwoom.comm_rq_data("계좌평가잔고내역요청", "opw00018", 2, "2000")
    while kiwoom.inquiry == '2':
        time.sleep(0.2)
        kiwoom.set_input_value("계좌번호", "8086919011")
        kiwoom.set_input_value("비밀번호", "0000")
        kiwoom.comm_rq_data("계좌평가잔고내역요청", "opw00018", 2, "2")

    print(kiwoom.data_opw00018['account_evaluation'])
    print(kiwoom.data_opw00018['stocks'])


def test_to_get_opt10081():
    kiwoom.set_input_value("종목코드", "035420")
    kiwoom.set_input_value("기준일자", "20170101")
    kiwoom.set_input_value("수정주가구분", 1)
    kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 0, "0101")
    while kiwoom.inquiry == '2':
        time.sleep(0.2)
        kiwoom.set_input_value("종목코드", "035420")
        kiwoom.set_input_value("기준일자", "20170101")
        kiwoom.set_input_value("수정주가구분", 1)
        kiwoom.comm_rq_data("주식일봉차트조회요청", "opt10081", 2, "0101")


def test_to_get_opt10086():
    kiwoom.set_input_value("종목코드", "035420")
    kiwoom.set_input_value("조회일자", "20170101")
    kiwoom.set_input_value("표시구분", 1)
    kiwoom.comm_rq_data("일별주가요청", "opt10086", 0, "0101")
    while kiwoom.inquiry == '2':
        time.sleep(0.2)
        kiwoom.set_input_value("종목코드", "035420")
        kiwoom.set_input_value("조회일자", "20170101")
        kiwoom.set_input_value("표시구분", 1)
        kiwoom.comm_rq_data("일별주가요청", "opt10086", 2, "0101")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Test Code
    kiwoom = Kiwoom()
    kiwoom.comm_connect()

    data = kiwoom.get_data_opt10086("035420", "20170101")
    print(len(data))
