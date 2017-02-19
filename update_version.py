from pywinauto import application
from pywinauto import timings
import time
import os


# Account
account = []
with open("C:\\Users\\seoga\\PycharmProjects\\PyTrader\\account.txt", 'r') as f:
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

time.sleep(50)
os.system("taskkill /im khmini.exe")

