"""Optimizer module

This script contains optimizer functions for creation of portfolios.

It contains following classes
    * Optimizer: Base Optimizer Class
    * EffOptimizer: Derived Optimizer Class for Efficient Frontiner based 
                    allocation
    * HRPOptimizer: Derived Optimizer Class for Hierarchial Risk Parity based
                    allocation
    * CLAOptimizer: Derived Optimizer Class for Critical Line Algorithm based
                    allocation
    * DeepDowOptimizer: Derived Optimizer Class for DeepDow (Deep Learning) 
                    based allocation
"""

from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.hierarchical_portfolio import HRPOpt
from pypfopt.cla import CLA
from pypfopt import risk_models, expected_returns
import pandas as pd

from ds import Portfolio


class Optimizer:
    """
    Base class to represent an Optimizer

    ...

    Attributes
    ----------
    portfolio : Portfolio()
        Portfolio object to contain optimizer's output
    processor : IndexProcessor()
        IndexProcessor object to collect input data
    optimizer : <varies>
        Optimizer object used for calculations
    
    Methods
    -------
    optimize(): void
        Performs portfolio optimization and constructs portfolio to store data
    """

    def __init__(self, processor=None):
        self.portfolio = Portfolio()
        self.processor = processor
        self.optimizer = None
    
    def optimize(self):
        """Performs portfolio optimization and constructs portfolio to store data
        """

        pass


class EffOptimizer:
    """
    Derived Optimizer Class for Efficient Frontiner based allocation

    ...

    Attributes
    ----------
    portfolio : Portfolio()
        Portfolio object to contain optimizer's output
    processor : IndexProcessor()
        IndexProcessor object to collect input data
    optimizer : EfficientFrontier()
        EfficientFrontier object used for calculations
    optimizer_type: str
        Specifies type of optimizer (max_sharpe or min_vol)
    mu: pd.DataFrame
        Stock Returns Matrix
    s: pd.DataFrame
        Stock Covariance Matrix
    
    Methods
    -------
    optimize(): void
        Executes optimize methods based on optimizer type specified
    optimize_max_sharpe(): void
        Performs portfolio optimization (aiming for maximum sharpe ratio value)
        and constructs portfolio to store data
    optimize_min_volatility(): void
        Performs portfolio optimization (aiming for minimum volatility)
        and constructs portfolio to store data
    """

    def __init__(self, close_matrix=None, metadata_loc=None):
        super().__init__()
        self.portfolio = Portfolio()
        self.close_matrix = close_matrix
        self.metadata_loc = metadata_loc
        self.optimizer = None
        self.optimizer_type = "max_sharpe"
    
    def optimize(self):
        """Executes optimize methods based on optimizer type specified
        """

        if(self.optimizer_type == "max_sharpe"):
            self.optimize_max_sharpe()
        elif(self.optimizer_type=="min_vol"):
            self.optimize_min_volatility()

    def optimize_max_sharpe(self):
        """Performs portfolio optimization (aiming for maximum sharpe ratio value)
        and constructs portfolio to store data
        """

        self.mu = expected_returns.mean_historical_return(self.close_matrix)
        self.s = risk_models.CovarianceShrinkage(self.close_matrix).ledoit_wolf()
        #self.s = risk_models.sample_cov(self.close_matrix)
        self.optimizer = EfficientFrontier(self.mu, self.s)

        self.optimizer.max_sharpe()
        self.portfolio.composition = self.optimizer.clean_weights()
        latest_price = self.close_matrix.tail(1)
        latest_price = latest_price.dropna(axis=1)
        latest_price = pd.Series(list(latest_price.T.to_dict().values())[0])
        self.portfolio.construct( latest_price, self.metadata_loc, 
                                    self.optimizer.portfolio_performance())


    def optimize_min_volatility(self):
        """Performs portfolio optimization (aiming for minimum volatility)
        and constructs portfolio to store data
        """

        self.mu = expected_returns.mean_historical_return(self.close_matrix)
        self.s = risk_models.CovarianceShrinkage(self.close_matrix).ledoit_wolf()
        #self.s = risk_models.sample_cov(self.processor.close_matrix)
        self.optimizer = EfficientFrontier(None, self.s)

        self.optimizer.min_volatility()
        self.portfolio.composition = self.optimizer.clean_weights()
        latest_price = self.close_matrix.tail(1)
        latest_price = latest_price.dropna(axis=1)
        latest_price = pd.Series(list(latest_price.T.to_dict().values())[0])
        self.portfolio.construct( latest_price, self.metadata_loc, 
                                    self.optimizer.portfolio_performance())


