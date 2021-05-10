from datetime import date, datetime
import json

import pandas as pd
import numpy as np

from processor import IndexProcessor
from optimizer import Optimizer
from ds import Portfolio, Stock
from utils import find_in_json, read_json, \
                  write_json, sort_dict, \
                  slice_dict, return_latest_data

class Environment:
    def __init__(self, data, metadata, lookback_period):
        self.data = data
        self.metadata = metadata
        self.dates = list(data.index)
        self.current_date =(-1)
        self.lookback_period = lookback_period
    
    def reset(self):
        self.current_date = (-1)

    def load_next_day(self, agent, bband_margins):
        dayend_prices = self.data[self.data.index == self.dates[self.current_date]]
        dayend_prices = dayend_prices.to_dict(orient='records')[0]

        agent.orders = {}
        agent.order_log = []

        for s in agent.portfolio.stocks:
         
            try:#try:
                ohlc_data = pd.read_csv(s.metadata['OHLC Data Location'])
                ohlc_data['Date'] = pd.to_datetime(ohlc_data['Date']).dt.date
                ohlc_data = ohlc_data[ohlc_data['Date'] == self.dates[self.current_date]]
                ohlc_data = ohlc_data.to_dict(orient='records')[0]

                s.price = dayend_prices[s.ticker]
                s.metadata['Price'] = dayend_prices[s.ticker]
                s.metadata['Value'] = s.metadata['Portfolio Allocation']*s.metadata['Price']

                if(bband_margins):
                    if((s.price <= ohlc_data['Bollinger Band Down']) or (s.price >= ohlc_data['Bollinger Band Up'])):
                        agent.execute_sell(s.ticker, -s.metadata['Portfolio Allocation'], s.price)   
                    elif((s.price <= ohlc_data['Stop Loss']) or (s.price >= ohlc_data['Profit Exit'])):
                        agent.execute_sell(s.ticker, -s.metadata['Portfolio Allocation'], s.price) 

            except IndexError as e:
                print("IndexError for ticker {}".format(s.ticker))
                #print("Price of stock: {}".format(s.price))
                #agent.execute_sell(s.ticker, -s.metadata['Portfolio Allocation'], s.price)



            # except Exception as e:
            #     # print("Exception {} for ticker {} for date {}".format(e, s.ticker, self.dates[self.current_date]))
            #     # continue
            #     agent.execute_sell(s.ticker, -s.metadata['Portfolio Allocation'], s.price)
            
        self.current_date += 1
        return dayend_prices
    
    def load_lookback_data(self, cumulative=True):
        start_cond = (self.data.index > self.dates[self.current_date - self.lookback_period])
        end_cond = (self.data.index <= self.dates[self.current_date])
        if cumulative:
            allocation_data = self.data.loc[end_cond]
        else:
            allocation_data = self.data.loc[start_cond & end_cond]
        return allocation_data

    def is_reallocation_day(self):
        flag = False
        if(self.current_date !=0):
            if(self.current_date % self.lookback_period==0):
                flag=True
        return flag


