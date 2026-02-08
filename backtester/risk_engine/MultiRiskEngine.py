import math
import os, sys
import traceback
import warnings
import numpy as np
import pandas as pd
import uuid
from datetime import datetime
from functools import partial
from typing import List, Tuple, Optional, Dict, Type, Union
from math import copysign
from copy import copy
import sys
from backtester.backtesting import Backtest, _Broker, Strategy, Trade, Order, _OutOfMoneyError, _Data, _Indicator
from backtester.multi_backtester.multi_backtester import MultiBacktest
from backtester.OutputUpdatersDB.output_updater import OutputUpdater
from backtester._stats import compute_stats


def normalize_levels(levels: Optional[Union[float, List[Union[float, Tuple[float, float]]]]]
                    ) -> Tuple[List[float], List[float]]:
    """
    Converts levels input into separate lists of (prices, weights).
    If weights not provided, evenly split weights assumed.
    """
    if levels is None:
        return [], []

    # Wrap single float or tuple in a list
    if not isinstance(levels, list):
        levels = [levels]

    # Detect if list contains tuples (level, weight)
    if all(isinstance(x, (float, int)) for x in levels):
        # Only levels given, equal weights
        prices = [float(x) for x in levels]
        weights = [1.0 / len(prices)] * len(prices) if prices else []
    elif all(isinstance(x, (list, tuple)) and len(x) == 2 for x in levels):
        # List of (level, weight) tuples provided
        prices = [float(x[0]) for x in levels]
        weights = [float(x[1]) for x in levels]
    else:
        raise ValueError("Levels must be a list of floats or list of (price, weight) tuples")

    return prices, weights


class BracketOrder(Order):
    def __init__(self, broker: 'SmartBroker', ticker: str, size: float, order_id: int, limit_price: Optional[float] = None,
                 stop_price: Optional[float] = None, parent_trade: Optional['BracketTrade'] = None, entry_time: datetime = None,
                 tag: object = None, reason: object = None, sl: Optional[List[Tuple[float, float]]] = None, tp: Optional[List[Tuple[float, float]]] = None):
        self.order_id = order_id
        super().__init__(broker=broker, ticker=ticker, size=size, limit_price=limit_price, stop_price=stop_price,
                        sl_price=None, tp_price=None, parent_trade=parent_trade, entry_time=entry_time, tag=tag, reason=reason)
        self.sl: Optional[List[Tuple[float, float]]] = sl
        self.tp: Optional[List[Tuple[float, float]]] = tp

    def __repr__(self):
        base_repr = super().__repr__()
        sl_str = f", sl={self.sl}" if self.sl else ""
        tp_str = f", tp={self.tp}" if self.tp else ""
        order_id_str = f",order_id = {self.order_id}" if self.order_id is not None else ""
        return base_repr[:-1] + f"{sl_str}{tp_str}{order_id_str}>"

    @property
    def sl(self) -> Optional[List[Tuple[float, float]]]:
        return self.__dict__.get('sl', None)

    @sl.setter
    def sl(self, value: Optional[List[Tuple[float, float]]]):
        self.__dict__['sl'] = value

    @property
    def tp(self) -> Optional[List[Tuple[float, float]]]:
        return self.__dict__.get('tp', None)

    @tp.setter
    def tp(self, value: Optional[List[Tuple[float, float]]]):
        self.__dict__['tp'] = value

    def _replace(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, f'_{Order.__qualname__}__{k}', v)
        return self

    def cancel(self):
        self._Order__broker.orders.remove(self)
        trade = self._Order__parent_trade
        if trade:
            if self in trade._sl_orders.values():
                for price_level, order in list(trade._sl_orders.items()):
                    if order.order_id == self.order_id:
                        trade._sl_orders.pop(price_level)
                        break
            elif self in trade._tp_orders.values():
                for price_level, order in list(trade._tp_orders.items()):
                    if order.order_id == self.order_id:
                        trade._tp_orders.pop(price_level)
                        break
            else:
                assert False


class BracketTrade(Trade):
    def __init__(self, broker: 'SmartBroker', ticker: str, size: int, entry_price: float, entry_bar, entry_time, tag, reason: Optional['BracketOrder'] = None):
        super().__init__(broker, ticker, size, entry_price, entry_bar, entry_time, tag, reason)
        self._sl_orders: Dict[float, 'BracketOrder'] = {}
        self._tp_orders: Dict[float, 'BracketOrder'] = {}
        self.__trade_id = 0
        self.__metadata = {
            'SL': [],  # List of all SL prices
            'TP': [],  # List of all TP prices
            'SL_weights': [],  # List of all SL weights
            'TP_weights': []   # List of all TP weights
        }

    def __repr__(self):
        return f'<Trade ID={self.__trade_id} Trade size={self.__size} time={self.__entry_bar}-{self.__exit_bar or ""} ' \
               f'price={self.__entry_price}-{self.__exit_price or ""} ' \
               f'{" sl="+str(self.sl) if self.sl is not None else "No SL"}' \
               f'{" tp="+str(self.tp) if self.tp is not None else "No TP"} ' \
               f'pl={self.pl:.0f}' \
               f'{" tag="+str(self.__tag) if self.__tag is not None else ""}' \
               f'{" reason="+str(self.__reason) if self.__reason is not None else ""}>'

    @property
    def sl(self) -> Optional[List[Tuple[float, float]]]:
        if not self._sl_orders:
            return None
        return [(price, abs(order.size)) for price, order in self._sl_orders.items()]

    @sl.setter
    def sl(self, levels: Optional[List[Tuple[float, float]]]):
        self.__set_contingent('sl', levels)

    @property
    def tp(self) -> Optional[List[Tuple[float, float]]]:
        if not self._tp_orders:
            return None
        return [(price, abs(order.size)) for price, order in self._tp_orders.items()]

    @tp.setter
    def tp(self, levels: Optional[List[Tuple[float, float]]]):
        self.__set_contingent('tp', levels)

    @property
    def metadata(self) -> dict:
        """
        Metadata dictionary containing SL/TP prices and weights.
        
        Returns:
            dict: Contains keys 'SL', 'TP', 'SL_weights', 'TP_weights'
        """
        return self.__metadata.copy()

    @metadata.setter
    def metadata(self, value: dict):
        """
        Set metadata dictionary. Only allows updating specific keys.
        
        Args:
            value: dict containing any of 'SL', 'TP', 'SL_weights', 'TP_weights'
        """
        allowed_keys = {'SL', 'TP', 'SL_weights', 'TP_weights'}
        for key, val in value.items():
            if key in allowed_keys:
                self.__metadata[key] = val

    @property
    def sl_metadata(self) -> dict:
        """
        Get SL-related metadata.
        
        Returns:
            dict: Contains 'SL' and 'sl_weights'
        """
        return {
            'SL': self.__metadata.get('SL'),
            'SL_weights': self.__metadata.get('SL_weights')
        }

    @property
    def tp_metadata(self) -> dict:
        """
        Get TP-related metadata.
        
        Returns:
            dict: Contains 'TP' and 'tp_weights'
        """
        return {
            'TP': self.__metadata.get('TP'),
            'TP_weights': self.__metadata.get('TP_weights')
        }

    def __set_contingent(self, order_type: str, levels: Optional[List[Tuple[float, float]]]):
        assert order_type in ('sl', 'tp')
        orders_dict = self._sl_orders if order_type == 'sl' else self._tp_orders

        if levels is None:
            for order in list(orders_dict.values()):
                order.cancel()
            orders_dict.clear()
            return

        if not isinstance(levels, list):
            raise TypeError(f"{order_type.upper()} expects a list of (price, size) tuples or None.")

        existing_prices = set(orders_dict.keys())
        new_prices = set(price for price, _ in levels)

        for price in existing_prices - new_prices:
            order = orders_dict.pop(price)
            order.cancel()
            if order in self._Trade__broker.orders:
                self._Trade__broker.orders.remove(order)

        temp_size = 0
        levels_len = len(levels)
        iterable = enumerate(reversed(levels))

        for idx, (price, weight) in iterable:
            if not (0 < price < float('inf')):
                raise ValueError(f"{order_type.upper()} price must be positive and finite.")
            if weight <= 0:
                raise ValueError(f"{order_type.upper()} weight must be positive.")

            proportional_size = self.size * weight

            if idx == levels_len - 1:
                remaining_size = abs(self.size) - temp_size
                desired_size = -remaining_size if self.is_long else remaining_size
            else:
                desired_size = -round(abs(proportional_size)) if self.is_long else round(abs(proportional_size))
                temp_size += abs(desired_size)

            if price in orders_dict:
                existing_order = orders_dict[price]
                if existing_order.size != desired_size:
                    existing_order._replace(size=desired_size)
            else:
                kwargs = {'stop': price} if order_type == 'sl' else {'limit': price}
                new_order = self._Trade__broker.new_order(
                    self.ticker,
                    desired_size,
                    trade=self,
                    **kwargs
                )
                orders_dict[price] = new_order

    def close(self, portion: float = 1., finalize=False):
        assert 0 < portion <= 1, "portion must be a fraction between 0 and 1"
        size = copysign(max(1, round(abs(self._Trade__size) * portion)), -self._Trade__size)
        order = BracketOrder(self._Trade__broker, self._Trade__ticker, size, order_id=self._Trade__broker.order_id, parent_trade=self, entry_time=self._Trade__broker.now, tag=self._Trade__tag)
        self._Trade__broker.order_id += 1
        if finalize:
            return order
        else:
            self._Trade__broker.orders.insert(0, order)

    def _replace(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, f'_{Trade.__qualname__}__{k}', v)
        return self


