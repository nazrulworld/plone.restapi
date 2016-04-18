# -*- coding: utf-8 -*-
from plone.app.contentlisting.interfaces import IContentListingObject
from plone.restapi.interfaces import ISerializeToJsonSummary
from Products.CMFPlone.interfaces import IPloneSiteRoot
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface


@implementer(ISerializeToJsonSummary)
@adapter(Interface, Interface)
class DefaultJSONSummarySerializer(object):
    """Default ISerializeToJsonSummary adapter.

    Requires context to be adaptable to IContentListingObject, which is
    the case for all content objects providing IContentish.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        obj = IContentListingObject(self.context)
        summary = {
            '@id': obj.getURL(),
            'title': obj.Title(),
            'description': obj.Description()
        }
        return summary


@implementer(ISerializeToJsonSummary)
@adapter(IPloneSiteRoot, Interface)
class SiteRootJSONSummarySerializer(object):
    """ISerializeToJsonSummary adapter for the Plone Site root.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        summary = {
            '@id': self.context.absolute_url(),
            'title': self.context.title,
            'description': self.context.description
        }
        return summary