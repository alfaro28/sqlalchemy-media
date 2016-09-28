
import unittest
from io import BytesIO
from os.path import join, exists

from sqlalchemy import Column, Integer, Unicode

from sqlalchemy_media import File, StoreManager
from sqlalchemy_media.tests.helpers import Json, TempStoreTestCase
from sqlalchemy_media.exceptions import MaximumLengthIsReachedError, MinimumLengthIsNotReachedError


class FileTestCase(TempStoreTestCase):

    def setUp(self):
        super().setUp()
        self.sample_text_file1 = join(self.stuff_path, 'sample_text_file1.txt')

    def test_attachment(self):

        class Person(self.Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)
            name = Column(Unicode(50), nullable=False, default='person1')
            image = Column(File.as_mutable(Json), nullable=True)

        session = self.create_all_and_get_session()

        # person1 = Person(name='person1')
        person1 = Person()
        self.assertIsNone(person1.image)
        sample_content = b'Simple text.'
        person1.image = File()

        with StoreManager(session):

            # First file before commit
            person1.image.attach(BytesIO(sample_content), content_type='text/plain', extension='.txt')
            self.assertIsInstance(person1.image, File)
            self.assertDictEqual(person1.image, {
                'contentType': 'text/plain',
                'key': person1.image.key,
                'extension': '.txt',
                'length': len(sample_content)
            })
            first_filename = join(self.temp_path, person1.image.path)
            self.assertTrue(exists(first_filename))

            # Second file before commit
            person1.image.attach(BytesIO(sample_content), content_type='text/plain', extension='.txt')
            second_filename = join(self.temp_path, person1.image.path)
            self.assertTrue(exists(second_filename))

            # Adding object to session, the new life-cycle of the person1 just began.
            session.add(person1)
            session.commit()
            self.assertFalse(exists(first_filename))
            self.assertTrue(exists(second_filename))

            # Loading again
            sample_content = b'Lorem ipsum dolor sit amet'
            person1 = session.query(Person).filter(Person.id == person1.id).one()
            person1.image.attach(BytesIO(sample_content), content_type='text/plain', extension='.txt')
            self.assertIsInstance(person1.image, File)
            self.assertDictEqual(person1.image, {
                'contentType': 'text/plain',
                'key': person1.image.key,
                'extension': '.txt',
                'length': len(sample_content)
            })
            third_filename = join(self.temp_path, person1.image.path)
            self.assertTrue(exists(second_filename))
            self.assertTrue(exists(third_filename))

            # Committing the session, so the store must done the scheduled jobs
            session.commit()
            self.assertFalse(exists(second_filename))
            self.assertTrue(exists(third_filename))

            # Rollback
            person1.image.attach(BytesIO(sample_content), content_type='text/plain', extension='.txt')
            forth_filename = join(self.temp_path, person1.image.path)
            self.assertTrue(exists(forth_filename))
            session.rollback()
            self.assertTrue(exists(third_filename))
            self.assertFalse(exists(forth_filename))

            # Delete file after object deletion
            person1 = session.query(Person).filter(Person.id == person1.id).one()
            session.delete(person1)
            session.commit()
            self.assertFalse(exists(third_filename))

            # Delete file on set to null
            person1 = Person()
            self.assertIsNone(person1.image)
            person1.image = File()
            person1.image.attach(BytesIO(sample_content), content_type='text/plain', extension='.txt')
            fifth_filename = join(self.temp_path, person1.image.path)
            person1.image = None
            session.add(person1)
            self.assertTrue(exists(fifth_filename))
            session.commit()
            self.assertFalse(exists(fifth_filename))

    def test_file_size_limit(self):

        class LimitedFile(File):
            min_length = 20
            max_length = 30

        class Person(self.Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)
            cv = Column(LimitedFile.as_mutable(Json), nullable=True)

        session = self.create_all_and_get_session()

        person1 = Person()
        person1.cv = LimitedFile()

        with StoreManager(session):

            # MaximumLengthIsReachedError, MinimumLengthIsNotReachedError
            self.assertRaises(MinimumLengthIsNotReachedError, person1.cv.attach, BytesIO(b'less than 20 chars!'))
            self.assertRaises(MaximumLengthIsReachedError, person1.cv.attach,
                              BytesIO(b'more than 30 chars!............'))

    def test_attribute_type_assertion(self):
        class MyAttachmentType(File):
            pass

        class Person(self.Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)
            cv = Column(MyAttachmentType.as_mutable(Json), nullable=True)

        person1 = Person()

        def set_invalid_type():
            person1.cv = File()

        self.assertRaises(TypeError, set_invalid_type)

    def test_model_constructor(self):

        class Person(self.Base):
            __tablename__ = 'person'
            id = Column(Integer, primary_key=True)
            cv = Column(File.as_mutable(Json), nullable=True)

        session = self.create_all_and_get_session()
        person1 = Person(cv=File())
        self.assertIsInstance(person1.cv, File)
        with StoreManager(session):
            person1.cv.attach(BytesIO(b'Simple text'))
            session.add(person1)
            session.commit()


if __name__ == '__main__':
    unittest.main()
