#!/usr/bin/env python
try:
    from urllib2 import HTTPError, URLError
    from cookielib import CookieJar
    import urllib2
    import urllib
    import lxml.etree
    import ast
    import sys
    import sqlite3
    import os
    import argparse
    import logging
except Exception, err:
    print 'error while imports'
    print str(err)

class Stock(object):
    def __init__(self, code, mkt):
        self.nse = mkt
        self.code = code
        for key, value in self.nse.get_quote(code).items():
            self.__dict__[key] = value

    def get_quote(self):
        ''' uses market object to get the price '''
        pass

    def refresh(self):
        ''' refetches the stock price '''
        pass
    def show_quote(self, quote):
        for key, value in self.__dict__.items():
            print key, '::', value

class NseDriver(object):
    ''' it accepts a Stock object and fetches it price
    assosiated information'''

    def __init__(self, db):
        logging.basicConfig(level=logging.DEBUG)
        self.log = logging.getLogger('NseDriver')
        self.db = db
        self.baseurl = 'http://nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?'
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
            parser = lxml.etree.HTMLParser(encoding='utf-8')
            tree = lxml.etree.fromstring(res.read(), parser)
            # doi = data of interest
            doi = tree.xpath(self.xpath)
            quote = ast.literal_eval(doi[0].text.strip())['data'][0]
        except Exception, err:
            # control can come here when the stock code is invalid
            print '"%s" is invalid stock code' % code
            print 'If you are not sure about the stock code, try typing few characters of company name'
            print 'probable list based on current match:'
            self.print_probable_matches(code)
            sys.exit()
        else:
            return quote

    def show_quote(self, quote):
        ''' controls the display of a quote '''
        display_fields = self.db.get_config_setting('DISPLAY_FILEDS')
        for key in display_fields:
            if key in quote:
                if key == 'pChange':
                    print key, ':', quote[key], '%'
                else:
                    print key, ':', quote[key]
            else:
                print key, 'is not present in the quote'

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

        # create a row with default fileds to show
        c = self.db.cursor()
        try:
            # TODO: SETTING field must be unique
            c.execute("INSERT INTO CONFIG (SETTING, VALUE) VALUES(\
                      'DISPLAY_FILEDS', \
                      'lastPrice change pChange open dayHigh dayLow closePrice previousClose high52 low52')")
        except Exception, err:
            self.log.error('error while inserting DISPLAY_FILEDS setting')
            self.log.error(str(err))
            self.db.rollback()
            sys.exit()
        else:
            self.db.commit()
            self.log.debug('DISPLAY_FILEDS setting inserted successfully')

    def get_config_setting(self, setting):
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

# parse cli options
log = logging.getLogger('NseCli')
log.info('create log')
cparser = argparse.ArgumentParser()
cparser.add_argument('code', action='store', help='provide the stock code')
cparser.add_argument('-D', action="store_true", default=False,\
                     help='enables debug mode for debugging purpose')
cparser.add_argument('-reset', action="store_true", default=False,\
                     help='resets all the settings')
cparser.add_argument('-display_fields', action="store_true", default=False,\
                     help='shows all the possible display fields')
cli = cparser.parse_args()
if cli.D is True:
    logging.basicConfig(level=logging.DEBUG)

dirname, filename = os.path.split(os.path.abspath(__file__))

db = DB(dirname + '/' + 'nse.db')
nse = NseDriver(db)

# initialize the database in case of first time use.
if db.init is False:
    db.create_stocks_table(nse.download_stock_csv())
    db.init = True
    db.create_config_table()
nse.show_quote(nse.get_quote(cli.code))
# TODO: return a stock object which is capable of display functions
