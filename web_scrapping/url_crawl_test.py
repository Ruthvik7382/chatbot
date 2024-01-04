from .url_crawling import url_crawl
import pytest
import os   


#checking if the url_crawl class is fetching list of urls
@pytest.fixture
def url_crawl_test():
    return url_crawl(base_url='https://www.iit.edu/', depth=3)

def test_get_child_urls(url_crawl_test):
    child_urls = url_crawl_test.get_child_urls()
    assert isinstance(child_urls, list)
    assert all(isinstance(url, str) for url in child_urls)
