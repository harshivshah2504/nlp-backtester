import math
import numpy as np
from backtester.backtesting import Strategy

class RiskEngine(Strategy):
    def __init__(self, broker, data, params, *args, **kwargs):
        super().__init__(broker, data, params, *args, **kwargs)
        self.total_trades      = len(self.closed_trades)
        # entry_order.id → list of limit‐pyramid Orders
        self.pending_by_order  = {}
        self._cascade_map     = {}   # for “cascade” mode

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
        Returns None if value is NaN.
        """
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None  # or raise, or handle as you need
        pip_size = self.infer_pip_size(entry_price)
        return round(value / pip_size) * pip_size

    def add_buy_trade(self,
                      entry_mode: str = "normal",
                      X_pct:      float = 0.02,
                      Y_pct:      float = 0.5,
                      levels:     int   = 4):
        """
        entry_mode:
           'normal'        → one market fill
           'average_down'  → initial market + limit‐pyramids below entry
           'average_up'    → initial market + stop‐pyramids above entry
           'cascade'       → one market order, then re-enter at each TP until SL
        X_pct: how far (in %) the furthest pyramid is from CMP
        Y_pct: fraction of units to take immediately
        levels: number of pyramids to split the remainder
        """
        # 0) sanity checks
        assert entry_mode in ("normal","average_down","average_up", "cascade")
        assert 0 < Y_pct <= 1
        assert X_pct > 0 or entry_mode=="normal"
        assert levels >= 1 or entry_mode=="normal"
        # 1) compute total_units exactly as before
        risk  = self.risk_management_strategy.get_risk_per_trade()
        entry = float(self.data.Close[-1])
        if entry == 0 or np.isnan(entry):
            last_row = self.data.df.iloc[-1]
            last_index = self.data.df.index[-1]
            print("Suspicious last row at:", last_index, "with data:", last_row.to_dict())
            return
        if risk <= 0:
            return
        sl_raw, tp_raw = self.trade_management_strategy.calculate_tp_sl("buy")
        if sl_raw is None or (isinstance(sl_raw, float) and np.isnan(sl_raw)):
            print("Stop loss is NaN or None, skipping order")
            return
        else:
            sl = self.round_to_pip_size(sl_raw, entry)
            if sl is None:
                print("Rounded stop loss is invalid, skipping order")
                return

        if tp_raw is None or (isinstance(tp_raw, float) and np.isnan(tp_raw)):
            print("Take profit is NaN or None, skipping order")
            return
        else:
            tp = self.round_to_pip_size(tp_raw, entry)
            if tp is None:
                print("Rounded take profit is invalid, skipping order")
                return

        stop_loss_perc = (entry - sl) / entry
        if stop_loss_perc <= 0:
            return

        size_dollars = risk / stop_loss_perc
        if np.isnan(size_dollars) or size_dollars <= 0:
            return

        total_units = math.ceil(size_dollars / entry)
        cash        = self._broker._cash
        max_units   = math.floor(0.9 * cash / entry)
        total_units = min(total_units, max_units)
        if total_units == 0:
            return

        # 2) normal = single market order
        if entry_mode == "normal":
            self.buy(size=total_units, sl=sl, tp=tp)
            return

        # ─── CASCADE ─────────────────────────────────────────────
        if entry_mode == "cascade":
            o = self.buy(size=total_units, sl=sl, tp=tp, tag=None)
            if o is None:
                return
            eid = o.id
            o.tag = eid
            # store for re‐entry whenever TP hits
            self._cascade_map[eid] = dict(size=total_units, sl=abs(entry-sl), tp=abs(entry-tp))
            return

        # 3) initial market slice
        init_units  = math.ceil(total_units * Y_pct)
        entry_order = None
        if init_units > 0:
            entry_order = self.buy(size=init_units,
                                   sl=sl,
                                   tp=tp,
                                   tag=None)    # retag just below
        if entry_order is None:
            # Y_pct>0 assure init_units>0, so we should never get here
            return

        entry_id = entry_order.id
        entry_order.tag = entry_id            # so the resulting Trade.tag == entry_id
        self.pending_by_order[entry_id] = []  # hold onto the limit pyramids

        # 4) split remainder into pyramids
        rem       = total_units - init_units
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

            # for buys: average_down uses limit‐pyramids, average_up uses stop‐pyramids
            if direction == -1:
                pyramid = self.buy(size=qty, limit=price, sl=sl, tp=tp, tag=entry_id)
            else:
                pyramid = self.buy(size=qty, stop=price,  sl=sl, tp=tp, tag=entry_id)

            self.pending_by_order[entry_id].append(pyramid)

    def add_sell_trade(self,
                       entry_mode: str="normal",
                       X_pct:      float=0.02,
                       Y_pct:      float=0.5,
                       levels:     int=4):

        """
            entry_mode:
            normal        = one market order
            average_down  = market slice + STOP ladders on drops
            average_up    = market slice + LIMIT ladders on rallies
            cascade       = one market order, then re-enter at each TP until SL
        """
        # mirror of add_buy_trade for shorts
        assert entry_mode in ("normal","average_down","average_up", "cascade")
        assert 0 < Y_pct <= 1
        assert X_pct > 0 or entry_mode=="normal"
        assert levels >= 1 or entry_mode=="normal"

        risk  = self.risk_management_strategy.get_risk_per_trade()
        entry = float(self.data.Close[-1])
        if entry == 0 or np.isnan(entry):
            last_row = self.data.df.iloc[-1]
            last_index = self.data.df.index[-1]
            print("Suspicious last row at:", last_index, "with data:", last_row.to_dict())
            return
        if risk <= 0:
            return
        sl_raw, tp_raw = self.trade_management_strategy.calculate_tp_sl("sell")
        if sl_raw is None or (isinstance(sl_raw, float) and np.isnan(sl_raw)):
            print("Stop loss is NaN or None, skipping order")
            return
        else:
            sl = self.round_to_pip_size(sl_raw, entry)
            if sl is None:
                print("Rounded stop loss is invalid, skipping order")
                return

        if tp_raw is None or (isinstance(tp_raw, float) and np.isnan(tp_raw)):
            print("Take profit is NaN or None, skipping order")
            return
        else:
            tp = self.round_to_pip_size(tp_raw, entry)
            if tp is None:
                return
        stop_loss_perc = (sl - entry) / entry
        if stop_loss_perc <= 0:
            return

        size_dollars = risk / stop_loss_perc
        if np.isnan(size_dollars) or size_dollars <= 0:
            return

        total_units = math.ceil(size_dollars / entry)
        cash        = self._broker._cash
        max_units   = math.floor(0.9 * cash / entry)
        total_units = min(total_units, max_units)
        if total_units == 0:
            return

        if entry_mode == "normal":
            self.sell(size=total_units, sl=sl, tp=tp)
            return

        # ─── CASCADE ─────────────────────────────────────────────
        if entry_mode == "cascade":
            o = self.sell(size=total_units, sl=sl, tp=tp, tag=None)
            if o is None:
                return
            eid = o.id
            o.tag = eid
            self._cascade_map[eid] = dict(size=total_units, sl=abs(entry-sl), tp=abs(entry-tp))
            return

        init_units  = math.ceil(total_units * Y_pct)
        entry_order = None
        if init_units > 0:
            entry_order = self.sell(size=init_units,
                                    sl=sl,
                                    tp=tp,
                                    tag=None)
        if entry_order is None:
            return

        entry_id = entry_order.id
        entry_order.tag = entry_id
        self.pending_by_order[entry_id] = []

        rem       = total_units - init_units
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

            # for sells: average_down uses stop‐pyramids, average_up uses limit‐pyramids
            if direction == -1:
                pyramid = self.sell(size=qty, stop=price,  sl=sl, tp=tp, tag=entry_id)
            else:
                pyramid = self.sell(size=qty, limit=price, sl=sl, tp=tp, tag=entry_id)

            self.pending_by_order[entry_id].append(pyramid)

    def on_trade_close(self):
        """
        Called each bar—detect newly closed trades,
        update risk manager and cancel any orphan limit orders.
        """
        closed_now = len(self.closed_trades)
        n_new      = closed_now - self.total_trades
        if n_new > 0:
            for tr in self.closed_trades[-n_new:]:

                eid = tr.tag   # this is the .id of your initial order
                
                if tr.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()

                # cascade re-entry
                info = self._cascade_map.pop(eid, None)
                if info:
                    reason = tr.reason
                    if reason == 'TP Hit':
                        # TP hit => re-enter once
                        if tr.size > 0:
                            newo = self.buy(size=info['size'],
                                            stop=tr.exit_price,
                                            sl=tr.exit_price-info['sl'],
                                            tp=tr.exit_price+info['tp'],
                                            tag=None)
                            if newo:
                                nid = newo.id
                                newo.tag = nid
                                self._cascade_map[nid] = info
                        else:
                            newo = self.sell(size=info['size'],
                                            stop=tr.exit_price,
                                            sl=tr.exit_price+info['sl'],
                                            tp=tr.exit_price-info['tp'],
                                            tag=None)
                            if newo:
                                nid = newo.id
                                newo.tag = nid
                                self._cascade_map[nid] = info
                    # else SL hit => do nothing (cascade stops)

                # cancel any leftover pyramids
                for pyramid in self.pending_by_order.pop(eid, []):
                    try:
                        pyramid.cancel()
                    except Exception:
                        pass

        self.total_trades = closed_now