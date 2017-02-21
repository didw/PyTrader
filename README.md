키움 Open API + 를 이용한 시스템트레이딩

## 개발환경
 - Anaconda3-4.3.0.1 32bit (Python 3.6, PyQt5.6, pywinauto, pandas)
 - Windows 7/10

## 환경설정
 - account.txt에 각 로그인정보 입력
 -- 사용자id
 -- 로그인 pw
 -- 공인인증서 pw
 - pytrader.py와 Kiwoom.py에 계좌번호와 비밀번호 설정.

## 사용법
 - 장 개시 전 pymon.py를 실행하여 매수할 종목을 선정. 매수할 종목은 buy_list.txt에 기록됨. (현재는 배당률 기반 투자전략 알고리즘을 사용)
 - 장 개시 전 update_version.py를 실행하여 kiwoom HTS version을 업데이트
 - 장 개시 후 pytrader.py를 실행하면 buy_list에 있는 종목을 매수.

## 참고사이트
 - [파이썬을 이용한 시스템 트레이딩(기초편)](https://wikidocs.net/book/110)