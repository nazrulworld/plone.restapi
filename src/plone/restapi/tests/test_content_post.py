# -*- coding: utf-8 -*-
from OFS.interfaces import IObjectWillBeAddedEvent
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import TEST_USER_PASSWORD
from plone.restapi import HAS_AT
from plone.restapi.testing import PLONE_RESTAPI_AT_FUNCTIONAL_TESTING
from plone.restapi.testing import PLONE_RESTAPI_DX_FUNCTIONAL_TESTING
from Products.CMFCore.utils import getToolByName
from zope.component import getGlobalSiteManager
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

import requests
import transaction
import unittest


class TestFolderCreate(unittest.TestCase):

    layer = PLONE_RESTAPI_DX_FUNCTIONAL_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.portal_url = self.portal.absolute_url()
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        login(self.portal, SITE_OWNER_NAME)
        self.portal.invokeFactory(
            'Folder',
            id='folder1',
            title='My Folder'
        )
        wftool = getToolByName(self.portal, 'portal_workflow')
        wftool.doActionFor(self.portal.folder1, 'publish')
        transaction.commit()

    def test_post_to_folder_creates_document(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
            },
        )
        self.assertEqual(201, response.status_code)
        transaction.begin()
        self.assertEqual("My Document", self.portal.folder1.mydocument.Title())
        self.assertEqual("Document", response.json().get('@type'))
        self.assertEqual("mydocument", response.json().get('id'))
        self.assertEqual("My Document", response.json().get('title'))

        expected_url = self.portal_url + u"/folder1/mydocument"
        self.assertEqual(expected_url, response.json().get('@id'))

    def test_post_to_folder_creates_folder(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Folder",
                "id": "myfolder",
                "title": "My Folder",
            },
        )
        self.assertEqual(201, response.status_code)
        transaction.begin()
        self.assertEqual("My Folder", self.portal.folder1.myfolder.Title())
        self.assertEqual("Folder", response.json().get('@type'))
        self.assertEqual("myfolder", response.json().get('id'))
        self.assertEqual("My Folder", response.json().get('title'))

        expected_url = self.portal_url + u"/folder1/myfolder"
        self.assertEqual(expected_url, response.json().get('@id'))

    def test_post_without_type_returns_400(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "id": "mydocument",
                "title": "My Document",
            },
        )
        self.assertEqual(400, response.status_code)
        self.assertIn("Property '@type' is required", response.content)

    def test_post_without_id_creates_id_from_title(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Document",
                "title": "My Document",
            },
        )
        self.assertEqual(201, response.status_code)
        transaction.begin()
        self.assertIn('my-document', self.portal.folder1)

    def test_post_without_id_creates_id_from_filename(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "File",
                "title": "My File",
                "file": {
                    "filename": "test.txt",
                    "data": "Spam and Eggs",
                    "content_type": "text/plain",
                },
            },
        )
        self.assertEqual(201, response.status_code)
        transaction.begin()
        self.assertIn('test.txt', self.portal.folder1)

    def test_post_with_id_already_in_use_returns_400(self):
        self.portal.folder1.invokeFactory('Document', 'mydocument')
        transaction.commit()
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
            },
        )
        self.assertEqual(400, response.status_code)

    def test_post_to_folder_returns_401_unauthorized(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(TEST_USER_NAME, TEST_USER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
            },
        )
        self.assertEqual(401, response.status_code)

    def test_post_to_folder_without_add_permission_returns_403_forbidden(self):
        self.portal.folder1.manage_permission(
            'plone.app.contenttypes: Add Document', [], acquire=False)
        transaction.commit()
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
            },
        )
        self.assertEqual(403, response.status_code)

    def test_post_to_folder_fires_proper_events(self):
        sm = getGlobalSiteManager()
        fired_events = []

        def record_event(event):
            fired_events.append(event.__class__.__name__)

        sm.registerHandler(record_event, (IObjectCreatedEvent,))
        sm.registerHandler(record_event, (IObjectWillBeAddedEvent,))
        sm.registerHandler(record_event, (IObjectAddedEvent,))
        sm.registerHandler(record_event, (IObjectModifiedEvent,))

        requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
                "description": "123",
            },
        )

        self.assertEqual(
            fired_events,
            [
                'ObjectCreatedEvent',
                'ObjectWillBeAddedEvent',
                'ObjectAddedEvent',
                'ContainerModifiedEvent',
            ])

        sm.unregisterHandler(record_event, (IObjectCreatedEvent,))
        sm.unregisterHandler(record_event, (IObjectWillBeAddedEvent,))
        sm.unregisterHandler(record_event, (IObjectAddedEvent,))
        sm.unregisterHandler(record_event, (IObjectModifiedEvent,))


class TestATFolderCreate(unittest.TestCase):

    layer = PLONE_RESTAPI_AT_FUNCTIONAL_TESTING

    def setUp(self):
        if not HAS_AT:
            raise unittest.SkipTest('Testing Archetypes support requires it')
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)
        self.portal.invokeFactory(
            'Folder',
            id='folder1',
            title='My Folder'
        )
        # wftool = getToolByName(self.portal, 'portal_workflow')
        # wftool.doActionFor(self.portal.folder1, 'publish')
        transaction.commit()

    def test_post_without_id_creates_id_from_title_for_archetypes(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(TEST_USER_NAME, TEST_USER_PASSWORD),
            json={
                "@type": "ATTestDocument",
                "title": "My Document",
                "testRequiredField": "My Value"
            },
        )
        self.assertEqual(201, response.status_code)
        transaction.begin()
        self.assertIn('my-document', self.portal.folder1)

    def test_id_from_filename(self):
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(TEST_USER_NAME, TEST_USER_PASSWORD),
            json={
                "@type": "File",
                "file": {"filename": "test.txt", "data": "Foo bar"},
            },
        )
        self.assertEqual(201, response.status_code)
        transaction.begin()
        self.assertIn('test.txt', self.portal.folder1)

    def test_post_with_id_already_in_use_returns_400(self):
        self.portal.folder1.invokeFactory('Document', 'mydocument')
        transaction.commit()
        response = requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(TEST_USER_NAME, TEST_USER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
            },
        )
        self.assertEqual(400, response.status_code)

    def test_post_to_folder_fires_proper_events(self):
        sm = getGlobalSiteManager()
        fired_events = []

        def record_event(event):
            fired_events.append(event.__class__.__name__)

        sm.registerHandler(record_event, (IObjectCreatedEvent,))
        sm.registerHandler(record_event, (IObjectWillBeAddedEvent,))
        sm.registerHandler(record_event, (IObjectAddedEvent,))
        sm.registerHandler(record_event, (IObjectModifiedEvent,))

        requests.post(
            self.portal.folder1.absolute_url(),
            headers={'Accept': 'application/json'},
            auth=(SITE_OWNER_NAME, SITE_OWNER_PASSWORD),
            json={
                "@type": "Document",
                "id": "mydocument",
                "title": "My Document",
                "description": "123",
            },
        )

        self.assertEqual(
            fired_events,
            [
                'ObjectInitializedEvent',
                'ObjectAddedEvent',
                'ContainerModifiedEvent',
            ])

        sm.unregisterHandler(record_event, (IObjectCreatedEvent,))
        sm.unregisterHandler(record_event, (IObjectWillBeAddedEvent,))
        sm.unregisterHandler(record_event, (IObjectAddedEvent,))
        sm.unregisterHandler(record_event, (IObjectModifiedEvent,))
