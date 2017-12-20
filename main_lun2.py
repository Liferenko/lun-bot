#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup as BS
from fake_useragent import UserAgent
import traceback
import time
from urllib.parse import urlparse
import re

URL = 'https://www.lun.ua/продажа-квартир-киевская-область'

HEADERS = {}
PROXY = {}
KEYWORD = 'Владелец'
DOMAIN = 'https://www.lun.ua'
agent = UserAgent()

class LUN:
    def __init__(self):
        self.agent = agent.random
        self.sess = requests.session()
        self.domain = DOMAIN
    def sending_request(self, url, headers = HEADERS, proxy = PROXY, set_agent = True):
        """
        Sending request 10 times
        :param url:
        :param headers:
        :param proxy:
        :return:
        """
        if set_agent:
            headers['User-Agent'] = self.agent
        idx = 9
        while idx > 0:
            try:
                r = self.sess.get(url = url, headers = headers, proxies = proxy)
                if r.status_code == 200:
                    return r
            except:
                traceback.print_exc()
            idx -= 1
        else:
            return None
    def correct_url(self, domain, url):
        """
        check if url is relative or full (starts with domain or not),
        :param domain:
        :param url:
        :return: full url
        """
        if not url.startswith(domain):
            url = domain + url
        return url
    def analyze_start_page(self, url):
        """analyze items (is keyword in item text or not) at pages + pagination, with saving links into list 'links' and returning it"""
        links = []
        counter = 1
        while True:
            resp = self.sending_request(url, headers = HEADERS, proxy = PROXY).content.decode()
            if not resp:
                print('Cant get page')
                break
            page_source = BS(resp, 'lxml')
            source = page_source.find('div',{'class':'table-view-wrap'}).findAll('div', {'class':'table-view_emulate__row'})
            source = [div.find('noindex').find('a',{'href':True}).get('href', False) for div in source if KEYWORD in div.text]
            for l in source:
                if not l:
                    continue
                link = self.correct_url(self.domain, l)
                redirect_page = self.sending_request(link, headers=HEADERS, proxy=PROXY)
                try:
                    links.append(BS(redirect_page.content.decode(), 'lxml').find('a',{'href':True})['href'])
                except:
                    pass
            #find next page
            try:
                nxt_page = page_source.find('div',{'class':'pagination pagination_center'}).find('i',{'class':'icon-right-open'}).parent.get('href', False)
                if not nxt_page:
                    break
                url = self.correct_url(self.domain, nxt_page)
                #delay 2 seconds between requests
                time.sleep(2)
                counter += 1
                print(counter, ' Next url:', url)
            except:
                #traceback.print_exc()
                break
            print('In links:',len(links))
        return links

class Rieltor:
    def analyze(self, resp):
        try:
            return BS(resp.content.decode(), 'lxml').find('div',{'class':'ov-author__info'}).find('div',{'class':'ov-author__phone'}).text.strip()
        except:
            return None

class DomRia:
    def get_params(self, resp):
        if not resp: return False
        source = BS(resp.content.decode(), 'lxml')
        try:
            csrf = source.find('script',{'data-csrf':True}).get('data-csrf', False)
        except: csrf = False
        try:
            user_id = BS(source.find('script',{'id':'finalPageUserInfoBlockPhonesTemplate'}).text, 'lxml').find('a', {'owner_id':True}).get('owner_id', False)
        except: user_id = False
        if not csrf or not user_id:
            print('Cant extract params for next request from: ', resp.url)
            return False
        url = 'https://dom.ria.com/node/api/getOwnerAndAgencyDataByIds?userId='+user_id+\
              '&agencyId=0&langId=2&'+\
              '_csrf='+csrf
        headers = {
                    'Accept': 'application / json, text / javascript, * / *; q = 0.01',
                    'Accept - Encoding': 'gzip, deflate, br',
                    'Accept - Language': 'en - US, en; q = 0.8',
                    'Connection': 'keep - alive',
                    'Host': 'dom.ria.com',
                    'Referer': resp.url,
                    'User-Agent': agent.random,
                    'X - Requested - With': 'XMLHttpRequest'
        }
        return {'url':url, 'headers':headers}
    def analyze(self, resp):
        if not resp:
            print('Cant extract data')
            return False
        try:
            return resp.json()['owner']['owner_phones'][0]['phone_formatted']
        except:
            return False

class AddressUA:
    def analyze(self, resp):
        try:
            return BS(resp.content.decode(), 'lxml').find('div',{'class':'author-contacts'}).find('div',{'id':'phone_a1'}).text.strip()
        except:
            return False

class Aviso:
    def analyze(self, resp):
        data = BS(resp.content.decode(), 'lxml').find('span',{'class':'phone-number'})
        oper = re.findall(r'(\d+)', data.text)
        phone = data.get('data-last', False)
        if not oper or not phone:
            print('Cant extract data from: ', resp.url)
            return False
        phone = oper[0] + phone
        if not phone.startswith('+380'):
            phone = '+380'+phone
        return phone

class Country:
    def analyze(self, resp):
        try:
            return BS(resp.content.decode(), 'lxml').find('div', {'class':'showingphone'}).text.strip()
        except:
            return False

class KievMesto:
    def analyze(self, url):
        pass
    #selenium+phantom required

class EstUA:
    def analyze(self, resp):
        source = BS(resp.content.decode(), 'lxml')
        links = source.findAll('a',{'href':True})
        try:
            return ';'.join({a.text for a in links if a['href'].startswith('tel:')})
        except:
            return False


class Megamakler:
    def analyze(self, resp):
        source = BS(resp.content.decode(), 'lxml').find('span',{'class':'phones'})
        if not source:
            return False
        return ''.join(re.findall(r'(\d+)', source.text.strip()))

class FnUA:
    def analyze(self, resp):
        source = BS(resp.content.decode(), 'lxml').find('div', {'id': 'showPhone'}).find('a',{'href':True})
        if not source:
            return False
        return re.search(r'(\d+)',source.get('href', '')).group()

if __name__ == '__main__':
    DATA = {}
    failed = {}
    lun = LUN()
    links = lun.analyze_start_page(URL)

    parsers = {
        'dom.ria.com':DomRia(),
        'rieltor.ua':Rieltor(),
        '.est.ua':EstUA(),
        'address.ua':AddressUA(),
        'www.aviso.ua':Aviso(),
        'www.country.ua':Country(),
        'megamakler.com.ua':Megamakler(),
        'fn.ua':FnUA()
    }

    for x, i in enumerate(links):
        url_components = urlparse(i)
        if not url_components.scheme:
            i = 'http://'+i
        resp = lun.sending_request(i)
        if not resp:
            failed[x] = (i, 'No responce')
            continue
        if url_components.netloc == 'dom.ria.com':
            data = parsers['dom.ria.com'].get_params(resp)
            resp = lun.sending_request(url=data['url'], headers=data['headers'], set_agent=False)
            phone = parsers['dom.ria.com'].analyze(resp)
        elif url_components.netloc.endswith('.est.ua'):
            phone = parsers['.est.ua'].analyze(resp)
        elif url_components.netloc == 'kiev.mesto.ua':
            phone = False
        else:
            parser = parsers.get(url_components.netloc, False)
            if parser:
                phone = parser.analyze(resp)
        if phone:
            DATA[x] = (resp.url, phone)
        else:
            failed[x] = (resp.url, phone)
        print(x, ' : ', phone, ' : ', resp.url)

