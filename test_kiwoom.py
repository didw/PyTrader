from pykiwoom.kiwoom import *
from pykiwoom.wrapper import *


if __name__ == '__main__':
    kiwoom = Kiwoom()
    kiwoom.comm_connect()
    wrapper = KiwoomWrapper(kiwoom)

    data = wrapper.get_data_opt10086("035420", "20170101")
    print(len(data))
