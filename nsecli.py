#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' 
    NSECLI is a command line application for fetching live stock quotes 
    for Indian stocks. It uses NSE data as the backend for getting the live 
    quotes. 

    It provides a rich command line interface to most of the important features 
    available on National Stock Exchange's (NSE) official website. Apart from 
    fetching live quotes for stocks, this app can also provide indices data, 
    top gainers, top losers etc.


    Key Features:
    - Full featured CLI interface for accessing Indian Stock Quotes.
    - Extremely fast access time. Gets a quote in less than 200 mili seconds.
    - User can configure the fields displayed in the stock quotes.
    - No need to remember stock code, it provides a fuzzy match in case of typos.
    - Whole application is shipped as a single file.
    - Completely documented features with examples.
    - Uses only python standard modules hence hassle free installation.
    - All users options are persistently stored in sqlite database.

    For any details and use cases please refer to www.readthedocs.nsecli.com
'''

__author__ = "Vivek Jha"
__copyright__ = "Copyright 2014"
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Vivek Jha"
__email__ = "vsjha18@gmail.com"
__status__ = "Production"

try:
    from urllib2 import HTTPError, URLError
    from cookielib import CookieJar
    import urllib2
    import urllib
    # import lxml.etree
    import ast
    import sys
    import sqlite3
    import os
    import argparse
    import logging
    import re
except Exception, err:
    print 'error while importing module or package'
    print str(err)
    exit()

class NseCliApp(object):
    ''' This is the main framework class which acts as a controller for 
    for this application. It provide utilty methods to configure database,
    store and fetch user settings, and handling all the command line options.
    '''

    def __init__(self, db):
        global LOG_LEVEL
        logging.basicConfig(level=LOG_LEVEL)
        self.log = logging.getLogger('App')
        self.db = db


    def init_db(self):
        ''' initialyzes the database:
        - creates a table with the list of all stocks
        - creates a table to store user configuration
        '''
        db.create_stocks_table(nse.download_stock_csv())
        db.create_config_table()
        db.init = True

    def get_current_display_fields(self):
        ''' returns a list of all current display fields '''
        display_fields = self.db.get_config_setting('DISPLAY_FIELDS')
        return display_fields

    def get_all_display_fields(self):
        ''' return a list of all display fields '''
        all_display_fields = self.db.get_config_setting('ALL_DISPLAY_FIELDS')
        return all_display_fields

    def add_display_fields(self, fields):
        ''' adds a list of display fields to the current display fields '''
        self.log.debug('display fields to be added: %s' % fields)
        all_display_fields = self.db.get_config_setting('ALL_DISPLAY_FIELDS')
        current_display_fields = self.db.get_config_setting('DISPLAY_FIELDS')
        FLAG_1 = False
        FLAG_2 = False
        exists = []
        invalid = []

        for field in fields:
            # check of the given fields is already displayed
            if field in current_display_fields:
                exists.append(field)
                FLAG_1 = True
            # check in the given field is valid
            if field not in all_display_fields:
                invalid.append(field)
                FLAG_2 = True
        if FLAG_1 is True:
            print 'field %s already exists' % exists
        if FLAG_2 is True:
            print 'field %s is invalid' % invalid
        if FLAG_1 is True or FLAG_2 is True:
            print 'please provide valid inputs'
            sys.exit()

        # update the data base with current field
        current_display_fields += fields
        self.db.update_config_setting('DISPLAY_FIELDS',current_display_fields)

    def remove_display_fields(self, fields):
        ''' remove the list of fields from the list of display fields '''
        self.log.debug('removing display fields: %s' % fields)
        current_display_fields = self.db.get_config_setting('DISPLAY_FIELDS')
        FLAG = False
        invalid = []

        for field in fields:
            # check if the given fields is the part of current display field
            if field not in current_display_fields:
                invalid.append(field)
                FLAG = True
            else:
                current_display_fields.remove(field)
        if FLAG is True:
            print "field %s doesn't exist in current display fields" % invalid
            print 'please provide valid inputs'
            sys.exit()

        # update the data base with current field
        self.db.update_config_setting('DISPLAY_FIELDS', current_display_fields)

    def reset_display_fields(self):
        ''' resets all the display fields to the default one '''
        self.log.debug('reseting DISPLAY_FIELDS setting')
        default_display_fields = self.db.get_config_setting(\
                                        'DEFAULT_DISPLAY_FIELDS')
        self.db.update_config_setting('DISPLAY_FIELDS', default_display_fields)



class NseDisplay(object):
    ''' NseDisplay contains all the function related to displaying
    and controlling display of results and quotes.
    '''
    def __init__(self, db, header=True):
        global LOG_LEVEL
        logging.basicConfig(level=LOG_LEVEL)
        self.log = logging.getLogger('NseDisplay')
        self.db = db
        self.header = header

    def show_quote(self, quote, display_fields, stock_name = None):
        ''' displays the quote based on the list of display fields
        quote is dictionary received from NSE
        '''
        self.print_header(stock_name)
        for field in display_fields:
            if field == 'pChange':
                print '%-15s : %s' % (field, quote[field]) + '%'
            else:
                print '%-15s : %s' % (field, quote[field])
                # print field, ':', quote[field]

        #TODO: check if the quote contains that field


    def show_current_display_fields(self, fields):
        ''' shows current display fields '''
        self.print_header('Current Display Fields')
        for field in fields:
            print field

    def show_all_display_fields(self, fields):
        ''' accepts a list and display it '''
        self.print_header('ALL DISPLAY FIELDS')
        for field in fields:
            print field

    def print_header(self, string):
        ''' prints a string like a header if self.header is
        set to True, else it doesnt print anything'''
        if self.header is True and string is not None:
            l = len(string)
            print '-'*l
            print string
            print '-'*l


class NseDriver(object):
    ''' it accepts a Stock object and fetches it price
    assosiated information'''

    def __init__(self, db):
        # logging.basicConfig(level=logging.DEBUG)
        global LOG_LEVEL
        logging.basicConfig(level=LOG_LEVEL)
        self.log = logging.getLogger('NseDriver')
        self.db = db
        self.baseurl = 'http://nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?'
        self.top_gainer_url = 'http://www.nseindia.com/live_market/dynaContent/live_analysis/gainers/niftyGainers1.json'
        self.opener = self.build_opener()
        self.headers = self.build_headers()
        self.xpath = '//*[@id="responseDiv"]'
        self.code_csv_url = 'http://www.nseindia.com/content/equities/EQUITY_L.csv'

    def get_quote(self, code):
        ''' gets the stock details by querying the market'''
        # TODO: Handle invalid stock codes
        url = self.build_url(code)
        request = urllib2.Request(url, None, self.headers)
        try:
            res = self.opener.open(request)
        except HTTPError as error:
            self.log.error('unable to open the link %s' % url)
            self.log.error(str(error))
            sys.exit()
        except URLError as error:
            self.log.error('no internet connection')
            self.log.error(str(error))
            sys.exit()
        try:
            match = re.search(\
                    r'\{<div\s+id="responseDiv"\s+style="display:none">\s+(\{.*?\{.*?\}.*?\})',
                    res.read(), re.S
                )
            quote = ast.literal_eval(match.group(1))['data'][0]
            # code using lxml
            # parser = lxml.etree.HTMLParser(encoding='utf-8')
            # tree = lxml.etree.fromstring(res.read(), parser)
            # doi = tree.xpath(self.xpath)
            # quote = ast.literal_eval(doi[0].text.strip())['data'][0]

        except Exception, err:
            # control can come here when the stock code is invalid
            print str(err)
            print '"%s" is invalid stock code' % code
            print 'If you are not sure about the stock code, try typing few characters of company name'
            print 'probable list based on current match:'
            self.print_probable_matches(code)
            sys.exit()
        else:
            return quote
    def get_top_gainers(self):
        url = self.top_gainer_url
        request = urllib2.Request(url, None, self.headers)
        try:
            res = self.opener.open(request)
        except HTTPError as error:
            self.log.error('unable to open the link %s' % url)
            self.log.error(str(error))
            sys.exit()
        except URLError as error:
            self.log.error('no internet connection')
            self.log.error(str(error))
            sys.exit()
        import json
        res = res.read()

    def build_headers(self):
        ''' builds the headers for making http request '''
        headers = {'Accept' : '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Host':    'nseindia.com',
            'Referer': 'http://nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?symbol=INFY&illiquid=0',
            'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
            'X-Requested-With':    'XMLHttpRequest'
            }
        return headers

    def download_stock_csv(self):
        ''' downloads the csv file '''
        try:
            request = urllib2.Request(self.code_csv_url, None, self.headers)
            res = self.opener.open(request)
        except HTTPError as error:
            print 'unable to open the link %s' % self.code_csv_url
            print str(error)
        except URLError as error:
            print 'no internet connection'
            print str(error)
        return res.read()

    def build_opener(self):
        ''' builds the opener required for the making http req '''
        cj = CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        return opener

    def build_url(self, code):
        ''' makes the right url string for fetching a quote '''
        encoded_args = urllib.urlencode({'symbol':code, 'illiquid': '0'})
        url = self.baseurl + encoded_args
        return url

    def print_probable_matches(self, code):
        ''' list all the probable matches of stocks and
        there respective codes
        '''
        sdict = self.db.get_all_stock_list()
        for key, value in sdict.iteritems():
            if code.lower() in value.lower():
                print key,'\t\t', value



class DB(object):
    ''' This class abstracts all the data access needs for other classes.
    It also makes sure database is created and connected when the application
    is used first time and database is connected when application is used
    later. None of the classes in the system, except this class should attempt
    to connect to the database.
    All the other classes in the system which needs context and db awareness
    should accept this class as one of constructor requirement
    '''
    def __init__(self, db_path):
        global LOG_LEVEL
        logging.basicConfig(level=LOG_LEVEL)
        self.log = logging.getLogger('DB')
        self.db_path = db_path
        self.init = None
        if not os.path.isfile(self.db_path):
            self.log.debug('db file not present, initialization required')
            self.init = False
        else:
            self.log.debug('db file present no initialization required')
            self.init = True
        try:
            self.db = sqlite3.connect(self.db_path)
        except Exception, err:
            self.log.error('Error while connecting to database')
            self.log.error(str(err))
            sys.exit()

    def create_stocks_table(self, csv):
        ''' creates the stocks table in the database '''
        # delete the table if it is already present
        self.db.execute('DROP TABLE IF EXISTS STOCKS')
        c = self.db.cursor()
        try:
            self.db.execute('CREATE TABLE STOCKS\
                            (ID INTEGER PRIMARY KEY AUTOINCREMENT, CODE TEXT, NAME TEXT)')
        except Exception, e:
            self.log.error('stocks table already exists !!')
            print str(e)
            sys.exit()

        c = self.db.cursor()
        try:
            for line in csv.split('\n'):
                # skip the header line
                if 'NAME OF COMPANY' in line:
                    continue
                # skip the blank lines, last line comes as a blank line
                if not line:
                    continue
                else:
                    code, name = line.split(',')[0:2]
                    c.execute('INSERT INTO STOCKS (CODE,NAME) VALUES("%s","%s")' % (code,name))
        except Exception, e:
            self.log.error('error while inserting rows to stocks table from csv file')
            self.log.error(str(e))
            self.db.rollback()
        else:
            self.db.commit()
        self.log.debug('all rows inserted to stocks table successfully')

    def create_config_table(self):
        ''' creates a table named 'config' to store application config '''

        self.db.execute('DROP TABLE IF EXISTS CONFIG')
        c = self.db.cursor()
        try:
            self.db.execute('CREATE TABLE CONFIG\
                            (ID INTEGER PRIMARY KEY AUTOINCREMENT,\
                            SETTING TEXT, VALUE TEXT)')
        except Exception, e:
            self.log.error('config table already exists !!')
            print str(e)
            sys.exit()
        self.log.debug('config table created')

        # create a row with default fields to show
        c = self.db.cursor()
        try:
            # TODO: SETTING field must be unique
            c.execute("INSERT INTO CONFIG (SETTING, VALUE) VALUES(\
                      'DISPLAY_FIELDS', \
                      'lastPrice change pChange open dayHigh dayLow closePrice previousClose high52 low52')")
            c.execute("INSERT INTO CONFIG (SETTING, VALUE) VALUES(\
                      'DEFAULT_DISPLAY_FIELDS', \
                      'lastPrice change pChange open dayHigh dayLow closePrice previousClose high52 low52')")
        except Exception, err:
            self.log.error('error while inserting DISPLAY_FIELDS or DEFAULT_DISPLAY_FIELDS setting')
            self.log.error(str(err))
            self.db.rollback()
            sys.exit()
        else:
            self.db.commit()
            self.log.debug('DISPLAY_FIELDS & DEFAULT_DISPLAY_FIELDS setting inserted successfully')

        # create a row with all show fields
        all_fields = 'adhocMargin applicableMargin averagePrice bcEndDate' + ' ' + \
            'bcStartDate buyPrice1 buyPrice2 buyPrice3' + ' ' + \
            'buyPrice4 buyPrice5 buyQuantity1 buyQuantity2' + ' ' + \
            'buyQuantity3 buyQuantity4 buyQuantity5 change' + ' ' + \
            'closePrice cm_adj_high cm_adj_high_dt cm_adj_low' + ' ' + \
            'cm_adj_low_dt cm_ffm companyName dayHigh' + ' ' + \
            'dayLow deliveryQuantity deliveryToTradedQuantity exDate' + ' ' + \
            'extremeLossMargin faceValue high52 indexVar' + ' ' + \
            'isinCode lastPrice low52 marketType ' + ' ' + \
            'ndEndDate ndStartDate open pChange' + ' ' + \
            'previousClose priceBand pricebandlower pricebandupper' + ' ' + \
            'purpose quantityTraded recordDate secDate' + ' ' + \
            'securityVar sellPrice1 sellPrice2 sellPrice3' + ' ' + \
            'sellPrice4 sellPrice5 sellQuantity1 sellQuantity2' + ' ' + \
            'sellQuantity3 sellQuantity4 sellQuantity5 series' + ' ' + \
            'symbol totalBuyQuantity totalSellQuantity totalTradedValue' + ' ' + \
            'totalTradedVolume varMargin'
        c = self.db.cursor()
        try:
            # TODO: SETTING field must be unique
            c.execute("INSERT INTO CONFIG (SETTING, VALUE) VALUES(\
                      'ALL_DISPLAY_FIELDS', \
                      '%s')" % all_fields)
        except Exception, err:
            self.log.error('error while inserting ALL_DISPLAY_FIELDS setting')
            self.log.error(str(err))
            self.db.rollback()
            sys.exit()
        else:
            self.db.commit()
            self.log.debug('ALL_DISPLAY_FIELDS setting inserted successfully')

    def get_config_setting(self, setting, ret='as_list'):
        ''' return setting as a list of strings'''
        self.log.debug('getting config setting for %s' % setting)
        c = self.db.cursor()
        try:
            c.execute('SELECT VALUE FROM CONFIG WHERE SETTING = "%s"' % setting)
        except Exception, err:
            self.log.error('error while fetching setting %s' % setting)
            self.log.error(str(err))
            sys.exit()
        res = c.fetchone()[0].split()
        return [str(x) for x in res]

    def update_config_setting(self, setting, value):
        ''' updates a row with the new value in the config table '''
        self.log.debug('updating field %s of config table' % setting)
        self.log.debug('value is :%s' % value)

        if type(value) is list:
            value = " ".join(str(i) for i in value)
        elif type(value) is str:
            pass
        else:
            self.log.error('invalid type for %s, must be list or string'
                           % value)
            sys.exit()
        c = self.db.cursor()
        try:
            c.execute("UPDATE CONFIG SET VALUE = '%s' WHERE SETTING = '%s'" %
                      (value, setting))
        except Exception, err:
            self.log.error('error while updating %s' % setting)
            self.log.error(str(err))
            self.db.rollback()
            sys.exit()
        else:
            self.db.commit()
            self.log.debug('%s setting updated successfully' % setting)

    def get_stock_name(self, code):
        ''' fetches the stock name for the given code '''
        self.log.debug('fetching stock name for %s' % code)
        cur = self.db.cursor()
        try:
            cur.execute("SELECT NAME FROM STOCKS WHERE CODE == '%s'" % code.upper())
            return str(cur.fetchone()[0])

        except Exception, err:
            self.log.error('error while fetching name from stocks table')
            self.log.error(str(err))
            sys.exit()

    def get_all_stock_list(self):
        ''' returns a dict with all stock codes as
        keys and names as values'''
        cur = self.db.cursor()
        try:
            cur.execute('SELECT * FROM STOCKS')
        except Exception, err:
            self.log.error('error while fetch all stocks details')
            sys.exit()
        sdict = {}
        for idx, code, name in cur.fetchall():
            sdict[str(code)] = str(name)
        return sdict



############################
##       MAIN PROG        ##
############################

#### PARSE CLI OPTIONS ########
log = logging.getLogger('NseCli')
log.info('create log')
cparser = argparse.ArgumentParser()
cparser.add_argument('code',
                     nargs = '?',
                     action='store',
                     default = False,
                     help='provide the stock code')

cparser.add_argument('-D',
                     action="store_true",
                     default=False,
                     help='enables debug mode for debugging purpose')

cparser.add_argument('-reset',
                     action="store_true",
                     default=False,
                     help='resets all the display settings')

cparser.add_argument('-current_display_fields',
                     action="store_true",
                     default=False,
                     help='shows current display fields')

cparser.add_argument('-all_display_fields',
                     action="store_true",
                     default=False,
                     help='shows all possible display fields')

cparser.add_argument('-add_display_fields',
                     action="store",
                     nargs = '*',
                     default=False,
                     metavar = '',
                     help='adds a display field')

cparser.add_argument('-remove_display_fields',
                     action="store",
                     nargs = '*',
                     default=False,
                     metavar = '',
                     help='deletes a display fields')

cli = cparser.parse_args()

#### SET LOG LEVEL ####
if cli.D is True:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

#### INSTANTIATE CLASSES ####
dirname, filename = os.path.split(os.path.abspath(__file__))
db = DB(dirname + '/' + 'nse.db')
fw = NseCliApp(db)
nse = NseDriver(db)
disp = NseDisplay(db)

#### INTIALYZE DB FOR THE FIRST TIME USE ####
if db.init is False:
    fw.init_db()

if cli.code is not False:
    # disp.show_quote(nse.get_quote(cli.code))
    quote = nse.get_quote(cli.code)
    fields = fw.get_display_fields()
    name = db.get_stock_name(cli.code)
    disp.show_quote(quote, display_fields=fields, stock_name=name)
    db.get_stock_name(cli.code)

else:
    if cli.current_display_fields is True:
        fields = db.get_config_setting('DISPLAY_FIELDS')
        disp.show_current_display_fields(fields)

    elif cli.all_display_fields is True:
        fields = db.get_config_setting('ALL_DISPLAY_FIELDS')
        disp.show_all_display_fields(fields)

    elif cli.add_display_fields is not False:
        disp.add_display_fields(cli.add_display_fields)

    elif cli.reset is True:
        disp.reset_display_fields()

    elif cli.remove_display_fields is not False:
        disp.remove_display_fields(cli.remove_display_fields)
        # TODO: Add option to print headers
        # TODO: refactor the whole code
        # TODO: One more time think about DB and framework
        # TODO: Add debug logs and sensible handling of exception
        # TODO: documentation and concept of Mixins
        # TODO: option to update the stock list
        # TODO: option to hard_reset

