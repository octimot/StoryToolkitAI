import os
import codecs
import hashlib


class Document:
    
    _instances = {}

    def __new__(cls, *args, **kwargs):
        """
        This checks if the current document file path isn't already loaded in an instance
        and returns that instance if it is.
        """

        # we use the document file path as the id for the instance
        document_path_id = cls.get_document_path_id(
            document_file_path=kwargs.get('document_file_path', None) or args[0]
        )

        # if the document file path is already loaded in an instance, we return that instance
        if document_path_id in cls._instances:

            return cls._instances[document_path_id]

        # otherwise we create a new instance
        instance = super().__new__(cls)

        # and we store it in the instances dict
        cls._instances[document_path_id] = instance

        # then we return the instance
        return instance

    def __init__(self, document_file_path):

        # prevent initializing the instance more than once if it was found in the instances dict
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._document_path_id = None
        self.__document_file_path = None

        # this is used to check if the file has changed
        # it will be updated only when the file is loaded and saved
        self._last_hash = None

        self._name = os.path.basename(document_file_path)

        self._text = ''

        # this is set to false if the file wasn't found
        self._exists = False

        # use the passed document file path
        self.load_from_file(file_path=document_file_path)

        # add this to know that we already initialized this instance
        self._initialized = True

    @property
    def document_path_id(self):
        return self._document_path_id

    @property
    def document_file_path(self):
        return self.__document_file_path

    @property
    def name(self):
        return self._name

    @property
    def text(self):
        return self._text

    @property
    def exists(self):
        return self._exists

    @staticmethod
    def get_document_path_id(document_file_path: str = None):
        return hashlib.md5(document_file_path.encode('utf-8')).hexdigest()

    def load_from_file(self, file_path):
        """
        This changes the document_file_path
        and loads the document file from disk and sets the attributes
        """
        self.__document_file_path = file_path

        # when we set the document file_path, we also check if the file exists
        # but only if the file_path is a string
        self._exists = os.path.isfile(self.__document_file_path) if isinstance(file_path, str) else False

        # open the file and read the contents
        if self._exists:
            with codecs.open(self.__document_file_path, 'r', 'utf-8-sig') as document_file:
                self._text = document_file.read()
        