class Agent:
    def __init__(self, name=None, optimizer=Optimizer(), portfolio_value=1000000, 
                single_day_cash=0.60, **kwargs):
        self.name = name
        self.portfolio = Portfolio()
        self.optimizer = optimizer
        self.optimizer.portfolio = Portfolio()
        self.total_cash = portfolio_value
        self.single_day_cash = single_day_cash
        self.orders = {}
        self.order_log = []
        self.portfolio_logs = []
        self.optimizer_logs = []
        self.exec_order_logs = []
        self.init_portfolio = portfolio_value

        try:
            self.optimizer.optimizer_type = kwargs["optimizer_type"]
        except:
            self.optimizer.optimizer_type = None

        self.optimizer.metadata_loc = kwargs["metadata_loc"] 
    
    def allocate_portfolio(self, lookback_data):
        if(self.total_cash>0):
            self.optimizer.portfolio.reset(self.single_day_cash * self.total_cash)
            self.portfolio.reset(self.single_day_cash * self.total_cash)
            # self.optimizer.portfolio.portfolio_value = self.single_day_cash * self.total_cash
            # self.portfolio.portfolio_value = self.single_day_cash * self.total_cash
            # self.optimizer.portfolio.cash_left = self.single_day_cash * self.total_cash
            # self.portfolio.cash_left = self.single_day_cash * self.total_cash
            self.total_cash -= self.portfolio.portfolio_value

            self.optimizer.close_matrix = lookback_data.dropna(axis=1, how='all')
            try:
                self.optimizer.optimize()
            except Exception as e:
                print("Portfolio Optimization Error: {}".format(e))
                self.optimizer.portfolio = self.portfolio
        
        else:
            self.optimizer.portfolio.reset(0)
            self.portfolio.reset(0)



    def compute_allocation_orders(self):
        portfolio_comp = self.portfolio.discrete_composition
        optimizer_comp = self.optimizer.portfolio.discrete_composition

        self.orders = {}
        if len(self.portfolio.stocks) == 0:
            self.orders = optimizer_comp
        elif (portfolio_comp == optimizer_comp):
            self.orders = {}
        else:
            for k, v in optimizer_comp.items():
                if k in portfolio_comp.keys():
                    if v != portfolio_comp[k]:
                        self.orders[k] = v - portfolio_comp[k]
                self.orders[k] = v
        
    def execute_orders(self, dayend_prices=None):
        self.order_log = []
        for ticker, shares in self.orders.items():
            if shares > 0:
                self.execute_buy(ticker, shares, dayend_prices[ticker])
            elif shares < 0:
                self.execute_sell(ticker, shares, dayend_prices[ticker])
    
    def execute_buy(self, ticker, quantity, price):

        if(self.portfolio.cash_left>0 and (self.portfolio.cash_left > (quantity*price))):

            if(self.portfolio.stock_in_portfolio(ticker)):
                self.portfolio.update_allocation(ticker, quantity, price)
            else:
                metadata = find_in_json(read_json(self.optimizer.metadata_loc), "Ticker", ticker)
                stock = Stock()
                stock.load(metadata)
                stock.metadata['Portfolio Allocation'] = quantity
                stock.metadata['Price'] = price
                stock.price = price
                stock.metadata['Value'] = quantity*price
                self.portfolio.stocks.append(stock)

            self.total_cash -= (quantity*price)
            self.order_log.append({"Stock": ticker, "Sold": 0, "Bought": quantity, "Value": quantity*price})
    
    def execute_sell(self, ticker, quantity, price):

        if(self.portfolio.stock_in_portfolio(ticker)):
            self.portfolio.update_allocation(ticker, quantity, price)
        self.total_cash += ((-quantity)*price)
        self.order_log.append({"Stock": ticker, "Sold": -quantity, "Bought": 0, "Value": -quantity*price})
    
    def log(self, date, is_realloc):       
        pvalue = self.portfolio.total_portfolio_value()
        portfolio_log = {
            "Portfolio Name":self.name,
            "Date":date.strftime('%Y-%m-%d'),
            "Single Day Cash Allocation": self.single_day_cash*100,
            "Initial Portfolio Value": self.init_portfolio,
            "Current Portfolio Value": pvalue + self.total_cash,
            "Cumulative Portfolio Return":((pvalue + self.total_cash - \
                                    self.init_portfolio)/self.init_portfolio)*100,
            "Amount Invested":pvalue,
            "Amount Reserved":self.total_cash,
            "Reallocation Day":is_realloc,
        }
        print(json.dumps(portfolio_log, indent = 4))
        portfolio_log["Portfolio Composition"] = [s.metadata for s in self.portfolio.stocks]

        self.portfolio_logs.append(portfolio_log)

        optimizer_log = {}
        optimizer_log['Portfolio Name'] = self.name
        optimizer_log['Date'] = date.strftime('%Y-%m-%d')
        optimizer_log['Composition'] = self.optimizer.portfolio.discrete_composition

        self.optimizer_logs.append(optimizer_log)

        exec_order_log = {}
        exec_order_log['Portfolio Name'] = self.name
        exec_order_log['Date'] = date.strftime('%Y-%m-%d')
        exec_order_log["Executed Orders"] = self.order_log

        self.exec_order_logs.append(exec_order_log)
        

class Backtesting:
    def __init__(self, start_date=date(1980, 1, 1), end_date=date.today(), 
                bband_margins=True, bband_ma=20, bband_std_mul=2, 
                upper_margin=0.05, lower_margin=0.05, lookback_period=30,
                rebalance_period=30, proc_ohlc_loc=None, proc_metadata_loc=None,
                agents=[], benchmark={}, portfolio_value=1000000, 
                process_metrics=False, log_data_loc="data/processed/Simulated"):
                 
        self.start_date = start_date
        self.end_date = end_date
        self.bband_margins = bband_margins
        self.bband_ma = bband_ma,
        self.bband_std_mul = bband_std_mul
        self.upper_margin = upper_margin
        self.lower_margin = lower_margin
        self.lookback_period = lookback_period
        self.rebalance_period = rebalance_period
        self.benchmark = benchmark
        self.log_data_loc = log_data_loc
    
        self.processor = IndexProcessor(proc_ohlc_loc, proc_metadata_loc)
        if process_metrics:
            self.processor.process_metrics(upper_margin, lower_margin, bband_ma, 
                                        bband_std_mul)
        self.processor.process_close(start_date, end_date)

        self.agents = agents

        self.env = Environment(self.processor.close_matrix, 
                               pd.DataFrame(read_json(proc_metadata_loc)),
                               self.lookback_period)

    def backtest(self):
        for a in self.agents:
            for i in range(len(self.env.dates)):
                        
                    print("Day: {}".format(self.env.current_date+1))

                    dayend_prices = self.env.load_next_day(a, self.bband_margins)
                    if(self.env.is_reallocation_day()):

                        allocation_data = self.env.load_lookback_data()
                        a.allocate_portfolio(allocation_data)
                        a.compute_allocation_orders()
                        a.execute_orders(dayend_prices)
                        
                    a.total_cash += a.portfolio.cash_left
                    #print("This is cash left: {}".format(a.portfolio.cash_left))
                    #if(a.portfolio.cash_left )
                    a.portfolio.cash_left = 0
                    a.log(self.env.dates[i], self.env.is_reallocation_day())
                    print()
            
                    write_json(a.portfolio_logs, "{}/AGENT_{}_PORTFOLIO_DATA.json".format(self.log_data_loc, a.name))
                    write_json(a.optimizer_logs, "{}/AGENT_{}_OPTIMIZER_DATA.json".format(self.log_data_loc, a.name))
                    write_json(a.exec_order_logs, "{}/AGENT_{}_ORDER_DATA.json".format(self.log_data_loc, a.name))

            self.env.reset()
        
