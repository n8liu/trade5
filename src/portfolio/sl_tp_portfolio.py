import csv

from src.portfolio import naive_portfolio
from src import event


class StopLossTakeProfit(naive_portfolio.NaivePortfolio):
    """" Naive Portfolio with a Stop Loss and Take Profit."""
    def __init__(self, events, equity):
        self.events = events
        self.holdings = {}
        self.updated_list = {}
        self.history = []
        self.equity = [equity]
    
    def create_order(self, q_event):
        """
        Append an OrderEvent to the queue (typically after receiving a SignalEvent 
        from a strategy object, or after a MarketEvent hits a stoploss or takeprofit). 
        """
        with open("example.csv", 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([q_event.get_direction(), q_event.get_candle(), q_event.get_ticker()])

        self.events.append(event.OrderEvent(
            direction=q_event.get_direction(), 
            datetime=q_event.get_candle(),
            ticker=q_event.get_ticker(),
            quantity=1000
        ))
    
    def create_single_order(self, q_event):
        """
        Get a SignalEvent and enter accordingly, but also get rid of the 
        other holdings.
        """
        # if we're at the last signal event, process it and update the update_list
        if isinstance(self.events[0], event.SignalEvent) and len(self.events) == 1:
            self.updated_list[q_event.get_ticker()] = {
                'ticker': q_event.get_ticker(), 
                'direction': q_event.get_direction(), 
                'candle': q_event.get_candle()
            }
            # for each pair in the updated list, check if it's already in holdings
            # if the pair is in holidngs, do nothing.
            # if the pair is not in holdings,
            for pair in self.updated_list:
                if self.updated_list[pair]['ticker'] not in self.holdings:
                    # enter pairs not currently holding:
                    self.events.append(event.OrderEvent(
                        direction=self.updated_list[pair]['direction'], 
                        datetime=self.updated_list[pair]['candle'],
                        ticker=self.updated_list[pair]['ticker'], 
                        quantity=1000
                    ))
            for h in self.holdings:
                if self.holdings[h]['ticker'] not in self.updated_list: 
                    # leave pairs that aren't in updated list
                    self.events.append(event.OrderEvent(
                            direction=1 if self.holdings[h]['direction']==-1 else -1, 
                            datetime=self.holdings[h]['candle'],
                            ticker=self.holdings[h]['ticker'],
                            quantity=self.holdings[h]['quantity']
                        ))
            self.updated_list = {}
        else:
            self.updated_list[q_event.get_ticker()] = {
                'ticker': q_event.get_ticker(), 
                'direction': q_event.get_direction(),
                'candle': q_event.get_candle()
            }

    def create_close_order(self, ticker, direction, datetime, price, quantity=1000):
        """For takeprofit / stoploss caused OrderEvents. """
        print(ticker, 'closed')
        self.events.append(event.OrderEvent(
            direction=direction*-1, 
            datetime=datetime,
            ticker=ticker,
            price=price,
            quantity=quantity
        ))

    def update(self, q_event):
        """
        After receiving a FillEvent, update internal data to the FillEvent's 
        specifications.
        """
        if q_event.get_ticker() in self.holdings: # if an open order needs to be closed
            holding = self.holdings[q_event.get_ticker()]
            self.history.append({
                'ticker': holding['ticker'],
                'direction': holding['direction'],
                'price': holding['price'],
                'return': self.calculate_return(holding['ticker'], holding['direction'], holding['price'], q_event.get_price(), holding['pip_value']),
                'pip_value': holding['pip_value']
            })
            self.equity.append(self.equity[-1] + self.calculate_return(holding['ticker'], holding['direction'], holding['price'], q_event.get_price(), holding['pip_value']))
            del self.holdings[q_event.get_ticker()]
        else: # add order to holdings
            self.holdings[q_event.get_ticker()] = {
                'ticker': q_event.get_ticker(),
                'direction': q_event.get_direction(),
                'quantity': q_event.get_quantity(),
                'price': q_event.get_price(),
                'pip_value': q_event.get_pip_val(),
                'margin': q_event.get_margin(),
                'candle': q_event.get_candle(),
                'stop_loss': self.set_stop_loss(q_event.get_ticker(), q_event.get_direction(), q_event.get_price(), 500),
                'take_profit': self.set_take_profit(q_event.get_ticker(), q_event.get_direction(), q_event.get_price(), 400)
            }

    def check_if_close_triggered(self, q_event):
        """Takes a MarketEvent and checks if the candle would have triggered one of the 
        holdings to close. """
        if isinstance(q_event, event.MultipleMarketEvent):
            for e in q_event.get_market_events():
                if e.get_ticker() in self.holdings:
                    tick = e.get_ticker()
                    _dir = self.holdings[tick]['direction']
                    date = e.get_data()[-1]
                    bid = e.get_data()[-1]['bid']
                    ask = e.get_data()[-1]['ask']

                    if _dir < 0: # if short (buy ask)
                        if ask[1] >= self.holdings[tick]['stop_loss']:
                            # create an OrderEvent, pop holding out of holdings and into history
                            self.create_close_order(tick, _dir, date, self.holdings[tick]['stop_loss'])
                        elif ask[2] <= self.holdings[tick]['take_profit']:
                            # create an OrderEvent, pop holding out of holdings and into history
                            self.create_close_order(tick, _dir, date, self.holdings[tick]['take_profit'])
                    elif _dir > 0: # if long (sell bid)
                        if bid[2] <= self.holdings[tick]['stop_loss']:
                            self.create_close_order(tick, _dir, date, self.holdings[tick]['stop_loss'])
                        elif bid[1] >= self.holdings[tick]['take_profit']:
                            self.create_close_order(tick, _dir, date, self.holdings[tick]['take_profit'])

        elif isinstance(q_event, event.MarketEvent):
            if q_event.get_ticker() in self.holdings:
                tick = q_event.get_ticker()
                _dir = self.holdings[tick]['direction']
                date = q_event.get_data()[-1]
                bid = q_event.get_data()[-1]['bid']
                ask = q_event.get_data()[-1]['ask']

                if _dir < 0: # if short (buy bid)
                    if bid[1] > self.holdings[tick]['stop_loss']:
                        # create an OrderEvent, pop holding out of holdings and into history
                        self.create_close_order(tick, _dir, date, self.holdings[tick]['stop_loss'])
                    elif bid[2] < self.holdings[tick]['take_profit']:
                        # create an OrderEvent, pop holding out of holdings and into history
                        self.create_close_order(tick, _dir, date, self.holdings[tick]['take_profit'])
                elif _dir > 0: # if long (sell ask)
                    if ask[2] < self.holdings[tick]['stop_loss']:
                        self.create_close_order(tick, _dir, date, self.holdings[tick]['stop_loss'])
                    elif ask[1] < self.holdings[tick]['take_profit']:
                        self.create_close_order(tick, _dir, date, self.holdings[tick]['take_profit'])

    # utility functions
    def set_stop_loss(self, ticker, direction, price, pips):
        if ticker.startswith('JPY') or ticker.endswith('JPY'):
            if direction > 0:
                sl = price - 0.01*pips 
            elif direction < 0:
                sl = 0.01*pips + price
        else:
            if direction > 0:
                sl = price - 0.0001*pips
            elif direction < 0:
                sl = 0.0001*pips + price
        return sl
                
    def set_take_profit(self, ticker, direction, price, pips):
        if ticker.startswith('JPY') or ticker.endswith('JPY'):
            if direction > 0:
                tp = 0.01*pips + price
            elif direction < 0:
                tp = 0.01*pips - price
        else:
            if direction > 0:
                tp = 0.0001*pips + price
            elif direction < 0:
                tp = 0.0001*pips - price
        return tp
    
    def calculate_return(self, ticker, direction, price, new_price, pip_value):
        if ticker.startswith('JPY') or ticker.endswith('JPY'):
            rate = 0.01
        else:
            rate = 0.0001
        if direction > 0: # if we selling a long
            return (new_price - price) / rate * pip_value
        elif direction < 0: # if we covering a short
            return (price - new_price) / rate * pip_value

    #getters and setters
    def get_all_holdings(self):
        return self.holdings
    
    def get_events(self):
        return self.events

    def get_equity(self):
        return self.equity
    
    def get_history(self):
        return self.history

    def get_holding(self, ticker):
        return self.holdings[ticker]
    
    def set_holding(self, ticker, direction, quantity, price, stop_loss, take_profit):
        self.holdings[ticker] = {
            'ticker': ticker,
            'direction': direction,
            'quantity': quantity,
            'price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
