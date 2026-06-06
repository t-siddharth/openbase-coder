"""
Base viewset classes for openbase_coder_cli.

This module provides reusable base viewset classes that can be extended
in your application's views.
"""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.response import Response


class SingleObjectViewSet(viewsets.ViewSet):
    """
    A viewset for endpoints that operate on a single object (no list).

    Useful for settings, profile, or other singleton-type resources.
    Override get_object() to return your singleton instance.
    """

    serializer_class = None

    def get_object(self):
        """Override this method to return the singleton object."""
        msg = "Subclasses must implement get_object()"
        raise NotImplementedError(msg)

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance."""
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        """Return the serializer class to use."""
        return self.serializer_class

    def retrieve(self, request, *args, **kwargs):
        """Retrieve the singleton object."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update the singleton object."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Partially update the singleton object."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
