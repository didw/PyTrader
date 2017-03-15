import pandas as pd
import sqlite3
import glob
import h5py

def convert_sql_to_csv():
    con = sqlite3.connect("../data/stock.db")
    code_list = con.execute("SELECT name from sqlite_master WHERE type='table'").fetchall()
    code = code_list[0][0]
    for code in code_list:
        code = code[0]
        data = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자').sort_index()
        data.to_csv('../data/stocks/%s.csv' % code)

def convert_sql_to_h5():
    con = sqlite3.connect("../data/stock.db")
    code_list = con.execute("SELECT name from sqlite_master WHERE type='table'").fetchall()
    code = code_list[0][0]
    for code in code_list:
        code = code[0]
        data = pd.read_sql("SELECT * from '%s'" % code, con, index_col='일자').sort_index()
        data.to_hdf('../data/h5/%s.h5'%code,'df',mode='w',data_columns=True)

def read_h5():
    code_list = glob.glob('../data/h5/*')
    for code in code_list[:10]:
        h = h5py.File(code)
        print(h)

if __name__ == '__main__':
    read_h5()
