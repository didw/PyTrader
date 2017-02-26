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
            X, Y = self.make_x_y(data)
            if first:
                X_data = list(X)
                Y_data = list(Y)
                first = False
                print(np.shape(X_data), np.shape(Y_data))
            else:
                X_data.extend(X)
                Y_data.extend(Y)
                print(np.shape(X_data), np.shape(Y_data))
        return np.array(X_data), np.array(Y_data)

    def load_data(self, code, begin_date, end_date):
        con = sqlite3.connect('stock.db')
        df = pd.read_sql("SELECT * from '%s'" % code, con).sort_values(by=['일자'], ascending=True)
        remove_index = []
        for idx in range(len(df)):
            date = int(df['일자'][idx])
            if date < begin_date or date > end_date:
                remove_index.append(idx)
        data = df.drop(df.index[remove_index])
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
        data.loc[:,'일자'] = data.loc[:,'일자'].str[4:6]
        data = data.drop(['index', '체결강도'], axis=1)
        for i in range(self.frame_len+self.predict_dist, len(data)):
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
            data_y.extend(data.loc[i-self.frame_len-self.predict_dist, ['현재가']])
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

    def evaluate_model(self, X_test, Y_test):
        print("Evaluate model %d_%d.pkl" % (self.frame_len, self.predict_dist))
        model_name = "simple_reg_model/%d_%d.pkl" % (self.frame_len, self.predict_dist)
        self.estimator = joblib.load(model_name)
        pred = self.estimator.predict(X_test)
        res = 0
        score = 0
        assert(len(pred) == len(Y_test))
        score += np.sqrt(np.reduce_mean((Y_test - pred)*(Y_test - pred)))
        print("score: %f" % score)
        for idx in range(len(pred)):
            buy_price = X_test[idx][1]
            if pred[idx] > buy_price:
                res += (Y_test[idx] - buy_price)
        print("result: %d" % res)


if __name__ == '__main__':
    sm = SimpleModel()
    #X_train, Y_train = sm.load_all_data(20100101, 20151231)
    #sm.train_model(X_train, Y_train)

    X_test, Y_test = sm.load_all_data(20160101, 20161231)
    sm.evaluate_model(X_test, Y_test)
