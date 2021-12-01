from ctypes import sizeof
import time
import pyupbit
import datetime
import math
from pytz import timezone
import json

access = ""
secret = ""
DEFAULT_TICKER = "KRW-BTC"
K = 0.5
risk_ratio = 0.02
TODAY_BUY_LIMIT = 5
ORDER_MIN_MONEY = 5500

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
        if df is None :
            print("## get_target_price : df is None")
            return None
    
        target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    
        return target_price
    except Exception as e:
        print(e)
        return None

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma5(ticker):
    """5일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    return ma5

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    try:
        return pyupbit.get_orderbook(ticker)["orderbook_units"][0]["ask_price"]
    except Exception as e:
        print(e)
        return None


def get_risk_modifier(ticker, target_volatility):
    """변동성 자금관리"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    if df is None :
        print("## get_risk_modifier : df is None")
        return 0
    range = df.iloc[0]['high'] - df.iloc[0]['low']
    range_percnetage = range / df.iloc[0]['close']
    return (target_volatility / range_percnetage)


def check_is_over_ma(ticker, current_price):
    """3. 5, 10, 20일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=20)
    if df is None :
        print("## check_is_over_ma : df is None")
        return False
    ma = df['close'].rolling(window=3).mean().iloc[-1]
    if (ma < current_price):
        return True
    ma = df['close'].rolling(window=5).mean().iloc[-1]
    if (ma < current_price):
        return True
    ma = df['close'].rolling(window=10).mean().iloc[-1]
    if (ma < current_price):
        return  True
    ma = df['close'].rolling(window=20).mean().iloc[-1]
    if (ma < current_price):
        return True
    return False

def check_is_over_ma5(ticker, current_price):
    """5일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=5)
    if df is None :
        print("## check_is_over_ma5 : df is None")
        return False
    ma5 = df['close'].rolling(5).mean().iloc[-1]
    if (ma5 < current_price):
        return True
    return False


def check_is_min_order(ticker, order_money):
    chance = upbit.get_chance(ticker)
    print(chance)
    return int(chance['market']['bid']['min_total']) < order_money


def load_config_moving_average():
    with open("config.json", 'r', encoding='UTF-8') as json_file:
        json_data = json.load(json_file)
    
        return json_data["moving_average"]

def load_config_tickers():
    with open("config.json", 'r', encoding='UTF-8') as json_file:
        json_data = json.load(json_file)
        tickers  = json_data["tickers"]

        if (len(tickers) < 1):
            tickers = ["KRW-BTC"]

        return tickers
    return None

# 설정파일
krw_tickers = ["KRW-BTC"]
is_moving_average_5 = False

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

# 자동매매 시작
start_time = datetime.datetime.now()
end_time = start_time

# ticker
today_buy_coins = []
is_today_sell = False
krw = 0

time.sleep(1)
while True:
    try:        
        now = datetime.datetime.now()

        # 하루 타이머 갱신
        if end_time < now:
            print("## load config file...")

            is_moving_average_5 = load_config_moving_average()
            krw_tickers = load_config_tickers()

            print("config moving average : {0}".format(is_moving_average_5))
            
            print("config tickers >")
            for each_ticker in krw_tickers:
                print("    ticker : {0}".format(each_ticker))

            start_time = get_start_time(DEFAULT_TICKER)
            end_time = start_time + datetime.timedelta(days=1)

            today_buy_coins.clear()
            is_today_sell = False

            
            krw = get_balance("KRW")
            krw = 50000
            print("==========================================================")
            print("change date = {0} ~ {1}".format(start_time, end_time))
            print("current balance = {0}".format(krw))
        

        # 매매
        if (start_time < now < end_time - datetime.timedelta(seconds=60 * 1)):
            if len(today_buy_coins) < TODAY_BUY_LIMIT: 

                if krw > ORDER_MIN_MONEY:
                    buy_coins = []

                    sleep_count = 0
                    for each_ticker in krw_tickers:
                        if not (each_ticker in today_buy_coins):
                            target_price = get_target_price(each_ticker, K)
                            current_price = get_current_price(each_ticker)
                            if (target_price is not None and current_price is not None) and target_price < current_price:
                                
                                if is_moving_average_5 is True:
                                    if check_is_over_ma5(each_ticker, target_price):
                                        buy_coins.append(each_ticker)
                                else:    
                                    if check_is_over_ma(each_ticker, target_price):
                                        buy_coins.append(each_ticker)
                           
                            # sleep
                            sleep_count = sleep_count + 1
                            if sleep_count % 10 == 0:
                                time.sleep(1)

                        if TODAY_BUY_LIMIT <= len(buy_coins) + len(today_buy_coins):
                            break
            
                    for buy_ticker in buy_coins:
                      
                        order_money = krw * (get_risk_modifier(buy_ticker, risk_ratio) / TODAY_BUY_LIMIT)
                        order_money = math.floor(order_money * 0.9995)
                        print((get_risk_modifier(buy_ticker, risk_ratio) / TODAY_BUY_LIMIT))
                        if order_money < ORDER_MIN_MONEY:
                            order_money = ORDER_MIN_MONEY

                        result = upbit.buy_market_order(buy_ticker, order_money)
                        if (result is None) :
                            print("## Failed buy_market_order : {0}".format(buy_ticker))
                        else:
                            today_buy_coins.append(buy_ticker)
                            print("++매수요청! 티커 : {0:>10}, 거래액 : ₩{1:>15,}, timestamp : {2}\n{3}".format(buy_ticker, order_money, now, result))
                        time.sleep(0.2)
                    print(str(now) + " : buy process done. ")

            time.sleep(20)
         
        # 매도
        else:
            if is_today_sell == False:
                balances = upbit.get_balances()
                
                balance_count = 0
                for b in balances:
                     if b['balance'] is not None and b['currency'] is not None and b['currency'] != "KRW" and b['currency'] != "SGB":
                         balance_count = balance_count + 1
                is_today_sell = balance_count < 1

                for b in balances:
                    if b['balance'] is not None and b['currency'] is not None and b['currency'] != "KRW" and b['currency'] != "SGB":
                        ticker = "KRW-" + b['currency']

                        result = upbit.sell_market_order(ticker, float(b['balance']))
                        print("--매도요청! 현재가 : {0}, 수량 : {1}\n{2}".format(ticker, b['balance'], result))
                        time.sleep(0.2)        

                krw = math.floor(get_balance("KRW"))
                print("잔고 : ₩{0:<15,}".format(krw))                

            time.sleep(5)                

    except Exception as e:
        print(e)
        time.sleep(10)
