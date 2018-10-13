# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy

class ArchiveorgItem(scrapy.Item):
    # define the fields for your item here like:
    release_date = scrapy.Field()
    archive_url = scrapy.Field()
    google_url = scrapy.Field()
    URL = scrapy.Field()
    location = scrapy.Field()
    genre = scrapy.Field()

class DiscographyItem(scrapy.Item):
    # define the fields for your item here like:
    label = scrapy.Field()
    release_date = scrapy.Field()
    catalog_num = scrapy.Field()
    title = scrapy.Field()
    artist = scrapy.Field()
    composer = scrapy.Field()