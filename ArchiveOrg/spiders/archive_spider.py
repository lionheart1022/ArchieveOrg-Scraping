#!/usr/bin/env python
# -*- coding: utf-8 -*-

import scrapy
import re
import requests

from HTMLParser import HTMLParser

from ArchiveOrg.items import ArchiveorgItem, DiscographyItem

is_empty = lambda x, y=None: x[0] if x else y


class ArchiveSpider(scrapy.Spider):
    name = "archive_product"
    allowed_domains = ["https://archive.org", "www.45worlds.com"]

    start_urls = ['https://archive.org/details/georgeblood?sort=-publicdate']

    PAGE_LINK = 'https://archive.org/details/georgeblood?&sort=-publicdate&page={page_number}'
    item_per_page = 75  # display the number of items per page

    TITLE = ''
    PERFORMER = ''
    PUBLISHER = ''
    CATALOG_NUM = ''
    MORE_URL = ''
    URL = ''
    LOCATION = ''
    GENRE = ''

    def start_requests(self):
        yield scrapy.Request(url=self.start_urls[0], callback=self.parse_pages)

    def parse_pages(self, response):
        page_links = []

        # total count is number of results
        total_count = response.xpath('//div[@class="columns-facets"]'
                                     '/h3/text()').extract()
        total_count = self._clean_text(total_count[0])
        total_count = re.search('\d+', total_count).group(0)
        range_count = int(total_count) / self.item_per_page

        for page_num in range(1, range_count):
            link = self.PAGE_LINK.format(page_number=page_num)
            page_links.append(link)

        for page_link in page_links:
            yield scrapy.Request(url=page_link, callback=self.parse_links, dont_filter=True)

    def parse_links(self, response):
        href_links = response.xpath('//div[contains(@class, "item-ttl")]'
                                    '/a/@href').extract()

        for href in href_links:
            link = 'https://archive.org%s' % href
            yield scrapy.Request(url=link, callback=self.parse_product,
                                 dont_filter=True)

    def parse_product(self, response):
        item = ArchiveorgItem()

        title = self._parse_title(response)
        performer = self._parse_performer(response)
        publisher = self._parse_publisher(response)
        catalog_num = self._parse_catalog_num(response)

        # Parse Release date
        release_date = self._parse_release_date(response)

        if release_date == '':
            return
        else:
            item['title'] = title
            item['performer'] = performer
            item['publisher'] = publisher
            item['catalog_num'] = catalog_num

            # Parse Genre
            item['genre'] = self.GENRE

            item['archive_url'] = response.url
            item['release_date'] = release_date

            # Parse Google Search URL
            more_link = self._parse_search_link(response)
            item['google_url'] = more_link

            item['URL'] = self.URL

            # Parse Location
            item['location'] = self.LOCATION

            yield item

    def _parse_title(self, response):
        title = response.xpath('//div[contains(@class, "relative-row")]'
                               '//div[contains(@class, "thats-left")]'
                               '/h1/text()')[1].extract()
        title = self._clean_text(title)
        self.TITLE = title
        return title

    def _parse_release_date(self, response):
        release_date = is_empty(response.xpath('//div[contains(@class, "relative-row")]'
                                               '//div[contains(@class, "thats-left")]'
                                               '//div[@class="key-val-big"]'
                                               '/a/@href').extract())
        if '19' in release_date:
            release_date = re.search('date:(.*)', release_date)
            if release_date:
                release_date = release_date.group(1)
                self.URL = ""
        else:
            if self.CATALOG_NUM:
                if '-' in self.CATALOG_NUM:
                    date = ""
                    self.URL = ""
                else:
                    if re.search('\d+', self.CATALOG_NUM):
                        world_catalog = re.search('\d+', self.CATALOG_NUM).group()
                        url = 'http://www.45worlds.com/78rpm/record/' + str(world_catalog)
                        response_data = requests.get(url, timeout=5)

                        if str(response_data) == '<Response [200]>':
                            location = re.search('Country:</td><td>(.*?)</td></tr>',
                                                 response_data.content).group(1)
                            location = re.search('>(.*)</a>', location).group(1)
                            self.LOCATION = location

                            genre = re.search('Format:</td><td>(.*?)</td></tr>', response_data.content).group(1)
                            self.GENRE = HTMLParser().unescape(genre)

                            original_date = re.search('Date:</td><td>(.*?)</td></tr>', response_data.content).group(1)

                            if original_date:
                                date = original_date
                                self.URL = url
                            else:
                                date = ""
                        else:
                            date = ""
                    else:
                        date = ""

                release_date = date

            else:
                release_date = ""

        return release_date

    def _parse_performer(self, response):
        if 'Performer' in response.body:
            if 'Writer' in response.body:
                performer = re.search('<b>Performer:</b>(.*?)</p>', response.body).group(1)
                if 'Writer' in performer:
                    performer = re.search('<b>Performer:</b>(.*?)<br', response.body).group(1)
                else:
                    performer = performer
            else:
                if re.search('<b>Performer:</b>(.*?);', response.body):
                    performer = re.search('<b>Performer:</b>(.*?);', response.body).group(1)
                else:
                    performer = re.search('<b>Performer:</b>(.*?)</p>', response.body).group(1)
        else:
            performer = ""
        self.PERFORMER = performer
        return self.PERFORMER

    def _parse_publisher(self, response):
        publisher = response.xpath('//div[contains(@class, "relative-row")]'
                                   '//div[contains(@class, "thats-left")]'
                                   '/span[@class="value"]'
                                   '/a/text()').extract()
        if publisher:
            self.PUBLISHER = publisher[0]
            return self.PUBLISHER

    def _parse_catalog_num(self, response):
        catalog_num = re.search('<b>Catalog number:</b>(.*?)</p>', response.body)
        if catalog_num:
            self.CATALOG_NUM = catalog_num.group(1)
            return self.CATALOG_NUM

    def _parse_search_link(self, response):
        google_url = 'https://www.google.com/search?' \
                     'q=site:{reference_url}' + " " + \
                     '{publisher}' + " " + \
                     '{catalog_num}' + " " + '{title}' + " " + '{performer}'

        url = google_url.format(reference_url="www.78discography.com",
                                publisher=self.PUBLISHER,
                                catalog_num=self.CATALOG_NUM,
                                title=self.TITLE,
                                performer=self.PERFORMER)
        return url

    @staticmethod
    def _clean_text(self, text):
        text = re.sub("[\n\t]", "", text)
        text = re.sub(",", "", text).strip()
        return text


