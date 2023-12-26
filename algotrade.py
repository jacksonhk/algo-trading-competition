from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib
import numpy

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000, 1, 1)
        self.start_time = None  # the starting time of the trading
        self.arr_close = numpy.array([])
        self.ma_len = 20
        self.rsi_len = 14
        self.wait_time = self.ma_len  # in days

    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        if not self.start_time:
            self.start_time = bd[self.myinstrument]['timestamp']

        if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours=24):
            self.lasttradetime = bd[self.myinstrument]['timestamp']
            lastprice = bd[self.myinstrument]['lastPrice']
            self.arr_close = numpy.append(self.arr_close, lastprice)

            if len(self.arr_close) > self.ma_len:
                self.arr_close = self.arr_close[-self.ma_len:]

            if bd[self.myinstrument]['timestamp'] <= self.start_time + timedelta(days=self.wait_time):
                return

            sma = self.find_sma(self.arr_close, self.ma_len)
            sd = numpy.std(self.arr_close[-self.ma_len:])
            upper_bband = sma + 2 * sd
            lower_bband = sma - 2 * sd

            self.evt.consoleLog(f"datetime: {bd[self.myinstrument]['timestamp']}")
            self.evt.consoleLog(f"sma: {sma}")
            self.evt.consoleLog(f"upper: {upper_bband}")
            self.evt.consoleLog(f"lower: {lower_bband}")

            # Check for bullish divergence
            if lastprice < lower_bband and self.arr_close[-2] > lower_bband:
                bullish_divergence = True
            else:
                bullish_divergence = False

            # Check for bearish divergence
            if lastprice > upper_bband and self.arr_close[-2] < upper_bband:
                bearish_divergence = True
            else:
                bearish_divergence = False

            if bullish_divergence:
                rsi = self.find_rsi(self.arr_close, self.rsi_len)
                self.evt.consoleLog(f"rsi: {rsi}")
                if rsi > 70:
                    stop_loss = lastprice * 0.9  # Set a fixed stop loss level (90% of last price)
                    self.test_sendOrder(lastprice, -1, 'open', stop_loss)
                    self.evt.consoleLog("sell")

            if bearish_divergence:
                rsi = self.find_rsi(self.arr_close, self.rsi_len)
                self.evt.consoleLog(f"rsi: {rsi}")
                if rsi < 30:
                    stop_loss = lastprice * 0.9  # Set a fixed stop loss level (90% of last price)
                    self.test_sendOrder(lastprice, 1, 'open', stop_loss)
                    self.evt.consoleLog("buy")

    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        pass

    def on_openPositionfeed(self, op, oo, uo):
        pass

    def find_sma(self, data, window_size):
        return data[-window_size:].sum() / window_size

    def find_rsi(self, arr_close, window_size):
        deltas = numpy.diff(arr_close)
        gains = deltas * (deltas > 0)
        losses = -deltas * (deltas < 0)

        avg_gain = numpy.mean(gains[:window_size])
        avg_loss = numpy.mean(losses[:window_size])

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def test_sendOrder(self, lastprice, buysell, openclose, stop_loss):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = 1
        if buysell == 1:
            order.takeProfitLevel = lastprice * 1.1
            order.stopLossLevel = stop_loss
        elif buysell == -1:
            order.takeProfitLevel = lastprice * 0.9
            order.stopLossLevel = stop_loss
        order.volume = 10
        order.openclose = opencloseorder.buysell = buysell
        order.ordertype = 0  # 0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)
