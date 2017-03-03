# -*- encoding: utf-8 -*-
import pandas as pd
import numpy as np
import sqlite3
from sklearn.ensemble.forest import RandomForestRegressor
from sklearn.externals import joblib
from keras.models import Sequential
from keras.layers import Dense, Dropout, normalization
from keras.wrappers.scikit_learn import KerasRegressor
from keras import backend as K
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
import os

MODEL_TYPE = 'keras'
def baseline_model():
    # create model
    model = Sequential()
    #model.add(Dense(128, input_dim=174, init='he_normal', activation='relu'))
    model.add(Dense(128, input_dim=690, init='he_normal', activation='relu'))
    model.add(normalization.BatchNormalization(epsilon=0.001, mode=0, axis=-1, momentum=0.99, weights=None, beta_init='zero', gamma_init='one', gamma_regularizer=None, beta_regularizer=None))

    #model.add(Dropout(0.1))
    model.add(Dense(128, init='he_normal'))
    model.add(Dense(1, init='he_normal'))
    # Compile model
    model.compile(loss='mean_squared_error', optimizer='adam')
    return model


class SimpleModel:
    def __init__(self):
        self.data = dict()
        self.frame_len = 30
        self.predict_dist = 5

    def load_all_data(self, begin_date, end_date):
        con = sqlite3.connect('stock.db')
        code_list = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        X_data_list, Y_data_list, DATA_list = [0]*10, [0]*10, [0]*10
        idx = 0
        split = int(len(code_list) / 9)
        for code in code_list:
            data = self.load_data(code[0], begin_date, end_date)
            data = data.dropna()
            X, Y = self.make_x_y(data)
            print(idx, split, len(code_list))
            if idx%split == 0:
                X_data_list[int(idx/split)] = list(X)
                Y_data_list[int(idx/split)] = list(Y)
                DATA_list[int(idx/split)] = data.values.tolist()
            else:
                X_data_list[int(idx/split)].extend(X)
                Y_data_list[int(idx/split)].extend(Y)
                DATA_list[int(idx/split)].extend(data.values.tolist())
            print(idx, np.shape(X_data_list[int(idx/split)]), np.shape(Y_data_list[int(idx/split)]))
            idx += 1
        for i in range(10):
            if i == 0:
                X_data = X_data_list[i]
                Y_data = Y_data_list[i]
                DATA = DATA_list[i]
            else:
                X_data.extend(X_data_list[i])
                Y_data.extend(Y_data_list[i])
                DATA.extend(DATA_list[i])
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

    def train_model_keras(self, X_train, Y_train):
        #Tensorflow GPU optimization
        config = tf.ConfigProto()
        config.gpu_options.allow_growth = True
        sess = tf.Session(config=config)
        K.set_session(sess)

        print("training model %d_%d.pkl" % (self.frame_len, self.predict_dist))
        model_name = "reg_keras/%d_%d.pkl" % (self.frame_len, self.predict_dist)
        self.estimator = KerasRegressor(build_fn=baseline_model, nb_epoch=20, batch_size=64, verbose=0)
        self.estimator.fit(X_train, Y_train)
        print("finish training model")
        # saving model
        json_model = estimator.model.to_json()
        open(model_name.replace('h5', 'json'), 'w').write(json_model)
        self.estimator.model.save_weights(model_name, overwrite=True)

    def evaluate_model(self, X_test, Y_test, orig_data):
        print("Evaluate model %d_%d.pkl" % (self.frame_len, self.predict_dist))
        if MODEL_TYPE == 'random_forest':
            model_name = "simple_reg_model/%d_%d.pkl" % (self.frame_len, self.predict_dist)
            self.estimator = joblib.load(model_name)
        elif MODEL_TYPE == 'keras':
            model_name = "reg_keras/%d_%d.h5" % (self.frame_len, self.predict_dist)
            self.estimator = model_from_json(open(model_name.replace('h5', 'json')).read())
            self.estimator.load_weights(model_name)
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
            buy_price = float(X_test[idx][23*29])
            date = int(orig_data[idx][0])
            if pred[idx] > buy_price*1.1:
                res += (int(Y_test[idx]) - buy_price*1.005)*(100000/buy_price+1)
                print("[%s] buy: %6d, sell: %6d, earn: %6d" % (str(date), buy_price, int(Y_test[idx]), (int(Y_test[idx]) - buy_price*1.005)*(100000/buy_price)))
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
                buy_price = float(X_test[idx][23*29])
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
                current_price = float(X_test[idx][23*29])
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
    X_train, Y_train, _ = sm.load_all_data(20110101, 20151231)
    sm.train_model_keras(X_train, Y_train)
    X_test, Y_test, Data = sm.load_all_data(20160101, 20170228)
    sm.evaluate_model(X_test, Y_test, Data)

    #X_data, code_list = sm.load_current_data()
    #sm.make_buy_list(X_data, code_list)
    #X_data, code_list = sm.load_data_in_account()
    #sm.make_sell_list(X_data, code_list)
