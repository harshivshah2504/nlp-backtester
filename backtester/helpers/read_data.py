import ftplib
import pandas as pd
from io import BytesIO

class FTPClient:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        self.ftp = None

    def connect(self):
        self.ftp = ftplib.FTP(self.server)
        self.ftp.login(user=self.username, passwd=self.password)
        print("FTP connection established")

    def disconnect(self):
        if self.ftp:
            self.ftp.quit()
            print("FTP connection closed")

    def list_directory(self, path="."):
        if self.ftp:
            try:
                self.ftp.cwd(path)
                print(f"Current working directory: {self.ftp.pwd()}")
            except ftplib.error_perm as e:
                print(f"Failed to change directory to {path}: {e}")
                return []
            files = []
            self.ftp.retrlines('LIST', files.append)
            return files
        else:
            raise ConnectionError("Not connected to FTP server")

    def retrieve_csv(self, remote_path, local_path=None):
        if self.ftp:
            bio = BytesIO()
            try:
                self.ftp.retrbinary(f'RETR {remote_path}', bio.write)
                bio.seek(0)
                if local_path:
                    with open(local_path, 'wb') as f:
                        f.write(bio.getbuffer())
                    print(f"File saved locally at {local_path}")
                df = pd.read_csv(bio)
                return df
            except ftplib.error_perm as e:
                print(f"Failed to retrieve {remote_path}: {e}")
                return None
        else:
            raise ConnectionError("Not connected to FTP server")

    def fetch_historical_data(self, market, exchange, symbol, timeframe):
        path = f"{market}/{exchange}/{symbol}/{symbol}_{exchange}_{timeframe}.csv"
        print(f"Fetching data from: {path}")
        return self.retrieve_csv(path)

    def fetch_all_symbols_data(self, market, exchange, timeframe):
        path = f"{market}/{exchange}"
        print(f"Attempting to access path: {path}")
        symbols = self.list_directory(path)
        if not symbols:
            print(f"No symbols found in {path}")
            return {}

        all_data = {}
        for symbol in symbols:
            symbol_name = " ".join(symbol.split()[3:])  
            file_path = f"{symbol_name}/{symbol_name}_{exchange}_{timeframe}.csv"
            print(f"Attempting to retrieve CSV from: {file_path}")
            df = self.retrieve_csv(file_path)
            if df is not None:
                all_data[symbol_name] = df
            else:
                print(f"Data for {symbol_name} at {timeframe} timeframe not found.")
        return all_data

    def fetch_all_symbols_in_market(self, market):
        path = f"{market}"
        print(f"Path: {path}")
        exchanges = self.list_directory(path)
        if not exchanges:
            print(f"No exchanges found in {path}")
            return {}

        all_symbols = {}
        for exchange in exchanges:
            exchange_name = " ".join(exchange.split()[3:])  
            symbols_path = f"{exchange_name}"
            print(f"Symbols path: {symbols_path}")
            symbols = self.list_directory(symbols_path)
            if not symbols:
                print(f"No symbols found in {symbols_path}")
                continue
            all_symbols[exchange_name] = [" ".join(symbol.split()[3:]) for symbol in symbols]
        return all_symbols
    
    
import ftplib
import pandas as pd
from io import BytesIO

class FTPClient:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        self.ftp = None

    def connect(self):
        self.ftp = ftplib.FTP(self.server)
        self.ftp.login(user=self.username, passwd=self.password)
        print("FTP connection established")

    def disconnect(self):
        if self.ftp:
            self.ftp.quit()
            print("FTP connection closed")

    def list_directory(self, path="."):
        if self.ftp:
            try:
                self.ftp.cwd(path)
                print(f"Current working directory: {self.ftp.pwd()}")
            except ftplib.error_perm as e:
                print(f"Failed to change directory to {path}: {e}")
                return []
            files = []
            self.ftp.retrlines('LIST', files.append)
            return files
        else:
            raise ConnectionError("Not connected to FTP server")

    def retrieve_csv(self, remote_path, local_path=None):
        if self.ftp:
            bio = BytesIO()
            try:
                self.ftp.retrbinary(f'RETR {remote_path}', bio.write)
                bio.seek(0)
                if local_path:
                    with open(local_path, 'wb') as f:
                        f.write(bio.getbuffer())
                    print(f"File saved locally at {local_path}")
                df = pd.read_csv(bio)
                return df
            except ftplib.error_perm as e:
                print(f"Failed to retrieve {remote_path}: {e}")
                return None
        else:
            raise ConnectionError("Not connected to FTP server")

    def fetch_historical_data(self, market, exchange, symbol, timeframe):
        path = f"{market}/{exchange}/{symbol}/{symbol}_{exchange}_{timeframe}.csv"
        print(f"Fetching data from: {path}")
        return self.retrieve_csv(path)

    def fetch_all_symbols_data(self, market, exchange, timeframe):
        path = f"{market}/{exchange}"
        print(f"Attempting to access path: {path}")
        symbols = self.list_directory(path)
        if not symbols:
            print(f"No symbols found in {path}")
            return {}

        all_data = {}
        for symbol in symbols:
            symbol_name = " ".join(symbol.split()[3:])  
            # file_path = f"{symbol_name}/{symbol_name}_{exchange}_{timeframe}.csv"
            file_path = f"{symbol_name}/{symbol_name}_{timeframe}.csv"
            print(f"Attempting to retrieve CSV from: {file_path}")
            df = self.retrieve_csv(file_path)
            if df is not None:
                all_data[symbol_name] = df
            else:
                print(f"Data for {symbol_name} at {timeframe} timeframe not found.")
        return all_data

    def fetch_all_symbols_in_market(self, market):
        path = f"{market}"
        print(f"Path: {path}")
        exchanges = self.list_directory(path)
        if not exchanges:
            print(f"No exchanges found in {path}")
            return {}

        all_symbols = {}
        for exchange in exchanges:
            exchange_name = " ".join(exchange.split()[3:])  
            symbols_path = f"{exchange_name}"
            print(f"Symbols path: {symbols_path}")
            symbols = self.list_directory(symbols_path)
            if not symbols:
                print(f"No symbols found in {symbols_path}")
                continue
            all_symbols[exchange_name] = [" ".join(symbol.split()[3:]) for symbol in symbols]
        return all_symbols



# ftp_server = '82.180.146.204'
# ftp_username = 'Administrator'
# ftp_password = '2CentsOptions'

# client = FTPClient(ftp_server, ftp_username, ftp_password)

# markets = ['Crypto']
# exchanges = ['Binance', "ByBit"]
# timeframes = ['1d']

# all_data = {}

# try:
#     for market in markets:
#         # all_data[market] = {}
#         for exchange in exchanges:
#             # all_data[market][exchange] = {}
#             all_data[exchange] = {}
#             for timeframe in timeframes:
#                 print(f"Fetching data for Market: {market}, Exchange: {exchange}, Timeframe: {timeframe}")
#                 client.connect()
#                 data = client.fetch_all_symbols_data(market, exchange, timeframe)
#                 client.disconnect()
#                 # all_data[market][exchange][timeframe] = data
#                 all_data[exchange][timeframe] = data

# finally:
#     pass
