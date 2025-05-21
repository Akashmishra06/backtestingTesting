from strategyTools.infra import getBuyLimitPrice, getSellLimitPrice, postOrderToDbLIMITStock
from strategyTools.statusUpdater import infoMessage, errorMessage, positionUpdator
from strategyTools.tools import OHLCDataFetch, resample_data, get_candle_data
from pandas.api.types import is_datetime64_any_dtype
from strategyTools import dataFetcher, reconnect
from configparser import ConfigParser
from collections import defaultdict
from datetime import datetime, time
import os
import talib
import logging
import pandas as pd
import json
from time import sleep




def portfolioValue():
    df = combineOpenPnlCSV()
    
    # Initialize logging
    import csv
    from datetime import datetime
    
    log_filename = f"portfolio_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    df['EntryTime'] = pd.to_datetime(df['EntryTime'])
    AlgoStartDate = df['EntryTime'].min()

    # Get unique stocks in the portfolio
    stocks = df['Symbol'].unique()
    
    # Fetch daily close prices for each stock
    stock_data = {}
    for stock in stocks:
        stock_df = get_candle_data(stock, AlgoStartDate.timestamp(), 'd')
        if not stock_df.empty:
            stock_df['date'] = pd.to_datetime(stock_df['date']).dt.date
            stock_data[stock] = stock_df.set_index('date')['Close']
    
    # Convert EntryTime to date for matching with stock data
    df['EntryDate'] = pd.to_datetime(df['EntryTime']).dt.date
    
    # Get all unique dates from stock data
    all_dates = set()
    for stock in stock_data:
        all_dates.update(stock_data[stock].index)
    all_dates = sorted(all_dates)
    
    # Prepare detailed logging
    with open(log_filename, 'w', newline='') as logfile:
        writer = csv.writer(logfile)
        # Write header
        writer.writerow([
            'Date', 
            'Portfolio Value', 
            'Peak Value', 
            'Drawdown %',
            'Stock', 
            'Quantity', 
            'Entry Price', 
            'Daily Close', 
            'Position Value',
            'Stock Drawdown %'
        ])

        # Calculate portfolio value over time
        portfolio_values = []
        peak_values = []
        daily_drawdowns = []

        for date in all_dates:
            # Filter positions that were open on this date
            open_positions = df[df['EntryDate'] <= pd.to_datetime(date)]
            if len(open_positions) == 0:
                continue
            
            # Calculate total portfolio value for this date
            total_value = 0
            position_details = []
            
            for _, position in open_positions.iterrows():
                stock = position['Symbol']
                quantity = position['Quantity']
                entry_price = position['EntryPrice']
                
                # Get stock's close price on this date
                if stock in stock_data and date in stock_data[stock].index:
                    close_price = stock_data[stock].loc[date]
                    stock_value = close_price * quantity
                    total_value += stock_value
                    
                    # Calculate stock drawdown
                    relevant_prices = stock_data[stock][stock_data[stock].index >= position['EntryDate']]
                    lowest_price = relevant_prices.min()
                    stock_drawdown = (entry_price - lowest_price) / entry_price * 100

                    position_details.append({
                        'stock': stock,
                        'quantity': quantity,
                        'entry_price': entry_price,
                        'close_price': close_price,
                        'position_value': stock_value,
                        'stock_drawdown': stock_drawdown
                    })

            # Calculate daily portfolio metrics
            if not portfolio_values:  # First day
                peak = total_value
            else:
                peak = max(peak, total_value)

            drawdown = (peak - total_value) / peak * 100 if peak != 0 else 0

            portfolio_values.append(total_value)
            peak_values.append(peak)
            daily_drawdowns.append(drawdown)
            
            # Write detailed log for each position
            for pos in position_details:
                writer.writerow([
                    date.strftime('%Y-%m-%d'),
                    round(total_value, 2),
                    round(peak, 2),
                    round(drawdown, 2),
                    pos['stock'],
                    pos['quantity'],
                    pos['entry_price'],
                    pos['close_price'],
                    round(pos['position_value'], 2),
                    round(pos['stock_drawdown'], 2)
                ])
    
    # Calculate final max drawdown
    max_drawdown = max(daily_drawdowns) if daily_drawdowns else 0
    
    print(f"Detailed portfolio log saved to: {log_filename}")
    return max_drawdown


# def portfolioValue():
#     df = combineOpenPnlCSV()

#     df['EntryTime'] = pd.to_datetime(df['EntryTime'])
#     AlgoStartDate = df['EntryTime'].min()

#     # Get unique stocks in the portfolio
#     stocks = df['Symbol'].unique()
    
#     # Fetch daily close prices for each stock
#     stock_data = {}
#     for stock in stocks:
#         stock_df = get_candle_data(stock, AlgoStartDate.timestamp(), 'd')
#         if not stock_df.empty:
#             stock_df['date'] = pd.to_datetime(stock_df['date']).dt.date
#             stock_data[stock] = stock_df.set_index('date')['Close']
    
#     # Convert EntryTime to date for matching with stock data
#     df['EntryDate'] = pd.to_datetime(df['EntryTime']).dt.date
    
#     # Get all unique dates from stock data
#     all_dates = set()
#     for stock in stock_data:
#         all_dates.update(stock_data[stock].index)
#     all_dates = sorted(all_dates)
    
#     # Calculate portfolio value over time
#     portfolio_values = []
    
#     for date in all_dates:
#         # Filter positions that were open on this date
#         open_positions = df[df['EntryDate'] <= pd.to_datetime(date)]
#         if len(open_positions) == 0:
#             continue
        
#         total_value = 0
        
#         for _, position in open_positions.iterrows():
#             stock = position['Symbol']
#             quantity = position['Quantity']
            
#             if stock in stock_data and date in stock_data[stock].index:
#                 close_price = stock_data[stock].loc[date]  # Correct: Using .loc[index]
#                 stock_value = close_price * quantity
#                 total_value += stock_value
        
#         portfolio_values.append((date, total_value))
    
#     if not portfolio_values:
#         return {"portfolio_max_drawdown": 0, "stock_drawdowns": {}}

#     dates, values = zip(*sorted(portfolio_values))
#     peak = values[0]
#     max_drawdown = 0

#     for value in values:
#         if value > peak:
#             peak = value
#         drawdown = (peak - value) / peak
#         if drawdown > max_drawdown:
#             max_drawdown = drawdown
    
#     stock_drawdowns = {}
#     for _, position in df.iterrows():
#         stock = position['Symbol']
#         entry_price = position['EntryPrice']

