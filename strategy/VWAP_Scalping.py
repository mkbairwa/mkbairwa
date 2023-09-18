import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime as dt
import datetime
from five_paisa import *
from backtesting import Strategy
from backtesting import Backtest

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

df = client.historical_data('N', 'C', 3045, '5m', '2023-01-01', '2023-03-24')
df["Datetime"]=df["Datetime"].str.replace("T"," ")
df['Datetime']=pd.to_datetime(df['Datetime'],format='%Y-%m-%d %H:%M:%S')
df.set_index("Datetime", inplace=True)
print(df.tail(5))
print(df.info())
df=df[df['High']!=df['Low']]

df["VWAP"]=ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
df['RSI']=ta.rsi(df['Close'], length=16)
my_bbands = ta.bbands(df['Close'], length=14, std=2.0)
df=df.join(my_bbands)
print(df.tail(5))
print(df.info())


VWAPsignal = [0]*len(df)
backcandles = 15


for row in range(backcandles, len(df)):
    upt = 1
    dnt = 1
    for i in range(row-backcandles, row+1):
        if max(df['Open'][i], df['Close'][i])>=df['VWAP'][i]:
            dnt=0
        if min(df['Open'][i], df['Close'][i])<=df['VWAP'][i]:
            upt=0
    if upt==1 and dnt==1:
        VWAPsignal[row]=3
    elif upt==1:
        VWAPsignal[row]=2
    elif dnt==1:
        VWAPsignal[row]=1

df['VWAPSignal'] = VWAPsignal

def TotalSignal(l):
    if (df['VWAPSignal'][l]==2
        and df['Close'][l]<=df['BBL_14_2.0'][l]
        and df['RSI'][l]<45):
            return 2
    if (df['VWAPSignal'][l]==1
        and df['Close'][l]>=df['BBU_14_2.0'][l]
        and df['RSI'][l]>55):
            return 1
    return 0
        
TotSignal = [0]*len(df)
for row in range(backcandles, len(df)): #careful backcandles used previous cell
    TotSignal[row] = TotalSignal(row)
df['TotalSignal'] = TotSignal

df[df['TotalSignal']!=0].count()
print(df.tail(50))

def pointposbreak(x):
    if x['TotalSignal']==1:
        return x['High']+1e-4
    elif x['TotalSignal']==2:
        return x['Low']-1e-4
    else:
        return np.nan

df['pointposbreak'] = df.apply(lambda row: pointposbreak(row), axis=1)
print(df.tail(50))

st=10400
dfpl = df[st:st+350]
dfpl.reset_index(inplace=True)
fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
                open=dfpl['Open'],
                high=dfpl['High'],
                low=dfpl['Low'],
                close=dfpl['Close']),
                go.Scatter(x=dfpl.index, y=dfpl['VWAP'], 
                           line=dict(color='blue', width=1), 
                           name="VWAP"), 
                go.Scatter(x=dfpl.index, y=dfpl['BBL_14_2.0'], 
                           line=dict(color='green', width=1), 
                           name="BBL"),
                go.Scatter(x=dfpl.index, y=dfpl['BBU_14_2.0'], 
                           line=dict(color='green', width=1), 
                           name="BBU")])

fig.add_scatter(x=dfpl.index, y=dfpl['pointposbreak'], mode="markers",
                marker=dict(size=10, color="MediumPurple"),
                name="Signal")
fig.show()

dfpl = df.copy()

dfpl['ATR']=ta.atr(dfpl['High'], dfpl['Low'], dfpl['Close'], length=7)
#help(ta.atr)
def SIGNAL():
    return dfpl['TotalSignal']

class MyStrat(Strategy):
    initsize = 0.99
    mysize = initsize
    def init(self):
        super().init()
        self.signal1 = self.I(SIGNAL)

    def next(self):
        super().next()
        slatr = 1.2*self.data.ATR[-1]
        TPSLRatio = 1.5

        if len(self.trades)>0:
            if self.trades[-1].is_long and self.data.RSI[-1]>=90:
                self.trades[-1].close()
            elif self.trades[-1].is_short and self.data.RSI[-1]<=10:
                self.trades[-1].close()
        
        if self.signal1==2 and len(self.trades)==0:
            sl1 = self.data.Close[-1] - slatr
            tp1 = self.data.Close[-1] + slatr*TPSLRatio
            self.buy(sl=sl1, tp=tp1, size=self.mysize)
        
        elif self.signal1==1 and len(self.trades)==0:         
            sl1 = self.data.Close[-1] + slatr
            tp1 = self.data.Close[-1] - slatr*TPSLRatio
            self.sell(sl=sl1, tp=tp1, size=self.mysize)

bt = Backtest(dfpl, MyStrat, cash=100, margin=1/10, commission=0.00)
stat = bt.run()
print(stat)

bt.plot(show_legend=False)