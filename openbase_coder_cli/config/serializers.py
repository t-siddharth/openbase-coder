"""
Base serializer classes for openbase_coder_cli.

This module provides reusable base serializer classes that can be extended
in your application's serializers.
"""

from __future__ import annotations

from rest_framework import serializers


class TimestampedModelSerializer(serializers.ModelSerializer):
    """
    Base serializer for models with created_at and updated_at fields.

    Makes timestamp fields read-only by default.
    """

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ReadOnlyModelSerializer(serializers.ModelSerializer):
    """
    A read-only model serializer.

    Useful for list/retrieve endpoints where you don't want to allow updates.
    """

    def create(self, validated_data):
        msg = "This serializer is read-only."
        raise NotImplementedError(msg)

    def update(self, instance, validated_data):
        msg = "This serializer is read-only."
        raise NotImplementedError(msg)