#         if stock in stock_data:
#             stock_prices = stock_data[stock]
#             entry_date = position['EntryDate']
#             relevant_prices = stock_prices[stock_prices.index >= entry_date]
#             if not relevant_prices.empty:
#                 lowest_price = relevant_prices.min()
#                 drawdown = (entry_price - lowest_price) / entry_price
#                 stock_drawdowns[stock] = drawdown
    
#     return (max_drawdown*100)


def niftyFifty():

    openPnl = combineOpenPnlCSV()

    openPnl['EntryTime'] = pd.to_datetime(openPnl['EntryTime'])
    AlgoStartDate = openPnl['EntryTime'].min()

    df = get_candle_data("NIFTY 50", AlgoStartDate.timestamp(), 'd')
    df['RunningMax'] = df['Close'].cummax()
    df['Drawdown'] = (df['Close'] - df['RunningMax']) / df['RunningMax']
    df['DrawdownPct'] = df['Drawdown'] * 100
    max_drawdown = df['Drawdown'].min()
    print(f"Maximum Drawdown: {max_drawdown:.2%}")

    try:
        symbol = "NIFTY 50"
        current_timestamp = datetime.now().timestamp()
        bufferTimestamp = current_timestamp - (86400 * 10)
        df_1d, a, b = OHLCDataFetch(symbol, current_timestamp, bufferTimestamp, 'd', 10, None)
        df_1Min, c, d = OHLCDataFetch(symbol, current_timestamp, bufferTimestamp, 1, 10, None)

        if df_1d is not None and not df_1d.empty and len(df_1d) > 1:
            prev_day_close = df_1d.iloc[-1]["Close"]
            currentPrice = df_1Min.iloc[-1]["Close"]
        else:
            print(f"Data for symbol {symbol} is empty or invalid.")
    except Exception as e:
        print(f"Error fetching data for symbol {symbol} at {current_timestamp}: {e}")

    df['date'] = pd.to_datetime(df['date'])

    oldest_day_row = df[df['date'].dt.date == AlgoStartDate.date()].iloc[0]
    AlgoStartDateNiftyClose = oldest_day_row['Close']

    quantityNifty = int(1500000 // AlgoStartDateNiftyClose)

    niftyMTM = ((currentPrice - prev_day_close) * quantityNifty)
    netProfit = ((currentPrice - AlgoStartDateNiftyClose) * quantityNifty)

    niftyMtmPercentage = ((niftyMTM / (prev_day_close * quantityNifty))*100)
    niftynetProfitPercentage = ((netProfit / 1500000) * 100)

    return AlgoStartDate.date(), AlgoStartDateNiftyClose, quantityNifty, niftyMTM, netProfit, niftyMtmPercentage, niftynetProfitPercentage, (max_drawdown*100)

def updateCurrentPrices(self1):
    currentDatetime = datetime.now()
    currentTime = currentDatetime.time()

    for stock, stock_data in self1.stockDict.items():
        try:
            try:
                df_1d, candle_flag_1d, last_candle_time_1d = OHLCDataFetch(stock, currentDatetime.timestamp(), self1.candle_1d[stock]['last_candle_time'], 'd',
                    150, self1.candle_1d[stock]['df'], self1.stockDict[stock].stockLogger)
                self1.candle_1d[stock]['df'] = df_1d
                self1.candle_1d[stock]['last_candle_time'] = last_candle_time_1d
                resample_data(df_1d, 'd')
                self1.rename_col(df_1d)
            except Exception as e:
                self1.stockDict[stock].stockLogger.error(f"Error fetching daily OHLC data for {stock}: {e}")
                continue

            if df_1d is None or df_1d.empty:
                raise ValueError(f"Empty or invalid dataframe fetched for {stock}")

            prev_day_close = df_1d.iloc[-2]['c'] if len(df_1d) > 1 else df_1d.iloc[-1]['c']
            self1.stockDict[stock].prev_day_close = prev_day_close
            stock_data.stockLogger.info(f'Updated prev_day_close for {stock}: {prev_day_close}')

        except Exception as e:
            self1.stockDict[stock].stockLogger.error(f"Error fetching daily OHLC data for {stock}: {e}")
            continue

        try:
            if stock_data.openPnl is not None and not stock_data.openPnl.empty:
                currentPrice = dataFetcher([self1.idMap[stock]])[self1.idMap[stock]]
                stock_data.stockLogger.info(f'[Tick] => Current Price for {stock}: {currentPrice}')

                for index, row in stock_data.openPnl.iterrows():
                    try:
                        stock_data.openPnl.at[index, "CurrentPrice"] = currentPrice
                        stock_data.openPnl.at[index, "prev_day_c"] = self1.stockDict[stock].prev_day_close
                    except Exception as e:
                        stock_data.stockLogger.error(f"Error updating PnL for {stock} at index {index}: {e}")
                        continue

                stock_data.pnlCalculator()

        except Exception as e:
            self1.stockDict[stock].stockLogger.error(f"Error updating prices for {stock}: {e}")
            continue

def algoInfoMessage():

    openTradesdf = combineOpenPnlCSV()
    closeTradesdf = combineClosePnlCSV()
    symbolsList = None

    current_timestamp = datetime.now().timestamp()
    bufferTimestamp = current_timestamp - (86400 * 10)

    if openTradesdf is not None and not openTradesdf.empty and closeTradesdf is not None and not closeTradesdf.empty:
        symbolsList = pd.concat([openTradesdf['Symbol'], closeTradesdf['Symbol']]).drop_duplicates()
        print(symbolsList)
    elif openTradesdf is not None and not openTradesdf.empty:
        symbolsList = openTradesdf['Symbol']
    elif closeTradesdf is not None and not closeTradesdf.empty:
        symbolsList = closeTradesdf['Symbol']

    allSymbols_prev_day_c = defaultdict(float)
    allSymbols_CurrentPrice = defaultdict(float)

    if symbolsList is not None:
        for symbol in symbolsList:
            try:
                df_1d, a, b = OHLCDataFetch(symbol, current_timestamp, bufferTimestamp, 'd', 10, None)
                df_1Min, c, d = OHLCDataFetch(symbol, current_timestamp, bufferTimestamp, 1, 10, None)

                if df_1d is not None and not df_1d.empty and len(df_1d) > 1:
                    allSymbols_prev_day_c[symbol] = df_1d.iloc[-1]["Close"]
                    allSymbols_CurrentPrice[symbol] = df_1Min.iloc[-1]["Close"]
                else:
                    print(f"Data for symbol {symbol} is empty or invalid.")
            except Exception as e:
                print(f"Error fetching data for symbol {symbol} at {current_timestamp}: {e}")

    TotalValue = 1500000

    totalInvestedAmount = totalCurrentAmount = netPnl = realisedPnl = 0
    totalInvestedAmountPercentage = totalCurrentAmountPercentage = netPnlPercentage = realisedPnlPercentage = 0
    mtm = mtmPercentage = 0

    if openTradesdf is not None and not openTradesdf.empty:
        totalInvestedAmount = 0
        totalCurrentAmount = 0

        for index, row in openTradesdf.iterrows():
            symbol = row['Symbol']
            quantity = row['Quantity']
            entry_price = row['EntryPrice']

            current_price = allSymbols_CurrentPrice.get(symbol, 0)

            totalInvestedAmount += entry_price * quantity
            totalCurrentAmount += current_price * quantity

        totalInvestedAmountPercentage = (totalInvestedAmount * 100) / TotalValue
        totalCurrentAmountPercentage = (totalCurrentAmount * 100) / TotalValue

        netPnl = totalCurrentAmount - totalInvestedAmount
        netPnlPercentage = (netPnl * 100) / totalInvestedAmount

    if closeTradesdf is not None and not closeTradesdf.empty:
        realisedPnl = closeTradesdf['Pnl'].sum()
        realisedPnlPercentage = (realisedPnl * 100) / TotalValue

    if openTradesdf is not None and not openTradesdf.empty:
        df_openPositions = openTradesdf.copy()
        df_openPositions['todayTrade'] = ""

        for index, row in df_openPositions.iterrows():
            symbol = row['Symbol']
            quantity = row['Quantity']
            entry_price = row['EntryPrice']
            current_price = allSymbols_CurrentPrice.get(symbol, 0)
            prev_day_c = allSymbols_prev_day_c.get(symbol, 0)
            df_openPositions.at[index, 'CurrentPrice'] = current_price
            df_openPositions.at[index, 'prev_day_c'] = prev_day_c

            if datetime.now().date() == row['EntryTime'].date():
                df_openPositions.at[index, 'todayTrade'] = "Yes"
            elif datetime.now().date() != row['EntryTime'].date():
                df_openPositions.at[index, 'todayTrade'] = "No"

        df_today = df_openPositions[df_openPositions['todayTrade'] == "Yes"]
        df_oldDay = df_openPositions[df_openPositions['todayTrade'] == "No"]

        df_today['mtmm'] = ((df_today['CurrentPrice'] - df_today['EntryPrice']) * df_today['Quantity'])
        df_oldDay['mtmm'] = ((df_oldDay['CurrentPrice'] - df_oldDay['prev_day_c']) * df_oldDay['Quantity'])

        openmtm = (df_oldDay['mtmm'].sum()) + (df_today['mtmm'].sum())
    else:
        openmtm = 0

    if closeTradesdf is not None and not closeTradesdf.empty:
        df = closeTradesdf.copy()
        df['prev_c'] = ""
        df['todayTrade'] = ""

        for index, row in df.iterrows():
            symbol = row['Symbol']
            quantity = row['Quantity']
            entry_price = row['EntryPrice']
            current_price = allSymbols_CurrentPrice.get(symbol, 0)
            df.at[index, 'prev_c'] = current_price

            if (row['ExitTime'].date() == datetime.now().date()) and (row['Key'].date() == datetime.now().date()):
                df.at[index, 'todayTrade'] = "Yes"
            elif (row['ExitTime'].date() == datetime.now().date()) and (row['Key'].date() != datetime.now().date()):
                df.at[index, 'todayTrade'] = "No"

        df_today = df[df['todayTrade'] == "Yes"]
        df_oldDay = df[df['todayTrade'] == "No"]

        df_today['mtm'] = ((df_today['ExitPrice'] - df_today['EntryPrice']) * df_today['Quantity'])
        df_oldDay['mtm'] = ((df_oldDay['ExitPrice'] - df_oldDay['prev_c']) * df_oldDay['Quantity'])

        sameDayMtmClose = (df_today['mtm'].sum()) + (df_oldDay['mtm'].sum())
        finalclosedMtm = sameDayMtmClose
    else:
        finalclosedMtm = 0

    if (abs(finalclosedMtm) > 0) or (abs(openmtm) > 0):
        mtm = finalclosedMtm + openmtm
        mtmPercentage = ((mtm * 100) / totalInvestedAmount)

    return totalInvestedAmount, totalInvestedAmountPercentage, totalCurrentAmount, totalCurrentAmountPercentage, netPnl, netPnlPercentage, realisedPnl, realisedPnlPercentage, mtm, mtmPercentage


def setup_and_append(logFileFolder, values_to_append):
    if not os.path.exists(logFileFolder):
        os.makedirs(logFileFolder)
    file_path = os.path.join(logFileFolder, "DataNotFind.txt")
    with open(file_path, 'a') as file:
        file.write(values_to_append + '\n')

def algoLoggerSetup(algoName):
    logFileFolder = f'/root/liveAlgos/algoLogs/{algoName}'
    try:
        if not os.path.exists(logFileFolder):
            os.makedirs(logFileFolder)
    except Exception as e:
        print(e)
    
    jsonFileFolder = f'/root/liveAlgos/algoJson/{algoName}'
    try:
        if not os.path.exists(jsonFileFolder):
            os.makedirs(jsonFileFolder)
    except Exception as e:
        print(e)
    return logFileFolder,jsonFileFolder

def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logging.basicConfig(level=level, filemode='a', force=True)
    return logger

def createPortfolioList(file_path):
    with open(file_path, 'r') as file:
        stocks = [line.strip() for line in file if line.strip()]
    return stocks

def createSubPortfoliosList(stock_list, num_batches):
    batch_size = len(stock_list) // num_batches
    remainder = len(stock_list) % num_batches

    batches = []
    start = 0
    for i in range(num_batches):
        end = start + batch_size + (1 if i < remainder else 0)
        batches.append(stock_list[start:end])
        start = end
    return batches

def combineClosePnlCSV():
    closeCsvDir = fileDir["closedPositions"]
    if not os.listdir(closeCsvDir):
        return
    csvFiles = [file for file in os.listdir(closeCsvDir) if file.endswith(".csv")]
    closedPnl = pd.concat([pd.read_csv(os.path.join(closeCsvDir, file)) for file in csvFiles])
    if closedPnl.empty:
        return None
    if not is_datetime64_any_dtype(closedPnl["Key"]):
        closedPnl["Key"] = pd.to_datetime(closedPnl["Key"])
    if not is_datetime64_any_dtype(closedPnl["ExitTime"]):
        closedPnl["ExitTime"] = pd.to_datetime(closedPnl["ExitTime"])
    if "Unnamed: 0" in closedPnl.columns:
        closedPnl.drop(columns=["Unnamed: 0"], inplace=True)

    closedPnl.sort_values(by=["Key"], inplace=True)
    closedPnl.reset_index(inplace=True, drop=True)

    closedPnl.to_csv(f"{fileDir['baseJson']}/closePnl.csv", index=False)
    closedPnl[closedPnl["ExitTime"].dt.date == datetime.now().date()].to_csv(
        f"{fileDir['closedPositionsLogs']}/closePnl_{datetime.now().date().__str__()}.csv", index=False)

    return closedPnl

def create_dir_if_not_exists(dir_path):
    """Helper function to create directories if they do not exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

def writeJson1(key, value):
    file_path = f"{fileDir['jsonValue']}/data.json"
    jsonDict = readJson()
    if key in jsonDict:
        print(f"Key '{key}' already exists in the JSON file. Skipping write.")
        return
    jsonDict[key] = value
    with open(file_path, 'w') as json_file:
        json.dump(jsonDict, json_file, indent=4)
        print(f"Key '{key}' added successfully.")

def readJson(key=None):
    file_path = f"{fileDir['jsonValue']}/data.json"
    """Reads the single JSON file and returns data or a specific key."""
    create_dir_if_not_exists(os.path.dirname(file_path))

    if not os.path.exists(file_path):
        initial_data = {
            'amountPerTrade': 30000,
            'TotalTradeCanCome': 50,
        }
        with open(file_path, 'w') as json_file:
            json.dump(initial_data, json_file, indent=4)
        return initial_data

    try:
        with open(file_path, 'r') as json_file:
            jsonDict = json.load(json_file)
        if key:
            return jsonDict.get(key, 50)
        return jsonDict
    except (json.JSONDecodeError, IOError):
        return {}

def writeJson(key, value):

    file_path = f"{fileDir['jsonValue']}/data.json"
    jsonDict = readJson()
    jsonDict[key] = value
    with open(file_path, 'w') as json_file:
        json.dump(jsonDict, json_file, indent=4)

def combineOpenPnlCSV():
    openCsvDir = fileDir["openPositions"]
    if not os.listdir(openCsvDir):
        return pd.DataFrame()
    csvFiles = [file for file in os.listdir(openCsvDir) if file.endswith(".csv")]
    if not csvFiles:
        return pd.DataFrame()
    data_frames = []
    for file in csvFiles:
        file_path = os.path.join(openCsvDir, file)
        if os.stat(file_path).st_size == 0:
            print(f"Skipping empty file: {file_path}")
            continue
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                print(f"Warning: File {file_path} is empty.")
                continue
            data_frames.append(df)
        except pd.errors.EmptyDataError:
            print(f"Error: No columns in {file_path}")
        except Exception as e:
            print(f"Error reading {file_path}: {str(e)}")
    if not data_frames:
        return pd.DataFrame()
    openPnl = pd.concat(data_frames, ignore_index=True)
    if "EntryTime" in openPnl.columns and not is_datetime64_any_dtype(openPnl["EntryTime"]):
        openPnl["EntryTime"] = pd.to_datetime(openPnl["EntryTime"], errors="coerce")
    if "Unnamed: 0" in openPnl.columns:
        openPnl.drop(columns=["Unnamed: 0"], inplace=True)
    openPnl.sort_values(by=["EntryTime"], inplace=True)
    openPnl.reset_index(inplace=True, drop=True)
    openPnl.to_csv(f"{fileDir['baseJson']}/openPnl.csv", index=False)
    openPnl[openPnl["EntryTime"].dt.date == datetime.now().date()].to_csv(
        f"{fileDir['openPositionsLogs']}/openPnl_{datetime.now().date().__str__()}.csv", index=False)
    
    return openPnl

class Stock:
    def __init__(self, stockName):
        self.stockName = stockName

        self.openPnl = pd.DataFrame(columns=["EntryTime", "Symbol", "EntryPrice", "CurrentPrice", "Quantity", "PositionStatus", "Pnl"])
        self.closedPnl = pd.DataFrame(columns=["Key", "ExitTime", "Symbol", "EntryPrice", "ExitPrice", "Quantity", "PositionStatus", "Pnl", "ExitType"])

        stockLogDir = f"{fileDir['stockLogs']}/{self.stockName}"
        os.makedirs(stockLogDir, exist_ok=True)
        self.stockLogger = setup_logger(self.stockName, f"{stockLogDir}/log_{datetime.now().replace(microsecond=0)}.log")
        self.stockLogger.propagate = False

        self.readOpenPnlCsv()
        self.readClosePnlCsv()

        self.data_not_available = 0
        self.realizedPnl = 0
        self.unrealizedPnl = 0
        self.netPnl = 0

    def readOpenPnlCsv(self):
        openPnlCsvFilePath = f"{fileDir['openPositions']}/{self.stockName}_openPositions.csv"

        if os.path.exists(openPnlCsvFilePath):
            openPnlCsvDf = pd.read_csv(openPnlCsvFilePath)

            if 'Unnamed: 0' in openPnlCsvDf.columns:
                openPnlCsvDf.drop(columns=['Unnamed: 0'], inplace=True)

            self.openPnl = pd.concat([self.openPnl, openPnlCsvDf])

            if not is_datetime64_any_dtype(self.openPnl["EntryTime"]):
                self.openPnl["EntryTime"] = pd.to_datetime(self.openPnl["EntryTime"])

            self.stockLogger.info("OpenPnl CSV read successfully.")
        else:
            self.stockLogger.info("OpenPnl CSV not found.")

    def writeOpenPnlCsv(self):
        self.openPnl.to_csv(f"{fileDir['openPositions']}/{self.stockName}_openPositions.csv")

    def readClosePnlCsv(self):
        closePnlCsvFilePath = f"{fileDir['closedPositions']}/{self.stockName}_closedPositions.csv"

        if os.path.exists(closePnlCsvFilePath):
            closePnlCsvDf = pd.read_csv(closePnlCsvFilePath)

            if 'Unnamed: 0' in closePnlCsvDf.columns:
                closePnlCsvDf.drop(columns=['Unnamed: 0'], inplace=True)

            self.closedPnl = pd.concat([self.closedPnl, closePnlCsvDf])

            if not is_datetime64_any_dtype(self.closedPnl["Key"]):
                self.closedPnl["Key"] = pd.to_datetime(self.closedPnl["Key"])
            if not is_datetime64_any_dtype(self.closedPnl["ExitTime"]):
                self.closedPnl["ExitTime"] = pd.to_datetime(
                    self.closedPnl["ExitTime"])

            self.stockLogger.info("ClosedPnl CSV read successfully.")
        else:
            self.stockLogger.info("ClosedPnl CSV not found.")

    def writeClosePnlCsv(self):
        self.closedPnl.to_csv(f"{fileDir['closedPositions']}/{self.stockName}_closedPositions.csv")

    def entryOrder(self, instrumentID, symbol, entryPrice, quantity, orderSide, extraCols=None):
        if orderSide == "BUY":
            limitPrice = getBuyLimitPrice(entryPrice, float(config.get('inputParameters', 'extraPercent')))
        else:
            limitPrice = getSellLimitPrice(entryPrice, float(config.get('inputParameters', 'extraPercent')))

        postOrderToDbLIMITStock(exchangeSegment="NSECM",
            productType='CNC',
            algoName=algoName,
            isLive=True if config.get('inputParameters', 'islive') == "True" else False,
            exchangeInstrumentID=instrumentID,
            orderSide=orderSide,
            orderQuantity=quantity,
            limitPrice=limitPrice,
            upperPriceLimit=(float(config.get('inputParameters', 'upperPriceLimitPercent')) * limitPrice) if orderSide == "BUY" else 0,
            lowerPriceLimit=0 if orderSide == "BUY" else (float(config.get('inputParameters', 'lowerPriceLimitPercent')) * limitPrice),
            timePeriod=int(config.get('inputParameters', 'timeLimitOrder')),
            extraPercent=float(config.get('inputParameters', 'extraPercent')),
        )

        newTrade = pd.DataFrame({
            "EntryTime": datetime.now(),
            "Symbol": symbol,
            "EntryPrice": entryPrice,
            "CurrentPrice": entryPrice,
            "Quantity": quantity,
            "PositionStatus": 1 if orderSide == "BUY" else -1,
            "Pnl": 0
        }, index=[0])

        if extraCols:
            for key in extraCols.keys():
                newTrade[key] = extraCols[key]

        self.openPnl = pd.concat([self.openPnl, newTrade], ignore_index=True)
        self.openPnl.reset_index(inplace=True, drop=True)

        self.writeOpenPnlCsv()
        self.stockLogger.info(f'ENTRY {orderSide}: {symbol} @ {entryPrice} '.upper() + f'Qty- {quantity}')

    def exitOrder(self, index, instrumentID, exitPrice, exitType):
        trade_to_close = self.openPnl.loc[index].to_dict()

        if trade_to_close['PositionStatus'] == 1:
            limitPrice = getBuyLimitPrice(exitPrice, float(config.get('inputParameters', 'extraPercent')))
            orderSide = "SELL"
        else:
            limitPrice = getSellLimitPrice(exitPrice, float(config.get('inputParameters', 'extraPercent')))
            orderSide = "BUY"

        postOrderToDbLIMITStock(
            exchangeSegment="NSECM",
            productType='CNC',
            algoName=algoName,
            isLive=True if config.get('inputParameters', 'islive') == "True" else False,
            exchangeInstrumentID=instrumentID,
            orderSide=orderSide,
            orderQuantity=trade_to_close['Quantity'],
            limitPrice=limitPrice,
            upperPriceLimit=0 if trade_to_close['PositionStatus'] == 1 else (float(config.get('inputParameters', 'upperPriceLimitPercent')) * limitPrice),
            lowerPriceLimit=(float(config.get('inputParameters', 'lowerPriceLimitPercent')) * limitPrice) if trade_to_close['PositionStatus'] == 1 else 0,
            timePeriod=int(config.get('inputParameters', 'timeLimitOrder')),
            extraPercent=float(config.get('inputParameters', 'extraPercent')),)

        self.openPnl.drop(index=index, inplace=True)

        trade_to_close['Key'] = trade_to_close['EntryTime']
        trade_to_close['ExitTime'] = datetime.now()
        trade_to_close['ExitPrice'] = exitPrice
        trade_to_close['Pnl'] = (trade_to_close['ExitPrice'] - trade_to_close['EntryPrice']) * trade_to_close['Quantity'] * trade_to_close['PositionStatus']
        trade_to_close['ExitType'] = exitType

        for col in self.openPnl.columns:
            if col not in self.closedPnl.columns:
                del trade_to_close[col]

        self.closedPnl = pd.concat([self.closedPnl, pd.DataFrame([trade_to_close])], ignore_index=True)
        self.closedPnl.reset_index(inplace=True, drop=True)

        percentPnl = round(((trade_to_close['ExitPrice'] - trade_to_close['EntryPrice'])*trade_to_close['PositionStatus'])*100/trade_to_close['EntryPrice'], 1)
        percentPnl = "+" + str(percentPnl) if percentPnl > 0 else "-" + str(abs(percentPnl))

        profit = round(trade_to_close['Pnl'])
        if profit > 0:
            profit = f"+{round(profit)}"

        infoMessage(algoName=algoName, message=f'Exit {exitType}: {trade_to_close["Symbol"]} @ {exitPrice} [{percentPnl}%]'.upper() + f' PnL: {profit}')

        self.writeOpenPnlCsv()
        self.writeClosePnlCsv()
        self.stockLogger.info(f'Exit {exitType}: {trade_to_close["Symbol"]} @ {exitPrice}'.upper() + f'PnL: {profit}')


    def pnlCalculator(self):
        if not self.openPnl.empty:
            self.openPnl["PositionStatus"] = self.openPnl["PositionStatus"].fillna(0).astype(int)

            self.openPnl["Pnl"] = (self.openPnl["CurrentPrice"] - self.openPnl["EntryPrice"]) * self.openPnl["Quantity"] * self.openPnl["PositionStatus"]
            self.unrealizedPnl = self.openPnl["Pnl"].sum()

            self.writeOpenPnlCsv()
        else:
            self.unrealizedPnl = 0

        if not self.closedPnl.empty:
            self.realizedPnl = self.closedPnl["Pnl"].sum()
        else:
            self.realizedPnl = 0

        self.netPnl = self.unrealizedPnl + self.realizedPnl


class Strategy:
    def __init__(self):
        self.idMap = {}
        self.symListConn = None
        self.candle_1d = {}
        self.candle_1Min = {}
        self.stockDict = {}
        self.breakEven = {}

    def rename_col(self, df):
        df["ti"] = df.index
        df["o"] = df["Open"]
        df["h"] = df["High"]
        df["l"] = df["Low"]
        df["c"] = df["Close"]
        df["v"] = df["Volume"]
        df["sym"] = df["Symbol"]
        df["date"] = pd.to_datetime(df.index, unit='s')

        del df["Open"]
        del df["High"]
        del df["Low"]
        del df["Close"]
        del df["Volume"]

    def updateOpenPositionsInfra(self):
        combinedOpenPnl = pd.DataFrame(columns=["EntryTime", "Symbol", "EntryPrice", "CurrentPrice", "Quantity", "PositionStatus", "Pnl"])
        for stock in self.stockDict.keys():
            combinedOpenPnl = pd.concat([combinedOpenPnl, self.stockDict[stock].openPnl], ignore_index=True)
        combinedOpenPnl['EntryTime'] = combinedOpenPnl['EntryTime'].astype(str)
        positionUpdator(combinedOpenPnl, 'Process 1', algoName)

    def run_strategy(self, portfolio):
        try:
            subscribe_list = set(portfolio)
            for stock in portfolio:
                if stock not in self.stockDict:
                    self.stockDict[stock] = Stock(stock)
                    self.breakEven[stock] = False
                    writeJson1(f"breakEven{stock}", self.breakEven[stock])
                    self.candle_1d[stock] = {'last_candle_time': 0, 'df': None}
                    self.candle_1Min[stock] = {'last_candle_time': 0, 'df': None}
                subscribe_list.update(self.stockDict[stock].openPnl["Symbol"].unique().tolist())

            strategyLogger.info(f"Subscribing to the following symbols: {subscribe_list}")
            data, self.idMap, self.symListConn = reconnect(self.idMap, list(subscribe_list))

            portfolio = createSubPortfoliosList(portfolio, int(config.get('inputParameters', 'maxNumberOfThreads')))
            lastPrintHour = False
            algoStart = True
            while True:
                current_time = datetime.now().time()
                if (current_time < time(9, 16)) or (current_time > time(15, 30)):
                    sleep(1)
                    continue
                for subPortfolio in portfolio:
                    self.exec_strategy(subPortfolio)

                currentDatetime = datetime.now()
                currentTime = currentDatetime.time()
                currentHour = datetime.now().hour
                sleep(1)
                self.updateOpenPositionsInfra()
                updateCurrentPrices(self)
                combineClosePnlCSV()
                combineOpenPnlCSV()

                if (algoStart == True):
                    lastPrintHour = currentHour
                    try:
                        algoStart = False
                        max_drawdown_portfolio = portfolioValue()
                        totalInvestedAmount, totalInvestedAmountPercentage, totalCurrentAmount, totalCurrentAmountPercentage, netPnl, netPnlPercentage, realisedPnl, realisedPnlPercentage, mtm, mtmPercentage = algoInfoMessage()
                        AlgoStartDate, AlgoStartDateNiftyClose, quantityNifty, niftyMTM, netProfit, niftyMtmPercentage, niftynetProfitPercentage, max_drawdown = niftyFifty()
                        infoMessage(algoName=algoName, message=f"INVESTED: {round(totalInvestedAmount)}[{round(totalInvestedAmountPercentage, 1)}%] | CURRENT: {round(totalCurrentAmount)}[{round(totalCurrentAmountPercentage, 1)}%] | TOTAL: 1500000")
                        infoMessage(algoName=algoName,message=(f"START DATE: {AlgoStartDate} | INDEX START VALUE: {round(AlgoStartDateNiftyClose, 2)} | Qty: {round(quantityNifty)}"))    #| NIFTY CURRENT VALUE: {round(totalCurrentAmount, 2)} | max_drawdown: {round(max_drawdown, 2)}% | portfolio_drawdown: -{round(max_drawdown_portfolio, 2)}%
                        infoMessage(algoName=algoName, message=f"ALGO: [MTM: {round(mtm)}[{round(mtmPercentage, 1)}%] | NET P/L: {round(netPnl)}[{round(netPnlPercentage, 1)}%]  | REALISED: {round(realisedPnl)}[{round(realisedPnlPercentage, 1)}%] | MAX DD: [-{round(max_drawdown_portfolio, 2)}%]]")
                        infoMessage(algoName=algoName,message=(f"NIFTY: [MTM: {round(niftyMTM)}[{round(niftyMtmPercentage, 1)}%] | "f"NET P/L: {round(netProfit)}[{round(niftynetProfitPercentage, 1)}%] | MAX DD: [{round(max_drawdown, 2)}%]]"))
                        if (time(9, 20) < currentTime < time(9, 25)) or (time(15, 21) < currentTime < time(15, 29)):
                            sleep(300)
                    except Exception as e:
                        infoMessage(algoName=algoName, message=f"Error: {str(e)}")

                # if algoStart == True or datetime.now().hour != lastPrintHour:
                #     lastPrintHour = datetime.now().hour
                #     try:
                #         algoStart = False
                #         totalInvestedAmount, totalInvestedAmountPercentage, totalCurrentAmount, totalCurrentAmountPercentage, netPnl, netPnlPercentage, realisedPnl, realisedPnlPercentage, mtm, mtmPercentage  = algoInfoMessage()
                #         infoMessage(algoName=algoName, message=f"INVESTED: {round(totalInvestedAmount)}[{round(totalInvestedAmountPercentage, 1)}%] | CURRENT: {round(totalCurrentAmount)}[{round(totalCurrentAmountPercentage, 1)}%] | TOTAL: 1500000")
                #         infoMessage(algoName=algoName, message=f"MTM: {round(mtm)}[{round(mtmPercentage, 1)}%] | NET P/L: {round(netPnl)}[{round(netPnlPercentage, 1)}%]  | REALISED: {round(realisedPnl)}[{round(realisedPnlPercentage, 1)}%]")
                #         if (time(9, 20) < currentTime < time(9, 25)) or (time(15, 21) < currentTime < time(15, 29)):
                #             sleep(300)
                #     except Exception as e:
                #         infoMessage(algoName=algoName, message=f"Error: {str(e)}")

        except Exception as err:
            errorMessage(algoName=algoName, message=str(err))
            strategyLogger.exception(str(err))

    def exec_strategy(self, subPortfolio):
        try:
            currentDatetime = datetime.now()
            currentTime = currentDatetime.time()
            currentDate = currentDatetime.date()
            current_minute = datetime.now().minute
            # print(currentDate)

            # algoName = config.get('inputParameters', 'algoName')
            # logFileFolder, jsonFileFolder = algoLoggerSetup(algoName)

            for stock in subPortfolio:
                stock_logger = self.stockDict[stock].stockLogger

                try:
                    currentPrice = dataFetcher([self.idMap[stock]])[self.idMap[stock]]
                    stock_logger.info(f'[Tick] => Current Price: {currentPrice}')
                except Exception as e:
                    stock_logger.error(f"Error fetching current price for {stock}: {e}")
                    continue

                if currentPrice is None:
                    infoMessage(algoName=algoName, message=f"Data not found for: {stock}")
                    strategyLogger.info(f"Data not found for: {stock}")
                    continue

                try:
                    df_1d, candle_flag_1d, last_candle_time_1d = OHLCDataFetch(
                        stock, currentDatetime.timestamp(), self.candle_1d[stock]['last_candle_time'], 'd', 
                        150, self.candle_1d[stock]['df'], stock_logger)
                    self.candle_1d[stock]['df'], self.candle_1d[stock]['last_candle_time'] = df_1d, last_candle_time_1d
                    resample_data(df_1d, 'd')
                    self.rename_col(df_1d)
                except Exception as e:
                    stock_logger.error(f"Error fetching daily OHLC data for {stock}: {e}")
                    continue

                try:
                    df_1Min, candle_flag_1Min, last_candle_time_1Min = OHLCDataFetch(
                        stock, currentDatetime.timestamp(), self.candle_1Min[stock]['last_candle_time'], 1, 
                        5, self.candle_1Min[stock]['df'], stock_logger)
                    if candle_flag_1Min and df_1Min is not None:
                        self.candle_1Min[stock]['df'], self.candle_1Min[stock]['last_candle_time'] = df_1Min, last_candle_time_1Min
                        self.rename_col(df_1Min)
                except Exception as e:
                    stock_logger.error(f"Error fetching 1-minute OHLC data for {stock}: {e}")
                    continue

                try:
                    df_1d = pd.concat([df_1d, df_1Min.tail(1)], ignore_index=False)
                    df_1d['rsi'] = talib.RSI(df_1d['c'], timeperiod=(int(config.get('technicalIndicatorParameters', 'rsiTimePeriod'))))
                    stock_logger.info(f"[1d] => Close: {df_1d.at[df_1d.index[-1], 'c']}")
                    stock_logger.info(f"RSI: {stock},{df_1d.at[df_1d.index[-1], 'rsi']}")
                    # infoMessage(algoName=algoName, message=f"RSI: {df_1d.at[df_1d.index[-1], 'rsi']}")
                    # strategyLogger.info(f"EntryRSI: {df_1d.at[df_1d.index[-1], 'rsi']}")
                except Exception as e:
                    stock_logger.error(f"Error processing RSI for {stock}: {e}")
                    continue

                try:
                    self.breakEven[stock] = readJson(f"breakEven{stock}")
                    rsi_current, rsi_previous = df_1d.at[df_1d.index[-1], 'rsi'], df_1d.at[df_1d.index[-2], 'rsi']
                    prev_day_c = df_1d.at[df_1d.index[-2], 'c']
                    currentTime = pd.Timestamp.now().time()

                    if not self.stockDict[stock].openPnl.empty and currentTime < time(9,25):
                        for index, row in self.stockDict[stock].openPnl.iterrows():

                            if (row['EntrycurrentDate'] != currentDate) and row['entryTypeee'] == "one" and currentTime >= time(9, 20):
                                self.stockDict[stock].openPnl.at[index, "entryTypeee"] = "Done"

                            if (row['EntrycurrentDate'] != currentDate) and row['entryTypeee'] == "one" and currentTime >= time(9, 16) and currentTime <= time(9, 20) and rsi_previous < int(config["inputParameters"]["EntryTimeRsi"]):
                                self.breakEven[stock] = False
                                writeJson(f"breakEven{stock}", self.breakEven[stock])
                                self.stockDict[stock].exitOrder(index, self.idMap[row['Symbol']], row['CurrentPrice'], "DailyNextDayExit")
                                # infoMessage(algoName=algoName, message=f"Exit: {row['Symbol']} - DailyNextDayExit")
                                strategyLogger.info(f"Exit: {row['Symbol']} - DailyNextDayExit, {currentDatetime}")

                    current_time = datetime.now().time()
                    current_minute = datetime.now().minute
                    current_hour = datetime.now().hour
                    hourIn = [10,11,12,13,14,15]
                    if not ((current_time >= time(10,15) and current_time < time(15,19) and current_hour in hourIn and current_minute > 14 and current_minute < 16) or (current_time >= time(15,15))):
                        continue

                    if not self.stockDict[stock].openPnl.empty:
                        for index, row in self.stockDict[stock].openPnl.iterrows():

                            if currentTime >= time(15, 15) and currentTime < time(15, 18):

                                if (row['EntrycurrentDate'] == currentDate) and row['entryTypeee'] == "two" and rsi_current < int(config["inputParameters"]["EntryTimeRsi"]):
                                    self.breakEven[stock] = False
                                    writeJson(f"breakEven{stock}", self.breakEven[stock])
                                    self.stockDict[stock].exitOrder(index, self.idMap[row['Symbol']], row['CurrentPrice'], "DailyIntradayExit")
                                    # infoMessage(algoName=algoName, message=f"Exit: {row['Symbol']} - DailyIntradayExit")
                                    strategyLogger.info(f"Exit: {row['Symbol']} - DailyIntradayExit, {currentDatetime}")

                                elif self.breakEven[stock] != True and currentPrice < row['EntryPrice'] and rsi_current < int(config["inputParameters"]["breakevenExitRsi"]):
                                    self.breakEven[stock] = True
                                    writeJson(f"breakEven{stock}", self.breakEven[stock])
                                    infoMessage(algoName=algoName, message=f"Breakeven Triggered for {row['Symbol']}")
                                    strategyLogger.info(f"Breakeven Triggered for {row['Symbol']}, {currentDatetime}")

                                if self.breakEven[stock] and currentPrice > row['EntryPrice']:
                                    if rsi_current < int(config["inputParameters"]["EntryTimeRsi"]):
                                        self.breakEven[stock] = False
                                        writeJson(f"breakEven{stock}", self.breakEven[stock])
                                        self.stockDict[stock].exitOrder(index, self.idMap[row['Symbol']], row['CurrentPrice'], "Breakeven")
                                        infoMessage(algoName=algoName, message=f"Exit: {row['Symbol']} - Breakeven")
                                        strategyLogger.info(f"Exit: {row['Symbol']} - Breakeven, {currentDatetime}")

                                    elif rsi_current > int(config["inputParameters"]["EntryTimeRsi"]):
                                        self.breakEven[stock] = False
                                        writeJson(f"breakEven{stock}", self.breakEven[stock])
                                        infoMessage(algoName=algoName, message=f"Position_continue {row['Symbol']}")
                                        strategyLogger.info(f"Position_continue {row['Symbol']}, {currentDatetime}")

                                elif not self.breakEven[stock] and currentPrice > row['EntryPrice'] and rsi_current < int(config["inputParameters"]["RsiTargetUsingRsi"]):
                                    self.stockDict[stock].exitOrder(index, self.idMap[row['Symbol']], row['CurrentPrice'], "TargetHit")
                                    PnLL = (row['CurrentPrice'] - row['EntryPrice']) * row['Quantity']
                                    amountPerTrade = readJson("amountPerTrade")
                                    amountPerTrade += PnLL
                                    writeJson("amountPerTrade", amountPerTrade)
                                    infoMessage(algoName=algoName, message=f"NowamountPerTrade: {round(amountPerTrade)}")
                                    strategyLogger.info(f"NowamountPerTrade: {round(amountPerTrade)}, {currentDatetime}")

                    self.stockDict[stock].pnlCalculator()

                    nowTotalTrades = len(combineOpenPnlCSV())
                    TotalTradeCanCome = readJson("TotalTradeCanCome")
                    amountPerTrade = readJson("amountPerTrade")
                    BufferAmount = amountPerTrade // 2

                    if self.stockDict[stock].openPnl.empty and nowTotalTrades < TotalTradeCanCome:
                        quantity = amountPerTrade // currentPrice
                        if (amountPerTrade - (quantity * currentPrice) + BufferAmount) > currentPrice:
                            quantity += 1

                        entry_condition_1 = (time(15, 15) <= currentTime < time(15, 16)) and (rsi_current > int(config["inputParameters"]["EntryTimeRsi"])) and (rsi_current > rsi_previous)
                        entry_condition_2 = (time(10, 15) <= currentTime < time(14, 20)) and (rsi_current > int(config["inputParameters"]["EntryTimeRsi"])) and (rsi_previous < int(config["inputParameters"]["EntryTimeRsi"]))

                        if entry_condition_1:
                            nowTotalTrades += 1
                            self.breakEven[stock] = False
                            writeJson(f"breakEven{stock}", self.breakEven[stock])
                            self.stockDict[stock].entryOrder(self.idMap[stock], stock, currentPrice, quantity, "BUY", {"EntrycurrentDate": currentDate, "prev_day_c": prev_day_c, "entryTypeee": "one"})
                            prev_rsi = round(rsi_current, 2)
                            stock_logger.info(f'Entry BUY: {stock} @ {currentPrice}, Qty: {quantity}, Amount: {round(currentPrice * quantity)}')
                            infoMessage(algoName=algoName, message=f'{nowTotalTrades} of {TotalTradeCanCome}, RSI: {prev_rsi} Entry BUY: {stock} @ {currentPrice}, Qty: {quantity}, Amount: {round(currentPrice * quantity)}')
                            strategyLogger.info(f'{nowTotalTrades} of {TotalTradeCanCome}, RSI: {prev_rsi} Entry BUY: {stock} @ {currentPrice}, Qty: {quantity}, Amount: {round(currentPrice * quantity)}, entryTypeee: one, {currentDatetime}')

                        elif entry_condition_2:
                            nowTotalTrades += 1
                            self.breakEven[stock] = False
                            writeJson(f"breakEven{stock}", self.breakEven[stock])
                            self.stockDict[stock].entryOrder(self.idMap[stock], stock, currentPrice, quantity, "BUY", {"EntrycurrentDate": currentDate, "prev_day_c": prev_day_c, "entryTypeee": "two"})
                            prev_rsi = round(rsi_current, 2)
                            stock_logger.info(f'Entry BUY: {stock} @ {currentPrice}, Qty: {quantity}, Amount: {round(currentPrice * quantity)}')
                            infoMessage(algoName=algoName, message=f'{nowTotalTrades} of {TotalTradeCanCome}, RSI: {prev_rsi} Entry BUY: {stock} @ {currentPrice}, Qty: {quantity}, Amount: {round(currentPrice * quantity)}')
                            strategyLogger.info(f'{nowTotalTrades} of {TotalTradeCanCome}, RSI: {prev_rsi} Entry BUY: {stock} @ {currentPrice}, Qty: {quantity}, Amount: {round(currentPrice * quantity)}, entryTypeee: two, {currentDatetime}')

                except Exception as err:
                    errorMessage(algoName=algoName, message=str(err))
                    strategyLogger.exception(str(err))

        except Exception as err:
            errorMessage(algoName=algoName, message=str(err))
            strategyLogger.exception(str(err))


class algoLogic:
    def mainLogic(self, mpName):
        try:
            global config
            config = ConfigParser()
            config.read('config.ini')

            global algoName
            algoName = config.get('inputParameters', 'algoName')
            global fileDir

            logFileFolder, jsonFileFolder = algoLoggerSetup(algoName)

            fileDir = {
                "baseJson": f"{jsonFileFolder}/json",
                "openPositions": f"{jsonFileFolder}/json/OpenPositions",
                "closedPositions": f"{jsonFileFolder}/json/ClosedPositions",
                "baseLog": f"{logFileFolder}/logs",
                "strategyLogs": f"{logFileFolder}/logs/StrategyLog",
                "stockLogs": f"{logFileFolder}/logs/StrategyLog/Stocks",
                "jsonValue": f"{jsonFileFolder}/jsonss/jsonFiles",
                "openPositionsLogs": f"{logFileFolder}/StrategyLog/OpenPositions",
                "closedPositionsLogs": f"{logFileFolder}/StrategyLog/ClosePositions",

            }
            for keyDir in fileDir.keys():
                os.makedirs(fileDir[keyDir], exist_ok=True)

            global strategyLogger
            strategyLogger = setup_logger(algoName, f"{fileDir['strategyLogs']}/log_{datetime.now().replace(microsecond=0)}.log")
            strategyLogger.propagate = False

            portfolio = createPortfolioList(config.get('strategyParameters', 'portfolioList'))
            strategyLogger.info(f"PORTFOLIO USED: {portfolio}")

            strategyObj = Strategy()
            strategyObj.run_strategy(portfolio)

        except Exception as err:
            errorMessage(algoName=algoName, message=str(Exception(err)))
            strategyLogger.exception(str(Exception(err)))

if __name__ == "__main__":
    algoLogicObj = algoLogic()
    algoLogicObj.mainLogic("")