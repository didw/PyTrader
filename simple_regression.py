import pandas as pd
import numpy as np
import sqlite3
from sklearn.ensemble.forest import RandomForestRegressor
from sklearn.externals import joblib
import os

class SimpleModel:
    def __init__(self):
        self.data = dict()
        self.frame_len = 30
        self.predict_dist = 5

    def load_all_data(self, begin_date, end_date):
        con = sqlite3.connect('stock.db')
        code_list = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        first = True
        for code in code_list:
            data = self.load_data(code[0], begin_date, end_date)
            data = data.dropna()
            X, Y = self.make_x_y(data)
            if first:
                X_data = list(X)
                Y_data = list(Y)
                DATA = data.values.tolist()
                first = False
                print(np.shape(X_data), np.shape(Y_data))
            else:
                X_data.extend(X)
                Y_data.extend(Y)
                DATA.extend(data.values.tolist())
                print(np.shape(X_data), np.shape(Y_data))
        return np.array(X_data), np.array(Y_data), np.array(DATA)

    def load_data(self, code, begin_date, end_date):
        con = sqlite3.connect('stock.db')
        df = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자').sort_index()
        data = df.loc[df.index > str(begin_date)]
        data = data.loc[data.index < str(end_date)]
        data = data.reset_index()
        return data

    def make_x_y(self, data):
        data_x = []
        data_y = []
        for col in data.columns:
            try:
                data.loc[:, col] = data.loc[:, col].str.replace('--', '-')
                data.loc[:, col] = data.loc[:, col].str.replace('+', '')
            except AttributeError as e:
                pass
                print(e)
        data.loc[:, 'month'] = data.loc[:, '일자'].str[4:6]
        data = data.drop(['일자', '체결강도'], axis=1)
        for i in range(self.frame_len, len(data)-self.predict_dist):
            """
            for c in data.columns:
                try:
                    test = float(data.loc[i,c])
                except:
                    print("can not convert %s" % data.loc[i,c])
            """
            #print("make data from %s to %s, %s" % (data['일자'][i-frame_len], data['일자'][i-1], data['일자'][i-frame_len-predict_dist]))
            #print(np.array(data.iloc[i-frame_len:i, :]))
            data_x.extend(np.array(data.iloc[i-self.frame_len:i, :]))
            data_y.extend(data.loc[i+self.predict_dist, ['현재가']])
        np_x = np.array(data_x).reshape(-1, 23*30)
        np_y = np.array(data_y)
        return np_x, np_y

    def train_model(self, X_train, Y_train):
        print("training model %d_%d.pkl" % (self.frame_len, self.predict_dist))
        model_name = "simple_reg_model/%d_%d.pkl" % (self.frame_len, self.predict_dist)
        self.estimator = RandomForestRegressor(random_state=0, n_estimators=100, n_jobs=-1)
        self.estimator.fit(X_train, Y_train)
        print("finish training model")
        joblib.dump(self.estimator, model_name)

    def evaluate_model(self, X_test, Y_test, orig_data):
        print("Evaluate model %d_%d.pkl" % (self.frame_len, self.predict_dist))
        model_name = "simple_reg_model/%d_%d.pkl" % (self.frame_len, self.predict_dist)
        self.estimator = joblib.load(model_name)
        pred = self.estimator.predict(X_test)
        res = 0
        score = 0
        assert(len(pred) == len(Y_test))
        pred = np.array(pred).reshape(-1)
        Y_test = np.array(Y_test).reshape(-1)
        for i in range(len(pred)):
            score += (float(pred[i]) - float(Y_test[i]))*(float(pred[i]) - float(Y_test[i]))
        score = np.sqrt(score/len(pred))
        print("score: %f" % score)
        for idx in range(len(pred)):
            buy_price = float(X_test[idx][0])
            date = int(orig_data[idx][1])
            if pred[idx] > buy_price*1.1:
                res += (int(Y_test[idx]) - buy_price*1.005)*(100000/buy_price)
                print("buy: %6d, sell: %6d, earn: %6d" % (buy_price, int(Y_test[idx]), (int(Y_test[idx]) - buy_price*1.005)*(100000/buy_price)))
        print("result: %d" % res)

    def load_current_data(self):
        con = sqlite3.connect('stock.db')
        code_list = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        X_test = []
        code_list = list(map(lambda x: x[0], code_list))
        first = True
        for code in code_list:
            df = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자').sort_index()
            data = df.iloc[-30:,:]
            data = data.reset_index()
            for col in data.columns:
                try:
                    data.loc[:, col] = data.loc[:, col].str.replace('--', '-')
                    data.loc[:, col] = data.loc[:, col].str.replace('+', '')
                except AttributeError as e:
                    pass
                    print(e)
            data.loc[:, 'month'] = data.loc[:, '일자'].str[4:6]
            data = data.drop(['일자', '체결강도'], axis=1)
            if len(data) < 30:
                continue
            X_test.extend(np.array(data))
            print(np.shape(X_test))
        X_test = np.array(X_test).reshape(-1, 23*30) 
        return X_test, code_list

    def make_buy_list(self, X_test, code_list):
        BUY_UNIT = 300000
        print("make buy_list")
        model_name = "simple_reg_model/%d_%d.pkl" % (self.frame_len, self.predict_dist)
        self.estimator = joblib.load(model_name)
        pred = self.estimator.predict(X_test)
        res = 0
        score = 0
        pred = np.array(pred).reshape(-1)

        buy_item = ["매수", "", "시장가", 0, 0, "매수전"]  # 매수/매도, code, 시장가/현재가, qty, price, "주문전/주문완료"
        with open("buy_list.txt", "wt", encoding='utf-8') as f_buy:
            for idx in range(len(pred)):
                buy_price = float(X_test[idx][0])
                print("[BUY?] code: %s, cur: %d, predict: %d" % (code_list[idx], buy_price, pred[idx]))
                if pred[idx] > buy_price*1.3:
                    print("add to buy_list %d")
                    buy_item[1] = code_list[idx]
                    buy_item[3] = int(BUY_UNIT / buy_price)
                    for item in buy_item:
                        f_buy.write("%s;"%str(item))
                    f_buy.write('\n')

    def load_data_in_account(self):
        # load code list from account
        code_list = []
        with open('stocks_in_account.txt', encoding='utf-8') as f_stocks:
            for line in f_stocks.readlines():
                data = line.split(',')
                code_list.append([data[6].replace('A', ''), data[1], data[0]])

        # load data in code_list
        con = sqlite3.connect('stock.db')
        X_test = []
        first = True
        for code in code_list:
            df = pd.read_sql("SELECT * from '%s'" % code[0], con, index_col='일자').sort_index()
            data = df.iloc[-30:,:]
            data = data.reset_index()
            for col in data.columns:
                try:
                    data.loc[:, col] = data.loc[:, col].str.replace('--', '-')
                    data.loc[:, col] = data.loc[:, col].str.replace('+', '')
                except AttributeError as e:
                    pass
                    print(e)
            data.loc[:, 'month'] = data.loc[:, '일자'].str[4:6]
            data = data.drop(['일자', '체결강도'], axis=1)
            if len(data) < 30:
                continue
            X_test.extend(np.array(data))
            print(np.shape(X_test))
        X_test = np.array(X_test).reshape(-1, 23*30) 
        return X_test, code_list

    def make_sell_list(self, X_test, code_list):
        print("make sell_list")
        model_name = "simple_reg_model/%d_%d.pkl" % (self.frame_len, self.predict_dist)
        self.estimator = joblib.load(model_name)
        pred = self.estimator.predict(X_test)
        res = 0
        score = 0
        pred = np.array(pred).reshape(-1)

        sell_item = ["매도", "", "시장가", 0, 0, "매도전"]  # 매수/매도, code, 시장가/현재가, qty, price, "주문전/주문완료"
        with open("sell_list.txt", "wt", encoding='utf-8') as f_sell:
            for idx in range(len(pred)):
                current_price = float(X_test[idx][0])
                print("[SELL?] code: %s, cur: %d, predict: %d" % (code_list[idx], current_price, pred[idx]))
                if pred[idx] < current_price:
                    print("add to sell_list %d")
                    sell_item[1] = code_list[idx][0]
                    sell_item[3] = code_list[idx][1]
                    for item in sell_item:
                        f_sell.write("%s;"%str(item))
                    f_sell.write('\n')


if __name__ == '__main__':
    sm = SimpleModel()
    #X_train, Y_train, _ = sm.load_all_data(20160101, 20161231)
    #sm.train_model(X_train, Y_train)
    #X_test, Y_test, Data = sm.load_all_data(20170101, 20170231)
    #sm.evaluate_model(X_test, Y_test, Data)

    X_data, code_list = sm.load_current_data()
    sm.make_buy_list(X_data, code_list)
    X_data, code_list = sm.load_data_in_account()
    sm.make_sell_list(X_data, code_list)