class DiscographySpider(scrapy.Spider):
    name = 'disco_products'
    allowed_domains = ["78discography.com"]

    start_urls = ['http://78discography.com/']

    def start_requests(self):
        yield scrapy.Request(url=self.start_urls[0], callback=self.parse_pages)

    def parse_pages(self, response):

        links = response.xpath('//center//a/@href').extract()

        for link in links:
            if 'http' in link:
                href = link
            else:
                href = response.url + link

            yield scrapy.Request(url=href, callback=self.parse_product,
                                 dont_filter=True)

    def parse_product(self, response):
        product = DiscographyItem()
        total_count = response.xpath('//table/tr/td[1]/text()').extract()

        for i in range(len(total_count)):

            label = response.url.replace(".htm", "")
            label = re.search('http://78discography.com/(.*)', label).group(1)
            title = self._parse_title(response, i)
            artist = self._parse_artist(response, i)
            composer = self._parse_composer(response, i)
            date = self._parse_date(response, i)
            catalog_num = self._parse_catalog_num(response, i)

            if date == '':
                break

            else:
                product['title'] = title
                product['artist'] = artist
                product['composer'] = composer
                product['release_date'] = date
                product['catalog_num'] = catalog_num
                product['label'] = label

                yield product

    @staticmethod
    def _parse_catalog_num(response, index):
        cnum = response.xpath('//table/tr/td[1]/text()')[index].extract()
        return cnum

    @staticmethod
    def _parse_artist(response, index):
        artist = response.xpath('//table/tr/td[2]/text()')[index].extract()
        return artist

    @staticmethod
    def _parse_title(response, index):
        title = response.xpath('//table/tr/td[3]/text()')[index].extract()
        return title

    @staticmethod
    def _parse_date(response, index):
        date = response.xpath('//table/tr/td[7]/text()')[index].extract()

        if date == '-':
            date = ''
        else:
            if re.search('19(\d+)', date):
                date = re.search('19(\d+)', date).group()
            else:
                if '-' in date:
                    if len(re.search('-(\d+)', date).group(1)) == 1:
                        date = '190' + re.search('-(\d+)', date).group(1)
                    else:
                        date = '19' + re.search('-(\d+)', date).group(1)
                else:
                    if re.search('/(\d+)', date):
                        if len(re.search('/(\d+)', date).group(1)) == 1:
                            date = '190' + re.search('/(\d+)', date).group(1)
                        else:
                            date = '19' + re.search('/(\d+)', date).group(1)
                    else:
                        date = ''
        return date

    @staticmethod
    def _parse_composer(response, index):
        composer = response.xpath('//table/tr/td[8]/text()')[index].extract()

        if composer == '-':
            composer = ''

        return composer