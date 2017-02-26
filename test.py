import pandas as pd

def test_dataframe_replace():
    a = pd.DataFrame([{'a': '--10', 'b': '+20'}, {'a': '--10', 'b': '+20'}])
    a.loc[:, 'a'] = a.loc[:,'a'].str.replace('--', '-')
    print(a)


if __name__ == '__main__':
    test_dataframe_replace()