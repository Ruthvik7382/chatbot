from langchain.document_loaders import RecursiveUrlLoader
from tqdm import tqdm

class url_crawl(RecursiveUrlLoader):
    def __init__(self, base_url, depth):
        super().__init__(url=base_url, max_depth=depth)
        self.base_url = base_url
        self.max_depth = depth

    def get_child_urls(self):
        # Initialize a set to store visited URLs
        visited = set()
        
        # Initialize a list to store the collected URLs
        self.collected_urls = []

        # Call the _get_child_links_recursive method to start crawling
        for document in tqdm(self._get_child_links_recursive(self.base_url, visited)):
            self.collected_urls.append(document.metadata['source'])  

        return self.collected_urls