class SmartBroker(_Broker):
    def __init__(self, data, cash, commission, spread, margin, trade_on_close,
                 hedging, exclusive_orders, trade_start_date, lot_size,
                 fail_fast, is_option, holding, storage):
        super().__init__(data=data, cash=cash, commission=commission, spread=spread, margin=margin,
                         trade_on_close=trade_on_close, hedging=hedging,
                         exclusive_orders=exclusive_orders,
                         trade_start_date=trade_start_date, lot_size=lot_size,
                         fail_fast=fail_fast, is_option=is_option, holding=holding, storage=storage)
        self.orders: List[BracketOrder] = []
        self.order_id: int = 0
        self.tp_count = 0
        self.sl_count = 0
        self.__trade_id = 0

    def _process_orders(self):
        i = len(self._data) - 1
        reprocess_orders = False

        for order in list(self.orders):
            data = self._data
            ticker_key = order.ticker
            if isinstance(ticker_key, list):
                if len(ticker_key) == 1:
                    ticker_key = ticker_key[0]
                else:
                    raise ValueError(f"Multiple tickers not supported in order.ticker: {ticker_key}")

            open_, high, low = (data[ticker_key, 'Open'][-1],
                              data[ticker_key, 'High'][-1],
                              data[ticker_key, 'Low'][-1])
            prev_close = data[ticker_key, 'Close'][-2]

            if order not in self.orders:
                continue

            stop_price = order.stop
            if stop_price:
                is_stop_hit = ((high > stop_price) if order.is_long else (low < stop_price))
                if not is_stop_hit:
                    continue
                order._replace(stop_price=None)

            if order.limit:
                is_limit_hit = low < order.limit if order.is_long else high > order.limit
                is_limit_hit_before_stop = (is_limit_hit and
                                          (order.limit < (stop_price or -np.inf)
                                           if order.is_long
                                           else order.limit > (stop_price or np.inf)))
                if not is_limit_hit or is_limit_hit_before_stop:
                    continue

                price = (min(stop_price or open_, order.limit)
                        if order.is_long else
                        max(stop_price or open_, order.limit))
            else:
                price = prev_close if self._trade_on_close else open_
                price = (max(price, stop_price or -np.inf)
                        if order.is_long else
                        min(price, stop_price or np.inf))

            is_market_order = not order.limit and not stop_price
            time_index = (i - 1) if is_market_order and self._trade_on_close else i
            entry_time = data.index[time_index]

            if order.parent_trade:
                trade = order.parent_trade
                _prev_size = trade.size
                executed_size = copysign(min(abs(_prev_size), abs(order.size)), order.size)

                if trade in self.trades[ticker_key]:
                    hit = None
                    if stop_price:
                        hit = 'sl'
                    elif order.limit:
                        hit = 'tp'
                    else:
                        hit = None

                    self._reduce_trade(trade, price, executed_size, time_index, entry_time, order.order_id, hit)
                    assert trade.size * executed_size < 0, "Executed size must oppose trade size"
                    assert abs(order.size) <= abs(_prev_size), "Order size cannot exceed current trade size"
                else:
                    assert abs(_prev_size) >= abs(executed_size) >= 1
                    self.orders.remove(order)
                    continue

                if order in self.orders:
                    self.orders.remove(order)

                assert abs(order.size) <= abs(_prev_size)
                assert order not in self.orders

                continue

            # Adjust price to include spread and commission.
            # In long positions, the adjusted price is a fraction higher, and vice versa.
            adjusted_price = self._adjusted_price(order.ticker, order.size, price)
            adjusted_price_plus_commission = adjusted_price + self._commission(order.size, price)

            size = order.size
            if -1 < size < 1:
                size = copysign(int((self.margin_available * self._leverage * abs(size))
                                  // adjusted_price_plus_commission), size)
                if not size:
                    self.orders.remove(order)
                    continue
                else:
                    order.size = int(size)
            assert size == round(size)
            need_size = int(size)

            if not self._hedging:
                for trade in list(self.trades[ticker_key]):
                    if trade.is_long == order.is_long:
                        continue
                    assert trade.size * order.size < 0

                    if abs(need_size) >= abs(trade.size):
                        self._close_trade(trade, price, time_index, entry_time, order.order_id)
                        need_size += trade.size
                    else:
                        self._reduce_trade(trade, price, need_size, time_index, entry_time, order.order_id)
                        need_size = 0

                    if not need_size:
                        break

            if abs(need_size) * adjusted_price > self.margin_available * self._leverage:
                if self._fail_fast:
                    raise RuntimeError(
                        f'Not enough cash for {order}, has {int(self.margin_available * self._leverage)},'
                        f' needs {int(abs(need_size) * adjusted_price)}, aborting')
                else:
                    print(f"Order not executed. Not enough liquidity for {order}, has {int(self.margin_available * self._leverage)},"
                          f" needs {int(abs(need_size) * adjusted_price)}, skipping")
                    self.orders.remove(order)
                    continue

            if need_size:
                weighted_sl = order.sl if hasattr(order, 'sl') and order.sl else []
                weighted_tp = order.tp if hasattr(order, 'tp') and order.tp else []

                self._open_trade(ticker_key, adjusted_price, need_size, sl=weighted_sl, tp=weighted_tp, time_index=time_index, entry_time=entry_time, tag=order.tag)

                if weighted_sl or weighted_tp:
                    if is_market_order:
                        reprocess_orders = True
                    else:
                        sl_prices = [lvl for lvl, _ in weighted_sl]
                        tp_prices = [lvl for lvl, _ in weighted_tp]
                        if any(low <= sl <= high for sl in sl_prices) or any(low <= tp <= high for tp in tp_prices):
                            warnings.warn(
                                f"({data.index[-1]}) A contingent SL/TP order would execute in the "
                                "same bar its parent stop/limit order was turned into a trade. "
                                "Result may be dubious. See github issues.",
                                UserWarning)

            self.orders.remove(order)

        if reprocess_orders:
            self._process_orders()

    def _open_trade(self, ticker: str, price: float, size: int,
                    sl: Optional[List[Tuple[float, float]]] = None,
                    tp: Optional[List[Tuple[float, float]]] = None,
                    time_index: int = None, entry_time: datetime = None, tag=None) -> BracketTrade:
        self.__trade_id += 1
        trade = BracketTrade(self, ticker, size, price, time_index, entry_time, tag)
        trade.__trade_id = self.__trade_id
        self.trades[ticker].append(trade)

        if tp:
            total_tp_size = sum(size for _, size in tp)
            if total_tp_size > abs(size):
                raise ValueError(f"Sum of TP sizes ({total_tp_size}) exceeds trade size ({abs(size)})")
            if abs(size) < len(tp):
                raise ValueError(f"More TP levels ({len(tp)}) than absolute trade size ({abs(size)})")
            trade.tp = tp
            trade.metadata = {
                'TP': [lvl for lvl, _ in tp],
                'TP_weights': [weight * size for lvl, weight in tp]
            }

        if sl:
            total_sl_size = sum(size for _, size in sl)
            if total_sl_size > abs(size):
                raise ValueError(f"Sum of SL sizes ({total_sl_size}) exceeds trade size ({abs(size)})")
            if abs(size) < len(sl):
                raise ValueError(f"More SL levels ({len(sl)}) than absolute trade size ({abs(size)})")
            trade.sl = sl
            trade.metadata = {
                'SL': [lvl for lvl, _ in sl],
                'SL_weights': [weight * size for lvl, weight in sl]
            }

        return trade

    def new_order(self,
                  ticker: str,
                  size: float,
                  order_id: int = 0,
                  limit: Optional[float] = None,
                  stop: Optional[float] = None,
                  sl: Optional[Union[float, List[Union[float, Tuple[float, float]]]]] = None,
                  tp: Optional[Union[float, List[Union[float, Tuple[float, float]]]]] = None,
                  tag: object = None,
                  *,
                  trade: Optional[BracketTrade] = None) -> Optional[BracketOrder]:
        ticker = ticker or self._data.the_ticker
        size = float(size)
        stop = float(stop) if stop is not None else None
        limit = float(limit) if limit is not None else None

        if sl and abs(size) < len(sl):
            if self._fail_fast:
                raise ValueError(f"More SL levels ({len(sl)}) than absolute trade size ({abs(size)})")
            else:
                print(f"Order not executed. More SL levels ({len(sl)}) than absolute trade size ({abs(size)})")
                return None

        if tp and abs(size) < len(tp):
            if self._fail_fast:
                raise ValueError(f"More TP levels ({len(tp)}) than absolute trade size ({abs(size)})")
            else:
                print(f"Order not executed. More TP levels ({len(tp)}) than absolute trade size ({abs(size)})")
                return None

        sl_list, sl_weights = normalize_levels(sl)
        tp_list, tp_weights = normalize_levels(tp)

        if len(sl_list) != len(sl_weights):
            raise ValueError(f"SL levels and weights count mismatch: {len(sl_list)} vs {len(sl_weights)}")
        if len(tp_list) != len(tp_weights):
            raise ValueError(f"TP levels and weights count mismatch: {len(tp_list)} vs {len(tp_weights)}")

        entry_price = limit or stop or self._adjusted_price(ticker, size)
        is_long = size > 0

        if is_long:
            for sl_val in sl_list:
                if not sl_val < entry_price:
                    msg = f"SL ({sl_val}) must be less than entry price ({entry_price})"
                    if self._fail_fast:
                        raise ValueError(msg)
                    else:
                        print(f"Order not executed. Long orders require: {msg}")
                        return None
            for tp_val in tp_list:
                if not tp_val > entry_price:
                    msg = f"TP ({tp_val}) must be greater than entry price ({entry_price})"
                    if self._fail_fast:
                        raise ValueError(msg)
                    else:
                        print(f"Order not executed. Long orders require: {msg}")
                        return None
        else:
            for sl_val in sl_list:
                if not sl_val > entry_price:
                    msg = f"SL ({sl_val}) must be greater than entry price ({entry_price})"
                    if self._fail_fast:
                        raise ValueError(msg)
                    else:
                        print(f"Order not executed. Short orders require: {msg}")
                        return None
            for tp_val in tp_list:
                if not tp_val < entry_price:
                    msg = f"TP ({tp_val}) must be less than entry price ({entry_price})"
                    if self._fail_fast:
                        raise ValueError(msg)
                    else:
                        print(f"Order not executed. Short orders require: {msg}")
                        return None

        base_order = BracketOrder(self, ticker, size, limit_price=limit, stop_price=stop, sl=[], tp=[], parent_trade=trade, entry_time=self.now, tag=tag, order_id=self.order_id)
        self.order_id += 1
        if trade:
            self.orders.insert(0, base_order)
        else:
            if self._exclusive_orders:
                for o in list(self.orders):
                    if not o.is_contingent:
                        o.cancel()
                for t in self.trades.get(ticker, []):
                    t.close()
            self.orders.append(base_order)

        base_order.sl = list(zip(sl_list, sl_weights)) if sl_list else []
        base_order.tp = list(zip(tp_list, tp_weights)) if tp_list else []

        return base_order

    def _reduce_trade(self, trade: BracketTrade, price: float, size: float, time_index: int, entry_time: datetime, order_id: int, hit: str = None):
        assert trade.size * size < 0
        assert abs(trade.size) >= abs(size)

        size_left = trade.size + size
        assert size_left * trade.size >= 0

        if not size_left:
            close_trade = trade
            if hit:
                hit = f"Final {hit.upper()} Hit"
            else:
                hit = f"Trade Close"

            self.tp_count = 0
            self.sl_count = 0
            trade.reason = hit
        else:
            trade._replace(size=size_left)
            remaining_size = abs(size_left)

            if hit == 'sl':
                if hasattr(trade, '_tp_orders') and trade._tp_orders:
                    total_weight_tp = sum(abs(order.size) for order in trade._tp_orders.values())
                    if total_weight_tp == 0:
                        total_weight_tp = 1

                    allocated_size = 0
                    tp_items = list(trade._tp_orders.items())
                    last_index = len(tp_items) - 1

                    for idx, (price_level, order) in enumerate(tp_items):
                        current_weight = abs(order.size) / total_weight_tp
                        if idx < last_index:
                            new_size_abs = round(abs(size_left) * current_weight)
                            new_size = -new_size_abs if trade.size > 0 else new_size_abs
                            allocated_size += new_size_abs
                        else:
                            remaining = abs(size_left) - allocated_size
                            new_size = -remaining if trade.size > 0 else remaining

                        if abs(new_size) < 1:
                            order.cancel()
                            if order in self.orders:
                                self.orders.remove(order)
                        else:
                            order._replace(size=new_size)

            if hit == 'tp':
                if hasattr(trade, '_sl_orders') and trade._sl_orders:
                    total_weight_sl = sum(abs(order.size) for order in trade._sl_orders.values())
                    if total_weight_sl == 0:
                        total_weight_sl = 1

                    allocated_size = 0
                    sl_items = list(trade._sl_orders.items())
                    last_index = len(sl_items) - 1

                    for idx, (price_level, order) in enumerate(sl_items):
                        current_weight = abs(order.size) / total_weight_sl
                        if idx < last_index:
                            new_size_abs = round(abs(size_left) * current_weight)
                            new_size = -new_size_abs if trade.size > 0 else new_size_abs
                            allocated_size += new_size_abs
                        else:
                            remaining = abs(size_left) - allocated_size
                            new_size = -remaining if trade.size > 0 else remaining

                        if abs(new_size) < 1:
                            order.cancel()
                            if order in self.orders:
                                self.orders.remove(order)
                        else:
                            order._replace(size=new_size)

            close_trade = trade._copy(size=-size, sl_order=None, tp_order=None)
            self.trades[trade.ticker].append(close_trade)

        self._close_trade(close_trade, price, time_index, entry_time, order_id, hit)

    def _close_trade(self, trade: BracketTrade, price: float, time_index: int, entry_time: datetime, order_id: int, hit: Optional[str] = None):
        if trade in self.trades.get(trade.ticker, []):
            self.trades[trade.ticker].remove(trade)

        if hit == 'sl' and trade._sl_orders:
            order_to_remove = None
            for price_level, order in list(trade._sl_orders.items()):
                if order.order_id == order_id:
                    order_to_remove = order
                    trade._sl_orders.pop(price_level)
                    break

            if order_to_remove and order_to_remove in self.orders:
                self.orders.remove(order_to_remove)

            self.sl_count += 1
            trade.reason = f"SL{self.sl_count} Hit"
        elif hit == 'tp' and trade._tp_orders:
            order_to_remove = None
            for price_level, order in list(trade._tp_orders.items()):
                if order.order_id == order_id:
                    order_to_remove = order
                    trade._tp_orders.pop(price_level)
                    break

            if order_to_remove and order_to_remove in self.orders:
                self.orders.remove(order_to_remove)

            self.tp_count += 1
            trade.reason = f"TP{self.tp_count} Hit"
        else:
            if trade._sl_orders:
                for o in list(trade._sl_orders.values()):
                    if o in self.orders:
                        self.orders.remove(o)
                # trade._sl_orders.clear()
            if trade._tp_orders:
                for o in list(trade._tp_orders.values()):
                    if o in self.orders:
                        self.orders.remove(o)
                # trade._tp_orders.clear()

        self.closed_trades.append(trade._replace(exit_price=price, exit_bar=time_index, exit_time=entry_time))
        self._cash += trade.pl

    def finalize(self):
        final_orders = [trade.close(finalize=True) for trade in self.all_trades]
        for order in final_orders:
            price = self.last_price(order.ticker)
            time_index = len(self._data) - 1
            trade = order.parent_trade
            _prev_size = trade.size
            size = copysign(min(abs(_prev_size), abs(order.size)), order.size)
            if trade in self.trades[order.ticker]:
                self._reduce_trade(trade, price, size, time_index, self._data.index[time_index], order.order_id)
                assert order.size != -_prev_size or trade not in self.trades[order.ticker]

    def _copy(self, **kwargs):
        return copy(self)._replace(**kwargs)


class MultiBandStrategy(Strategy):
    def __init__(self, broker: SmartBroker, data: pd.DataFrame, params: dict):
        super().__init__(broker, data, params)
        # map entry_order_id -> list of its BracketOrder legs
        self.pending_by_order: Dict[int, List[BracketOrder]] = {}
        self._cascade_map = {}   # entry_order.id -> {'size','sl_levels','sl_weights','tp_levels','tp_weights'}
        self.tickers      = self.data.tickers
        # track how many closed trades we've handled so far
        self.total_trades = len(self.closed_trades)

    def infer_pip_size(self, price: float) -> float:
        """
        Infers pip size based on number of decimal digits in the price.
        - Most Forex pairs: 0.0001 (4 decimal places)
        - JPY pairs: 0.01 (2 decimal places)
        """
        price_str = f"{price:.10f}".rstrip('0')  # remove trailing zeros
        if '.' in price_str:
            decimals = len(price_str.split('.')[1])
        else:
            decimals = 0
            
        if decimals >= 4:
            return 0.0001
        elif decimals >= 2:
            return 0.01
        else:
            return 1.0  # fallback if it's an integer-like price

    def round_to_pip_size(self, value: float, entry_price: float) -> float:
        """
        Rounds a value to the appropriate pip size based on the entry price.
        
        Args:
            value (float): The value to round
            entry_price (float): The entry price to determine pip size
            
        Returns:
            float: The value rounded to pip size
        """
        pip_size = self.infer_pip_size(entry_price)
        return round(value / pip_size) * pip_size

    class __FULL_EQUITY(float):  # noqa: N801
        def __repr__(self): return '.9999'
    _FULL_EQUITY = __FULL_EQUITY(1 - sys.float_info.epsilon)

    def buy(self, *,
            ticker: str = None,
            size: float = _FULL_EQUITY,
            limit: Optional[float] = None,
            stop: Optional[float] = None,
            sl: Optional[List[Tuple[float, float]]] = None,  # List of (stop_loss_level, weight)
            tp: Optional[List[Tuple[float, float]]] = None,  # List of (take_profit_level, weight)
            tag: object = None):
        assert 0 < size < 1 or round(size) == size, \
            "size must be a positive fraction of equity, or a positive whole number of units"

        if sl is not None and not isinstance(sl, list):
            sl = [sl]
        if tp is not None and not isinstance(tp, list):
            tp = [tp]

        return self._broker.new_order(ticker=ticker, size=size, limit=limit, stop=stop, sl=sl, tp=tp, tag=tag)

    def sell(self, *,
             ticker: str = None,
             size: float = _FULL_EQUITY,
             limit: Optional[float] = None,
             stop: Optional[float] = None,
             sl: Optional[List[Tuple[float, float]]] = None,
             tp: Optional[List[Tuple[float, float]]] = None,
             tag: object = None):
        assert 0 < size < 1 or round(size) == size, \
            "size must be a positive fraction of equity, or a positive whole number of units"

        if sl is not None and not isinstance(sl, list):
            sl = [sl]
        if tp is not None and not isinstance(tp, list):
            tp = [tp]

        return self._broker.new_order(ticker=ticker, size=-size, limit=limit, stop=stop, sl=sl, tp=tp, tag=tag)

    def add_buy_trade(self, entry_mode: str = "normal", X_pct: float = 0.02, Y_pct: float = 0.5, levels: int = 4):

        """
        entry_mode:
            normal       → one market order
            average_down → market slice + LIMIT ladders
            average_up   → market slice + STOP  ladders
            cascade      → one market order, then re-enter at each TP level sl & tp are lists of (price, weight).
        """

        assert entry_mode in ("normal", "average_down", "average_up", "cascade"), f"entry_mode must be one of normal|average_down|average_up|cascade, got {entry_mode!r}"
        assert 0 < Y_pct <= 1,       f"Y_pct (initial fraction) must be in (0,1], got {Y_pct}"
        assert X_pct > 0 or entry_mode in ("normal", "cascade"), f"X_pct must be >0 in pyramiding mode, got {X_pct}"
        assert levels >= 1 or entry_mode in ("normal", "cascade"), f"levels must be >=1 in pyramiding mode, got {levels}"
        
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]
        
        if risk_per_trade > 0:

            weighted_sl, weighted_tp = self.trade_manager.calculate_weighted_tp_sl_levels("buy")
            
            tp_levels = [next(iter(tp)) for tp in weighted_tp if tp]  
            tp_weights = [list(tp.values())[0] for tp in weighted_tp if tp]  
            sl_levels = [next(iter(sl)) for sl in weighted_sl if sl]  
            sl_weights = [list(sl.values())[0] for sl in weighted_sl if sl]  
            
            # Round stop loss and take profit levels to pip size
            sl_levels = [self.round_to_pip_size(level, entry) for level in sl_levels]
            tp_levels = [self.round_to_pip_size(level, entry) for level in tp_levels]
            
            furthest_sl = min(sl_levels) 
            stop_loss_perc = abs(entry - furthest_sl) / entry    
            if stop_loss_perc <= 0:
                print("Stop‐loss % ≤ 0 → skip buy")
                return

            trade_size = risk_per_trade / stop_loss_perc    
            if np.isnan(trade_size) or trade_size <= 0:
                print("Bad $ size → skip buy")
                return

            qty = math.ceil(trade_size / entry)
            if qty == 0:
                print("Units=0 after cash check → skip buy")
                return

            sl_weighted = list(zip(sl_levels, sl_weights)) if sl_levels and sl_weights else None
            tp_weighted = list(zip(tp_levels, tp_weights)) if tp_levels and tp_weights else None


            # ─── NORMAL MODE ───────────────────────────────────────────────────────────
            if entry_mode == "normal":
                self.buy(size=qty, sl=sl_weighted, tp=tp_weighted)
                return

            # ─── CASCADE MODE ───────────────────────────────────────────────────────────
            if entry_mode == "cascade":
                o = self.buy(size=qty, sl=sl_weighted, tp=tp_weighted, tag=None)
                
                if not o:
                    return
                
                entry_id = o.id
                o.tag = entry_id
                
                # Prepare list of sl and tp levels
                sl_units = [abs(entry-level) for level, _ in sl_weighted] if sl_weighted else []
                tp_units = [abs(entry-level) for level, _ in tp_weighted] if tp_weighted else []

                # record for cascade
                self._cascade_map[entry_id] = {
                    'size': qty,
                    'sl_units':    sl_units,
                    'sl_weights':   sl_weights,
                    'tp_units':    tp_units,
                    'tp_weights':   tp_weights
                }

                return

            # ─── PYRAMIDING MODE ───────────────────────────────────────────────────────
            # initial market slice
            init_units = math.ceil(qty * Y_pct)
            if init_units <= 0:
                return

            entry_order = self.buy(size=init_units, sl=sl_weighted, tp=tp_weighted, tag=None)
            entry_id    = entry_order.id
            entry_order.tag = entry_id

            # record legs under this entry_id
            self.pending_by_order[entry_id] = []

            # split remainder into legs
            rem       = qty - init_units
            direction = -1 if entry_mode=="average_down" else 1
            step      = (X_pct * entry) / levels
            base      = rem // levels
            extra     = rem - base*levels

            for i in range(1, levels+1):
                qty = base + (extra if i==levels else 0)
                if qty <= 0:
                    continue
                price = entry + direction*step*i
                price = self.round_to_pip_size(price, entry)

                if direction < 0:
                    leg = self.buy(size=qty,
                                limit=price,
                                sl=sl_weighted, tp=tp_weighted,
                                tag=entry_id)
                else:
                    leg = self.buy(size=qty,
                                stop=price,
                                sl=sl_weighted, tp=tp_weighted,
                                tag=entry_id)

                self.pending_by_order[entry_id].append(leg)
            return

    def add_sell_trade(self, entry_mode: str = "normal", X_pct: float = 0.02, Y_pct: float = 0.5, levels: int = 4):

        """
        entry_mode:
            normal       → one market order
            average_down → market slice + LIMIT ladders
            average_up   → market slice + STOP  ladders
            cascade      → one market order, then re-enter at each TP level sl & tp are lists of (price, weight).
        """

        assert entry_mode in ("normal", "average_down", "average_up", "cascade"), f"entry_mode must be one of normal|average_down|average_up|cascade, got {entry_mode!r}"
        assert 0 < Y_pct <= 1,       f"Y_pct (initial fraction) must be in (0,1], got {Y_pct}"
        assert X_pct > 0 or entry_mode in ("normal", "cascade"), f"X_pct must be >0 in pyramiding mode, got {X_pct}"
        assert levels >= 1 or entry_mode in ("normal", "cascade"), f"levels must be >=1 in pyramiding mode, got {levels}"

        risk_per_trade = self.risk_management_strategy.get_risk_per_trade()
        entry = self.data.Close[-1]

        if risk_per_trade > 0:
        
            weighted_sl, weighted_tp = self.trade_manager.calculate_weighted_tp_sl_levels("sell")
            
            tp_levels = [next(iter(tp)) for tp in weighted_tp if tp]  
            tp_weights = [list(tp.values())[0] for tp in weighted_tp if tp]  
            sl_levels = [next(iter(sl)) for sl in weighted_sl if sl]  
            sl_weights = [list(sl.values())[0] for sl in weighted_sl if sl]  
            
            # Round stop loss and take profit levels to pip size
            sl_levels = [self.round_to_pip_size(level, entry) for level in sl_levels]
            tp_levels = [self.round_to_pip_size(level, entry) for level in tp_levels]
            
            closest_sl = max(sl_levels) 
            stop_loss_perc = abs(entry - closest_sl) / entry
            if stop_loss_perc <= 0:
                print("Stop‐loss % ≤ 0 → skip buy")
                return

            trade_size = risk_per_trade / stop_loss_perc
            if np.isnan(trade_size) or trade_size <= 0:
                print("Bad $ size → skip buy")
                return

            qty = math.ceil(trade_size / entry)
            if qty == 0:
                print("Units=0 after cash check → skip buy")
                return

            sl_weighted = list(zip(sl_levels, sl_weights)) if sl_levels and sl_weights else None
            tp_weighted = list(zip(tp_levels, tp_weights)) if tp_levels and tp_weights else None

            
            # ─── NORMAL MODE ───────────────────────────────────────────────────────────
            if entry_mode == "normal":
                self.sell(size=qty, sl=sl_weighted, tp=tp_weighted)
                return

            # ─── CASCADE ────────────────────────────────────────────────
            if entry_mode=="cascade":
                o = self.sell(size=qty, sl=sl_weighted, tp=tp_weighted, tag=None)
                
                if not o:
                    return
                                
                entry_id = o.id
                o.tag = entry_id

                # Prepare list of sl and tp levels - extract from tuples
                sl_units = [abs(entry-level) for level, _ in sl_weighted] if sl_weighted else []
                tp_units = [abs(entry-level) for level, _ in tp_weighted] if tp_weighted else []
                

                # record for cascade
                self._cascade_map[entry_id] = {
                    'size': qty,
                    'sl_units':    sl_units,
                    'sl_weights':   sl_weights,
                    'tp_units':    tp_units,
                    'tp_weights':   tp_weights
                }

                return

            # ─── PYRAMIDING MODE ───────────────────────────────────────────────────────
            # initial market slice
            init_units = math.ceil(qty * Y_pct)
            if init_units <= 0:
                return

            entry_order = self.sell(size=init_units, sl=sl_weighted, tp=tp_weighted, tag=None)
            entry_id    = entry_order.id
            entry_order.tag = entry_id

            # record legs under this entry_id
            self.pending_by_order[entry_id] = []

            # split remainder into legs
            rem       = qty - init_units
            direction = -1 if entry_mode=="average_down" else 1
            step      = (X_pct * entry) / levels
            base      = rem // levels
            extra     = rem - base*levels

            for i in range(1, levels+1):
                qty = base + (extra if i==levels else 0)
                if qty <= 0:
                    continue
                price = entry + direction*step*i
                price = self.round_to_pip_size(price, entry)

                if direction < 0:
                    leg = self.sell(size=qty,
                                limit=price,
                                sl=sl_weighted, tp=tp_weighted,
                                tag=entry_id)
                else:
                    leg = self.sell(size=qty,   
                                stop=price,
                                sl=sl_weighted, tp=tp_weighted,
                                tag=entry_id)

                self.pending_by_order[entry_id].append(leg)
            return

    def on_trade_close(self):
        """
        Cancel any leftover legs whose parent trade just closed.
        """
        closed_now   = len(self.closed_trades)
        newly_closed = closed_now - self.total_trades
        if newly_closed > 0:

            for tr in self.closed_trades[-newly_closed:]:

                eid = tr.tag   # entry_order.id
                if tr.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
                
                # cascade re-entry
                if tr.reason == 'Final TP Hit':

                    info = self._cascade_map.pop(eid, None)

                    if info:
                        # Final TP hit => re-enter once
                        if tr.size > 0:
                            # Prepare list of sl and tp levels
                            sl_levels = [tr.exit_price-level for level in info['sl_units']]
                            tp_levels = [tr.exit_price+level for level in info['tp_units']]
                            sl_weights = info['sl_weights']
                            tp_weights = info['tp_weights']
                            
                            # Re-enter once
                            newo = self.buy(size=info['size'],
                                            stop=tr.exit_price,
                                            sl=list(zip(sl_levels, sl_weights)) if sl_weights else None,
                                            tp=list(zip(tp_levels, tp_weights)) if tp_weights else None,
                                            tag=None)
                            if newo:
                                nid = newo.id
                                newo.tag = nid
                                self._cascade_map[nid] = info
                        else:
                            # Prepare list of sl and tp levels
                            sl_levels = [tr.exit_price+level for level in info['sl_units']]
                            tp_levels = [tr.exit_price-level for level in info['tp_units']]
                            sl_weights = info['sl_weights']
                            tp_weights = info['tp_weights']
                            
                            # Re-enter once
                            newo = self.sell(size=info['size'],
                                            stop=tr.exit_price,
                                            sl=list(zip(sl_levels, sl_weights)) if sl_weights else None,
                                            tp=list(zip(tp_levels, tp_weights)) if tp_weights else None,
                                            tag=None)
                            if newo:
                                nid = newo.id
                                newo.tag = nid
                                self._cascade_map[nid] = info

                if tr.reason in ("Final TP Hit", "Final SL Hit", "Trade Close"):
                    for leg in self.pending_by_order.pop(eid, []):
                        try:
                            leg.cancel()
                        except:
                            pass
        self.total_trades = closed_now


class _Backtest(Backtest):
    def __init__(self,
                 data: pd.DataFrame,
                 strategy: Type[MultiBandStrategy],
                 *,
                 cash: float = 10_000,
                 holding: dict = {},
                 commission: float = .0,
                 spread: float = .0,
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 trade_start_date=None,
                 lot_size=1,
                 fail_fast=True,
                 storage: dict | None = None,
                 is_option: bool = False):
        super().__init__(data=data, strategy=strategy, cash=cash, holding=holding, commission=commission,
                        spread=spread, margin=margin, trade_on_close=trade_on_close, hedging=hedging,
                        exclusive_orders=exclusive_orders, trade_start_date=trade_start_date,
                        lot_size=lot_size, fail_fast=fail_fast, storage=storage, is_option=is_option)
        self._broker = partial(
            SmartBroker, cash=cash, holding=holding, commission=commission, spread=spread, margin=margin,
            trade_on_close=trade_on_close, hedging=hedging,
            exclusive_orders=exclusive_orders,
            trade_start_date=trade_start_date if trade_start_date else None,
            lot_size=lot_size, fail_fast=fail_fast, storage=storage, is_option=is_option
        )

    def run(self, **kwargs) -> pd.Series:
        data = _Data(self._data.copy(deep=False))
        broker: SmartBroker = self._broker(data=data)
        strategy: MultiBandStrategy = self._strategy(broker, data, kwargs)
        processed_orders: List[BracketOrder] = []
        final_positions = None

        try:
            strategy.init()
        except Exception as e:
            print('Strategy initialization throws exception', e)
            print(traceback.format_exc())
            return

        indicator_attrs = {attr: indicator for attr, indicator in strategy.__dict__.items()
                         if any([indicator is item for item in strategy._indicators])}

        start = max((indicator.isna().any(axis=1).argmin() if isinstance(indicator, pd.DataFrame)
                    else indicator.isna().argmin() for indicator in indicator_attrs.values()), default=0)
        start = max(start, strategy._start_on_day)

        def deframe(df): return df.iloc[:, 0] if isinstance(df, pd.DataFrame) and len(df.columns) == 1 else df
        indicator_attrs_np = {attr: deframe(indicator).to_numpy() for attr, indicator in indicator_attrs.items()}
        self._strategy.indicator_attrs_np = indicator_attrs_np

        with np.errstate(invalid='ignore'):
            for i in range(start, len(self._data)):
                data._set_length(i + 1)
                for attr, indicator in self._strategy.indicator_attrs_np.items():
                    setattr(strategy, attr,
                            _Indicator(
                                array=indicator[: i + 1],
                                df=partial(_Indicator.lazy_indexing, indicator_attrs[attr], i + 1)))

                try:
                    broker.next()
                except _OutOfMoneyError:
                    print('Out of money error triggered')
                    break

                strategy.next()
                processed_orders.extend(broker.orders)
            else:
                final_positions = ({t: p.size for t, p in broker.positions.items()}
                                | {'Cash': int(broker.margin_available)})

                if start < len(self._data):
                    broker.finalize()

            data._set_length(len(self._data))

            equity = pd.DataFrame(broker._equity, index=data.index,
                                columns=['Equity', *data.tickers, 'Cash']).bfill().fillna(broker._cash)

            self._results = compute_stats(
                orders=processed_orders,
                trades=broker.closed_trades,
                equity=equity,
                ohlc_data=self._ohlc_ref_data,
                risk_free_rate=0.0,
                strategy_instance=strategy,
                positions=final_positions,
                trade_start_bar=start,
            )

        return self._results.copy()


class _MultiBacktest(MultiBacktest):
    def __init__(self, strategy, *,
                 cash: float = 10_000,
                 holding: dict = {},
                 commission: float = .0,
                 spread: float = .0,
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 trade_start_date=None,
                 lot_size=1,
                 fail_fast=True,
                 storage: dict | None = None,
                 is_option: bool = False,
                 equity_curve: bool = False,
                 load=0.6,
                 look_ahead_bias: bool = False,
                 database_name: str = 'backtest'):
        self.strategy = strategy
        self.cash = cash
        self.commission = commission
        self.holding = holding
        self.spread = spread
        self.margin = margin
        self.trade_on_close = trade_on_close
        self.hedging = hedging
        self.exclusive_orders = exclusive_orders
        self.trade_start_date = trade_start_date
        self.lot_size = lot_size
        self.fail_fast = fail_fast
        self.storage = storage
        self.is_option = is_option
        self.equity_curve = equity_curve
        self.load = load
        self.look_ahead_bias = look_ahead_bias
        self.database_name = database_name
        super().__init__(strategy, cash=cash, holding=holding, commission=commission,
                        spread=spread, margin=margin, trade_on_close=trade_on_close, hedging=hedging,
                        exclusive_orders=exclusive_orders, trade_start_date=trade_start_date,
                        lot_size=lot_size, fail_fast=fail_fast, storage=storage, is_option=is_option,
                        equity_curve=equity_curve, load=load, look_ahead_bias=look_ahead_bias, database_name=database_name)

    def backtest_stock(self, stock, timeframe, market, exchange = None, **kwargs):
        if timeframe.lower() == 'all':
            return self.backtest_stock_mtf(stock, market, exchange, **kwargs)
        data = self.reader.fetch_stock(stock, timeframe, market, exchange)
        for attr in dir(self.strategy):
            if not attr.startswith("__"):
                if attr == 'train_percentage':
                    print("Found train_percentage")
                    train_percentage = getattr(self.strategy,attr)
                    self.trade_start_date = data.index[int(train_percentage * len(data))]
                    base, _ = os.path.splitext(self.caller_filename)
                    self.model_path = base + ".pkl"
        if len(data) == 0:
            print("No data available for the given specifications")
            return
        print("Data fetched")
        bt = _Backtest(data, self.strategy,
                    cash = self.cash,
                    commission = self.commission,
                    holding = self.holding,
                    spread = self.spread,
                    margin = self.margin,
                    trade_on_close = self.trade_on_close,
                    hedging = self.hedging,
                    exclusive_orders = self.exclusive_orders,
                    trade_start_date = self.trade_start_date,
                    lot_size= self.lot_size,
                    fail_fast = self.fail_fast,
                    storage = self.storage,
                    is_option = self.is_option
                    )
        result = bt.run(**kwargs) # Pass the keyword arguments additionally passed
        result['stock_name'] = stock
        result['time_frame'] = timeframe
        result['exchange'] = exchange

        print("Backtest finished")

        if self.look_ahead_bias:    # Only check for look-ahead bias if the flag is set
            self.look_ahead_bias_check(result, bt._results._strategy)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{stock}_tearsheet.html'
        output_directory_path = self.get_root_dir()
        random_number = np.random.rand()
        output_directory_path = os.path.join(output_directory_path, f'multibacktester_output_{timestamp}_{random_number}')
        os.makedirs(output_directory_path)
        self.save_current_script(output_directory_path)
        output_tearsheet_filepath = os.path.join(output_directory_path, filename)
        warnings.filterwarnings("ignore", category=FutureWarning)
        try:
            bt.tear_sheet(results= result,plotting_date = self.trade_start_date, open_browser = False, output_path = output_tearsheet_filepath, equity_curve = self.equity_curve)
            print("Tearsheet generated and saved to",output_tearsheet_filepath)
        except Exception as e:
            print("Error while generating tearsheet for",stock,e)
        try:
            output_plot_filepath = os.path.join(output_directory_path, f'{stock}_plot.html')
            bt.plot(filename=output_plot_filepath, open_browser=False)
        except Exception as e:
            print("Error while generating plot",e)

        result_temp = result
        result_temp['stock_name'] = stock
        result_temp['time_frame'] = timeframe
        result_temp = self.clean_result(result_temp)
        
        # Always save to database
        temp = OutputUpdater(self.database_name)
        strategy_instance = bt._results._strategy
        code_id = str(uuid.uuid4())
        paths = self.get_class_source_paths(strategy_instance)
        for name, path in paths.items():
            temp._store_data(name,path,self.caller_filename,code_id)
        result_temp.pop('_strategy')
        temp.store_result(result_temp,"backtest_results", self.caller_filename,code_id,self.model_path)
        temp.store_code(self.caller_filename,code_id)
        return result

    def backtest_stockchunk(self, data_chunk,timeframe,exchange):
        results = []
        for data_tuple in data_chunk:
            stock, data, keyword_args = data_tuple
            for attr in dir(self.strategy):
                if not attr.startswith("__"):
                    if attr == 'train_percentage':
                        print("Found train_percentage")
                        train_percentage = getattr(self.strategy,attr)
                        self.trade_start_date = data.index[int(train_percentage * len(data))]
            if len(data) == 0:
                print("No data for",stock)
                continue
            print("Backtesting started for",stock)
            try:
                bt = _Backtest(data, self.strategy,
                                cash = self.cash,
                                commission = self.commission,
                                holding = self.holding,
                                spread = self.spread,
                                margin = self.margin,
                                trade_on_close = self.trade_on_close,
                                hedging = self.hedging,
                                exclusive_orders = self.exclusive_orders,
                                trade_start_date = self.trade_start_date,
                                lot_size= self.lot_size,
                                fail_fast = self.fail_fast,
                                storage = self.storage,
                                is_option = self.is_option
                                )
                result = bt.run(**keyword_args) # Pass the keyword arguments additionally passed
                result['stock_name'] = stock
                result['time_frame'] = timeframe
                result['exchange'] = exchange
            except Exception as e:
                print("Error while backtesting",stock,e)
                continue
            print("Backtest finishes for",stock)

            filename = f'{stock}_tearsheet.html'
            output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
            results.append((stock, bt, result, output_tearsheet_filepath))
            try:
                bt.tear_sheet(results= result,plotting_date = self.trade_start_date, open_browser = False, output_path = output_tearsheet_filepath, equity_curve=self.equity_curve)
                print("Tearsheet generated for",stock)
            except Exception as e:
                print("Error while generating tearsheet for",stock,e)
            try:
                bt.plot(filename = os.path.join(self.output_plot_directory, f'{stock}_plot.html'), open_browser=False)
            except Exception as e:
                print("Error while generating plot",stock,e)
            
            result_temp = result
            result_temp['stock_name'] = stock
            result_temp['time_frame'] = timeframe
            result_temp = self.clean_result(result)

            # Always save to database
            temp = OutputUpdater(self.database_name)
            strategy_instance = bt._results._strategy
            code_id = str(uuid.uuid4())
            paths = self.get_class_source_paths(strategy_instance)
            for name, path in paths.items():
                temp._store_data(name,path,self.caller_filename,code_id)
            result_temp.pop('_strategy')
            temp.store_result(result_temp,"backtest_results", self.caller_filename,code_id,self.model_path)
            temp.store_code(self.caller_filename,code_id)
        return results

    def backtest_universe_mtf_worker(self, data_tuple):
        stock, market, exchange, kwargs = data_tuple
        # Backtest for all timeframes sequentially
        data_all = self.reader.fetch_stock_alltfs(stock, market, exchange)
        results = []
        for timeframe, data in data_all.items():
            print("Started",stock,timeframe)
            bt = _Backtest(data, self.strategy,
                    cash = self.cash,
                    commission = self.commission,
                    holding = self.holding,
                    spread = self.spread,
                    margin = self.margin,
                    trade_on_close = self.trade_on_close,
                    hedging = self.hedging,
                    exclusive_orders = self.exclusive_orders,
                    trade_start_date = self.trade_start_date,
                    lot_size= self.lot_size,
                    fail_fast = self.fail_fast,
                    storage = self.storage,
                    is_option = self.is_option
                    )
            result = bt.run(**kwargs) # Pass the keyword arguments additionally passed
            result['stock_name'] = stock
            result['time_frame'] = timeframe
            try:
                bt.plot(filename = os.path.join(self.output_plot_directory, f'{stock}_{timeframe}_plot.html'), open_browser=False)
            except Exception as e:
                print(f"Error while plotting {stock} {timeframe}",e)
            filename = f'{stock}_{timeframe}_tearsheet.html'
            output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
            try:
                bt.tear_sheet(results= result,plotting_date = self.trade_start_date, open_browser = False, output_path = output_tearsheet_filepath, equity_curve=self.equity_curve)
                print(f"Tearsheet generated for {stock} {timeframe} and saved to {output_tearsheet_filepath}")
            except Exception as e:
                print("Error while generating tearsheet for",stock,timeframe,e)
            results.append((stock, timeframe, result))
            print("Done",stock,timeframe)

            result_temp = result
            result_temp['stock_name'] = stock
            result_temp['time_frame'] = timeframe
            result_temp = self.clean_result(result)
                        
            # Always save to database
            temp = OutputUpdater(self.database_name)
            strategy_instance = bt._results._strategy
            code_id = str(uuid.uuid4())
            paths = self.get_class_source_paths(strategy_instance)
            for name, path in paths.items():
                temp._store_data(name,path,self.caller_filename,code_id)
            result_temp.pop('_strategy')
            temp.store_result(result_temp,"backtest_results", self.caller_filename,code_id,self.model_path)
            temp.store_code(self.caller_filename,code_id)
        return results

    def backtest_stock_mtf_worker(self, data_tuple):
        stock, timeframe, data, kwargs = data_tuple
        bt = _Backtest(data, self.strategy,
                    cash = self.cash,
                    commission = self.commission,
                    holding = self.holding,
                    spread = self.spread,
                    margin = self.margin,
                    trade_on_close = self.trade_on_close,
                    hedging = self.hedging,
                    exclusive_orders = self.exclusive_orders,
                    trade_start_date = self.trade_start_date,
                    lot_size= self.lot_size,
                    fail_fast = self.fail_fast,
                    storage = self.storage,
                    is_option = self.is_option
                    )
        result = bt.run(**kwargs) # Pass the keyword arguments additionally passed
        result['stock_name'] = stock
        result['time_frame'] = timeframe
        filename = f'{stock}_{timeframe}_tearsheet.html'
        output_tearsheet_filepath = os.path.join(self.output_tearsheet_directory, filename)
        try:
            bt.plot(filename = os.path.join(self.output_plot_directory, f'{stock}_{timeframe}_plot.html'), open_browser=False)
        except Exception as e:
            print(f"Error while plotting {stock} {timeframe}",e)
            raise
        try:
            bt.tear_sheet(results= result,plotting_date = self.trade_start_date, open_browser = False, output_path = output_tearsheet_filepath, equity_curve=self.equity_curve)
            print(f"Tearsheet generated for timeframe {timeframe} and saved to {output_tearsheet_filepath}")
        except Exception as e:
            print("Error while generating tearsheet for",stock,timeframe,e)

        result_temp = result
        result_temp['stock_name'] = stock
        result_temp['time_frame'] = timeframe
        result_temp = self.clean_result(result)
        
        # Always save to database
        temp = OutputUpdater(self.database_name)
        strategy_instance = bt._results._strategy
        code_id = str(uuid.uuid4())
        paths = self.get_class_source_paths(strategy_instance)
        for name, path in paths.items():
            temp._store_data(name,path,self.caller_filename,code_id)
        result_temp.pop('_strategy')
        temp.store_result(result_temp,"backtest_results", self.caller_filename,code_id,self.model_path)
        temp.store_code(self.caller_filename,code_id)
        return (stock, timeframe, result)
