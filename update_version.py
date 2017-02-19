from pywinauto import application
from pywinauto import timings
import time
import os


# Account
account = []
with open("account.txt", 'r') as f:
    account = f.readlines()
app = application.Application()
app.start("C:/Kiwoom/KiwoomFlash2/khministarter.exe")

title = "번개 Login"
dlg = timings.WaitUntilPasses(20, 0.5, lambda: app.window_(title=title))

idForm = dlg.Edit0
idForm.SetFocus()
idForm.TypeKeys(account[0])

passForm = dlg.Edit2
passForm.SetFocus()
passForm.TypeKeys(account[1])

certForm = dlg.Edit3
certForm.SetFocus()
certForm.TypeKeys(account[2])

loginBtn = dlg.Button0
loginBtn.Click()

# 업데이트가 완료될 때 까지 대기
while True:
    time.sleep(5)
    with os.popen('tasklist /FI "IMAGENAME eq khmini.exe"') as f:
        lines = f.readlines()
        if len(lines) >= 3:
            break

# 번개2 종료
time.sleep(30)
os.system("taskkill /im khmini.exe")

