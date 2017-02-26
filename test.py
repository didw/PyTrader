import pandas as pd

def test_dataframe_replace():
    a = pd.DataFrame([{'a': '20170102', 'b': '--10', 'c': '+20'}, {'a': '20170103', 'b': '--20', 'c': '--20'}])
    a.loc[:,'a'] = a.loc[:,'a'].str[4:6]
    for c in a.columns:
        a.loc[:,c] = a.loc[:,c].str.replace('--', '-')
    print(a)


if __name__ == '__main__':
    test_dataframe_replace()