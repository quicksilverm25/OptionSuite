import strategy
from events import signalEvent
from datetime import datetime, timedelta
import pytz

class StrangleStrat(strategy.Strategy):
    """This class sets up the basics for a SPECIFIC strategy that will be used;
       In this case, we set up the strangle strategy, which involves buying or
       selling strangles with certain parameters
       
       Strangle specific attributes:
           optCallDelta:  optimal delta for call, usually around 16 delta
           maxCallDelta:  max delta for call, usually around 30 delta
           optPutDelta:  optimal delta for put, usually around 16 delta
           maxPutDelta:  max delta for put, usually around 30 delta


       General strategy attributes:
            startDateTime:  date/time to start the live trading or backtest
            strategy:  option strategy to use -- e.g., iron condor, strangle
            buyOrSell:  do we buy an iron condor or sell an iron condor? 0 = buy, 1 = sell
            underlying:  which underlying to use for the strategy
            orderQuantity:  number of strangles, iron condors, etc
            daysBeforeClose:  number of days before expiration to close the trade

            optional attributes:

            expCycle:  specifies if we want to do monthly ('m'); unspecified means we can do weekly, quarterly, etc
            optimalDTE:  optimal number of days before expiration to put on strategy
            minimumDTE:  minimum number of days before expiration to put on strategy
            roc:  minimal return on capital for overall trade as a decimal
            minDaysToEarnings:  minimum number of days to put on trade before earnings
            minCredit:  minimum credit to collect on overall trade
            maxBuyingPower:  maximum buying power to use on overall trade
            profitTargetPercent:  percentage of initial credit to use when closing trade
            avoidAssignment:  boolean -- closes out trade using defined rules to avoid stock assignment
            maxBidAsk:  maximum price to allow between bid and ask prices of option (for any strike or put/call)
            maxMidDev:  maximum deviation from midprice on opening and closing of trade (e.g., 0.02 cents from midprice)
            minDaysSinceEarnings:  minimum number of days to wait after last earnings before putting on strategy
            minIVR:  minimum implied volatility rank needed to put on strategy
    """

    def __init__(self, eventQueue, optCallDelta, maxCallDelta, optPutDelta, maxPutDelta, startTime, buyOrSell,
                 underlying, orderQuantity, daysBeforeClose, expCycle=None, optimalDTE=None,
                 minimumDTE=None, roc=None, minDaysToEarnings=None, minCredit=None, maxBuyingPower=None,
                 profitTargetPercent=None, avoidAssignment=None, maxBidAsk=None, minDaysSinceEarnings=None,
                 minIVR=None):

        #For arguments that are not supported or don't have implementations, we return an exception to prevent confusion
        if not roc == None:
            raise NotImplementedError, "Specifying ROC currently not supported"

        if not minDaysToEarnings == None or not minDaysSinceEarnings == None:
            raise NotImplementedError, "Ability to filter out dates with respect to earnings currently not supported"

        if not avoidAssignment == None:
            raise NotImplementedError, "Strategy for avoiding assignment currently not implemented / supported"

        if not minIVR == None:
            raise NotImplementedError, "Specifying implied volatility rank currently not implemented / supported"

        if not maxBuyingPower == None:
            raise NotImplementedError, "Specifying max buying power not implemented / supported"

        self.__eventQueue = eventQueue
        self.__strategy = "strangle"
        self.__optCallDelta = optCallDelta
        self.__maxCallDelta = maxCallDelta
        self.__optPutDelta = optPutDelta
        self.__maxPutDelta = maxPutDelta

        strategy.Strategy.__init__(self, startTime, self.__strategy, buyOrSell, underlying, orderQuantity,
                                   daysBeforeClose, expCycle, optimalDTE, minimumDTE, roc, minDaysToEarnings,
                                   minCredit, maxBuyingPower, profitTargetPercent, avoidAssignment,
                                   maxBidAsk, minDaysSinceEarnings, minIVR)

    def getOptimalCallDelta(self):
        return self.__optCallDelta

    def getMaxCallDelta(self):
        return self.__maxCallDelta

    def getOptimalPutDelta(self):
        return self.__optPutDelta

    def getMaxPutDelta(self):
        return self.__maxPutDelta

    def checkForSignal(self, event):
        """Criteria that we need to check before generating a signal event:

        Required:
        optCallDelta:  optimal delta for call, usually around 16 delta
        maxCallDelta:  max delta for call, usually around 30 delta
        optPutDelta:  optimal delta for put, usually around 16 delta
        maxPutDelta:  max delta for put, usually around 30 delta
        startDateTime:  date/time to start the live trading or backtest
        strategy:  option strategy to use -- e.g., iron condor, strangle
        buyOrSell:  do we buy an iron condor or sell an iron condor? 0 = buy, 1 = sell
        underlying:  which underlying to use for the strategy
        orderQuantity:  number of strangles, iron condors, etc
        daysBeforeClose:  number of days before expiration to close the trade

        Optional:
        expCycle:  specifies if we want to do monthly ('m'); unspecified means we can do weekly, quarterly, etc
        optimalDTE:  optimal number of days before expiration to put on strategy
        minimumDTE:  minimum number of days before expiration to put on strategy
        roc:  minimal return on capital for overall trade as a decimal
        minDaysToEarnings:  minimum number of days to put on trade before earnings
        minCredit:  minimum credit to collect on overall trade
        maxBuyingPower:  maximum buying power to use on overall trade
        profitTargetPercent:  percentage of initial credit to use when closing trade
        avoidAssignment:  boolean -- closes out trade using defined rules to avoid stock assignment
        maxBidAsk:  maximum price to allow between bid and ask prices of option (for any strike or put/call)
        maxMidDev:  maximum deviation from midprice on opening and closing of trade (e.g., 0.02 cents from midprice)
        minDaysSinceEarnings:  minimum number of days to wait after last earnings before putting on strategy
        minIVR:  minimum implied volatility rank needed to put on strategy

        We go through each option in the option chain and find all of the options that meet the criteria.  If there
        are multiple options that meet the criteria, we choose the first one, but we could use some other type of
        rule for choosing.
        """

        #Get the data from the tick event
        eventData = event.getData()

        #These temporary variables will be used to keep track of the optimal options as we go through the options
        #chain
        optimalCallOpt = []
        optimalCallDelta = None
        optimalPutOpt = []
        optimalPutDelta = None

        #Process one option at a time from the option chain (now objects of option class)
        for option in eventData:

            #First check if the option is a call or a put
            if option.getOptionType() == 'CALL':
                if self.getExpCycle() == 'm': #monthly options specified
                    if not self.isMonthlyExp(option.getDTE()):
                        continue

                #Check min DTE
                if not self.getMinimumDTE() == None:
                    if not self.hasMinimumDTE(option.getDateTime(), option.getDTE()):
                        continue

                #Check that call delta is less or equal to than max call delta specified
                if not option.getDelta() <= self.getMaxCallDelta():
                    continue

                #Check if optimalCallDelta has been set from a previous iteration;
                #If the current iteration has a delta closer to optCallDelta, save this option
                if optimalCallDelta == None:
                    optimalCallOpt = option
                    optimalCallDelta = option.getDelta()
                    #print('Call found at delta {}'.format(option.getDelta()))
                else:
                    curDelta = option.getDelta()
                    optCurDelta = self.getOptimalCallDelta()
                    if abs(curDelta - optCurDelta) <  abs(optimalCallDelta - optCurDelta):
                        optimalCallOpt = option
                        optimalCallDelta = option.getDelta()

            elif option.getOptionType() == 'PUT':
                if self.getExpCycle() == 'm': #monthly options specified
                    if not self.isMonthlyExp(option.getDTE()):
                        continue

                #Check min DTE
                if not self.getMinimumDTE() == None:
                    if not self.hasMinimumDTE(option.getDateTime(), option.getDTE()):
                        continue

                #Check that put delta is greater than or equal to max put delta specified
                if not option.getDelta() >= self.getMaxPutDelta():
                    continue

                #Check if optimalPutDelta has been set from a previous iteration;
                #If the current iteration has a delta closer to optPutDelta, save this option
                if optimalPutDelta == None:
                    optimalPutOpt = option
                    optimalPutDelta = option.getDelta()
                    #print('Put found at delta {}'.format(option.getDelta()))
                else:
                    curDelta = option.getDelta()
                    optCurDelta = self.getOptimalPutDelta()
                    if abs(curDelta - optCurDelta) <  abs(optimalPutDelta - optCurDelta):
                        optimalPutOpt = option
                        optimalPutDelta = option.getDelta()

        #Must check that a CALL and PUT were found which meet criteria and are in the same expiration
        if optimalPutOpt and optimalCallOpt and optimalPutOpt.getDTE() == optimalCallOpt.getDTE():
            #Temporarily add the optimal put and optimal call to an array for testing; we will create
            #a strangle option primitive in the actual system; the strangle primitive will have several of the
            #arguments from the init of StrangleStrat class
            tempData = [optimalPutOpt, optimalCallOpt]
            #Create signal event to put on strangle strategy and add to queue
            event = signalEvent.SignalEvent()
            event.createEvent(tempData)
            #self.__eventQueue.put(event)

        #return eventData

    def isMonthlyExp(self, dateTime):
        '''
        Check if the option expiration falls on the third Friday of the month, or if the third Friday is a holiday,
        check if the expiration falls on the Thursday that preceeds it
        Technically, the option expire on a Saturday, so we need to subtract a day from the date and check if the day
        is the third friday of the month
        :param dateTime: option expiration date in mm/dd/yy format
        :return: true if it's a monthly option; false otherwise
        '''

        #Subtract one from expiration date to get the Friday before expiration (independent of holidays)
        adjustDate = dateTime - timedelta(days=1)

        return (adjustDate.weekday() == 4 and 14 < adjustDate.day < 22)

        #return ((dateTime.weekday() == 4 or dateTime.weekday() == 3) and 14 < dateTime.day < 22)

    def hasMinimumDTE(self, curDateTime, expDateTime):
        '''
        Determine if the current expiration date of the option is >= self.minimumDTE days from the current date
        :param curDateTime: current date in mm/dd/yy format
        :param expDateTime: option expiration date in mm/dd/yy format
        :return: true if difference between current date and dateTime is >= self.minimumDTE; else false
        '''
        return (expDateTime - curDateTime).days >= self.getMinimumDTE()