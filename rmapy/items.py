import datetime
import logging
import re

from . import api
from .exceptions import DocumentNotFound

def now():
    return datetime.datetime.now(datetime.timezone.utc)

class Item:

    DOCUMENT = 'DocumentType'
    FOLDER = 'CollectionType'

    @staticmethod
    def parse_datetime(dt):
        # fromisoformat needs 0, 3, or 6 decimal places for the second, but
        # we can get other numbers from the API.  Since we're not doing anything
        # that time-sensitive, we'll just chop off the fractional seconds.
        dt = re.sub(r'\.\d*', '', dt).replace('Z', '+00:00')
        return datetime.datetime.fromisoformat(dt)

    @classmethod
    def from_metadata(cls, metadata):
        type_ = metadata.get('Type')
        if type_ == cls.DOCUMENT:
            return Document(metadata)
        if type_ == cls.FOLDER:
            return Folder(metadata)
        logging.error(f"Unknown document type: {type_}")
        return None

    def __init__(self, metadata):
        self._metadata = metadata
        self._raw = b''

    @property
    def name(self):
        return self._metadata.get('VissibleName')

    @property
    def id(self):
        return self._metadata.get('ID')

    @property
    def parent(self):
        return self._metadata.get('Parent')

    @property
    def mtime(self):
        return self.parse_datetime(self._metadata.get('ModifiedClient'))

    @property
    def virtual(self):
        return False

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'

    def refresh_metadata(self, downloadable=True):
        try:
            self._metadata = api.client.get_metadata(self.id, downloadable)
        except DocumentNotFound:
            logging.error(f"Could not update metadata for {self}")

    @property
    def download_url(self):
        url = self._metadata['BlobURLGet']
        if url and self.parse_datetime(self._metadata['BlobURLGetExpires']) > now():
            return url
        return None

    @property
    def raw(self):
        if not self._raw:
            if not self.download_url:
                self.refresh_metadata(downloadable=True)
            # This could have failed...
            if self.download_url:
                self._raw = api.client.get_blob(self.download_url)
        return self._raw

    @property
    def raw_size(self):
        if self._raw:
            return len(self._raw)
        return 0


class Document(Item):

    def get_contents(self):
        ...


class Folder(Item):

    def __init__(self, metadata):
        super().__init__(metadata)
        self.children = []


class VirtualFolder(Folder):

    def __init__(self, name):
        self._name = name
        self.children = []

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._name.lower()

    @property
    def parent(self):
        return None

    @property
    def mtime(self):
        return now()

    @property
    def virtual(self):
        return True
