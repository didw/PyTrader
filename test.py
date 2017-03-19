# -*- encoding: utf-8 -*-
import pandas as pd
import sqlite3

def test_dataframe_replace():
    a = pd.DataFrame([{'a': '20170102', 'b': '--10', 'c': '+20'}, {'a': '20170103', 'b': '--20', 'c': '--20'}])
    a.loc[:,'a'] = a.loc[:,'a'].str[4:6]
    for c in a.columns:
        a.loc[:,c] = a.loc[:,c].str.replace('--', '-')
    print(a)

def concat_df():
    A = pd.DataFrame([{'일자':'20161201', '가격': '1231', '거래': '1231'}, {'일자':'20161200', '가격': '1231', '거래': '1231'}])
    B = pd.DataFrame([{'일자':'20161101', '가격': '1231', '거래': '1231'}, {'일자':'20161100', '가격': '1231', '거래': '1231'}])
    C = A.loc[:, ['가격', '거래']]
    C.index = A.loc[:,'일자']
    D = B.loc[:, ['가격', '거래']]
    D.index = B.loc[:,'일자']
    print(C)
    print(D)
    E = pd.concat([C,D], axis=0)
    print(E)
    F = E.loc[E.index < C.index[0]]
    print(F)

def get_sqlite(code):
    con = sqlite3.connect("stock.db")
    data = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자')
    print(data.index[0])
    print(data.head())
    data = data.loc[data.index > '20170102']
    data.to_sql(code, con, if_exists='replace')

def convert_index_sqlite():
    con = sqlite3.connect("stock.db")
    code_list = con.execute("SELECT name from sqlite_master WHERE type='table'").fetchall()
    for code in code_list:
        print("convert %s" % code[0])
        if '(' in code[0]:
            continue
        try:
            data = pd.read_sql("SELECT * from '%s'" % code[0], con, index_col='index')
        except:
            data = pd.read_sql("SELECT * from '%s'" % code[0], con, index_col='일자')
        data.index.name = '일자'
        #data = data.loc[data.index > '20010101']
        data.to_sql(code[0], con, if_exists='replace')

def delete_table(table_name):
    con = sqlite3.connect("stock.db")
    con.execute("DROP TABLE '%s'" % table_name)

def print_table_columns():
    con = sqlite3.connect("../data/stock.db")
    code_list = con.execute("SELECT name from sqlite_master WHERE type='table'").fetchall()
    code = code_list[0][0]
    data = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자')
    print(data.columns)

def print_table_tail():
    con = sqlite3.connect("../data/stock.db")
    code_list = con.execute("SELECT name from sqlite_master WHERE type='table'").fetchall()
    code = code_list[0][0]
    for code in code_list:
        code = code[0]
        data = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자')
        print(data.index[len(data)-3:len(data)])

if __name__ == '__main__':
    print_table_tail()
