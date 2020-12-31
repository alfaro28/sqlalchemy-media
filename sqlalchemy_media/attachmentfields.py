from sqlalchemy import String, TypeDecorator

from sqlalchemy_media import StringFile


class FileField(TypeDecorator):
    impl = String

    def __init__(self, directory=None, image_store=None, processors=None, attachment_type=StringFile,
                 length=255, *args, **kwargs):
        self._image_store = image_store
        self._attachment_type = attachment_type
        self._directory = directory
        self._processors = processors
        super(FileField, self).__init__(length=length, *args, **kwargs)

    def process_bind_param(self, value, dialect):
        if not value:
            return None

        if not isinstance(value, self._attachment_type):
            raise ValueError('StringFileField requires %s, '
                             'got %s instead' % (self._attachment_type, type(value)))

        return value.encode()

    def process_result_value(self, value, dialect):
        return self._attachment_type.decode(value, self._image_store, self._directory, self._processors)