class HRPOptimizer:
    """
    Derived Optimizer Class for Hierarchial Risk Parity based allocation

    ...

    Attributes
    ----------
    portfolio : Portfolio()
        Portfolio object to contain optimizer's output
    processor : IndexProcessor()
        IndexProcessor object to collect input data
    optimizer : HRPOpt()
        HRPOpt object used for calculations
    mu: pd.DataFrame
        Stock Returns Matrix
    
    Methods
    -------
    optimize(): void
        Performs portfolio optimization (aiming for most diverse portfolio)
        and constructs portfolio to store data
    """

    def __init__(self, close_matrix=None, metadata_loc=None):
        super().__init__()
        self.portfolio = Portfolio()
        self.close_matrix = close_matrix
        self.metadata_loc = metadata_loc
        self.optimizer = None

    def optimize(self):
        """Performs portfolio optimization (aiming for most diverse portfolio)
        and constructs portfolio to store data
        """

        self.mu = expected_returns.returns_from_prices(self.close_matrix)
        self.optimizer = HRPOpt(self.mu)
        self.optimizer.optimize()
        self.portfolio.composition = self.optimizer.clean_weights()
        latest_price = self.close_matrix.tail(1)
        latest_price = latest_price.dropna(axis=1)
        latest_price = pd.Series(list(latest_price.T.to_dict().values())[0])
        self.portfolio.construct( latest_price, self.metadata_loc, 
                                    self.optimizer.portfolio_performance())



class CLAOptimizer:
    """
    Derived Optimizer Class for Critial Line Algorithm based allocation

    ...

    Attributes
    ----------
    portfolio : Portfolio()
        Portfolio object to contain optimizer's output
    processor : IndexProcessor()
        IndexProcessor object to collect input data
    optimizer : CLA()
        CLA object used for calculations
    optimizer_type: str
        Specifies type of optimizer (max_sharpe or min_vol)
    mu: pd.DataFrame
        Stock Returns Matrix
    s: pd.DataFrame
        Stock Covariance Matrix
    
    Methods
    -------
    optimize(): void
        Executes optimize methods based on optimizer type specified
    optimize_max_sharpe(): void
        Performs portfolio optimization (aiming for maximum sharpe ratio value)
        and constructs portfolio to store data
    optimize_min_volatility(): void
        Performs portfolio optimization (aiming for minimum volatility)
        and constructs portfolio to store data
    """

    def __init__(self, close_matrix=None, metadata_loc=None):
        super().__init__()
        self.portfolio = Portfolio()
        self.close_matrix = close_matrix
        self.metadata_loc = metadata_loc
        self.optimizer = None
        self.optimizer_type = "max_sharpe"

    def optimize(self):
        """Executes optimize methods based on optimizer type specified
        """

        if(self.optimizer_type == "max_sharpe"):
            self.optimize_max_sharpe()
        elif(self.optimizer_type=="min_vol"):
            self.optimize_min_volatility()
            
    def optimize_max_sharpe(self):
        """Performs portfolio optimization (aiming for maximum sharpe ratio value)
        and constructs portfolio to store data
        """

        total_mean = self.close_matrix.mean(axis=0).mean()
        self.close_matrix = self.close_matrix[self.close_matrix.columns[
                                    self.close_matrix.mean(axis=0) > total_mean]]
        self.mu = expected_returns.mean_historical_return(self.close_matrix)
        #self.s = risk_models.sample_cov(processor.close_matrix)
        self.s = risk_models.CovarianceShrinkage(self.close_matrix).ledoit_wolf()

        self.optimizer = CLA(self.mu, self.s)
        self.portfolio.composition = self.optimizer.max_sharpe()
        latest_price = self.close_matrix.tail(1)
        latest_price = latest_price.dropna(axis=1)
        latest_price = pd.Series(list(latest_price.T.to_dict().values())[0])
        self.portfolio.construct( latest_price, self.metadata_loc, 
                                    self.optimizer.portfolio_performance())


    def optimize_min_volatility(self):
        """Performs portfolio optimization (aiming for minimum volatility)
        and constructs portfolio to store data
        """

        total_mean = self.close_matrix.mean(axis=0).mean()
        self.close_matrix = self.close_matrix[self.close_matrix.columns[
                                    self.close_matrix.mean(axis=0) > total_mean]]
        self.mu = expected_returns.mean_historical_return(self.close_matrix)
        #self.s = risk_models.sample_cov(processor.close_matrix)
        self.s = risk_models.CovarianceShrinkage(self.close_matrix).ledoit_wolf()

        self.optimizer = CLA(self.mu, self.s)
        self.portfolio.composition = self.optimizer.min_volatility()
        latest_price = self.close_matrix.tail(1)
        latest_price = latest_price.dropna(axis=1)
        latest_price = pd.Series(list(latest_price.T.to_dict().values())[0])
        self.portfolio.construct( latest_price, self.metadata_loc, 
                                    self.optimizer.portfolio_performance())


class DeepDowOptimizer:
    """
    Derived Optimizer Class for DeepDow (Deep Learning) based allocation

    ...

    Attributes
    ----------
    portfolio : Portfolio()
        Portfolio object to contain optimizer's output
    processor : IndexProcessor()
        IndexProcessor object to collect input data
    optimizer : ________ 
        ______ object used for calculations
    
    Methods
    -------
    optimize(): void
        Performs portfolio optimization and constructs portfolio to store data
    """

    def __init__(self, processor=None):
        super().__init__()
    
    def optimize(self):
        """Performs portfolio optimization and constructs portfolio to store data
        """

        pass