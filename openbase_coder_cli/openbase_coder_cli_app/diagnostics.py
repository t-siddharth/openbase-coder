"""Health, diagnostics, and device discovery API views."""

from __future__ import annotations

import json
import logging
import time

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from openbase_coder_cli.openbase_coder_cli_app.common import _auth_debug_value
from openbase_coder_cli.paths import DEFAULT_LOG_DIR
from openbase_coder_cli.services.tailnet_devices import tailnet_devices_payload

logger = logging.getLogger(__name__)

IOS_LOG_UPLOAD_FILENAME = "ios-app.log"
IOS_LOG_UPLOAD_MAX_ENTRIES = 1000

class IOSLogEntrySerializer(serializers.Serializer):
    timestamp = serializers.CharField(required=False, allow_blank=True, max_length=64)
    component = serializers.CharField(required=False, allow_blank=True, max_length=128)
    message = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    metadata = serializers.DictField(
        child=serializers.CharField(allow_blank=True, max_length=1000),
        required=False,
    )
    line = serializers.CharField(required=False, allow_blank=True, max_length=4000)


class IOSLogUploadSerializer(serializers.Serializer):
    entries = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        max_length=IOS_LOG_UPLOAD_MAX_ENTRIES,
    )
    device = serializers.DictField(required=False)

    def validate_entries(self, entries):
        validated_entries = []
        for entry in entries:
            serializer = IOSLogEntrySerializer(data=entry)
            serializer.is_valid(raise_exception=True)
            validated_entries.append(serializer.validated_data)
        return validated_entries


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    logger.info(
        "health_check request path=%s auth=%s",
        request.path,
        _auth_debug_value(request),
    )
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


@api_view(["POST"])
def ios_logs_upload(request):
    """Append uploaded iOS diagnostics to the Openbase Coder log directory."""
    serializer = IOSLogUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    entries = serializer.validated_data["entries"]
    device = serializer.validated_data.get("device") or {}
    uploaded_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = DEFAULT_LOG_DIR / IOS_LOG_UPLOAD_FILENAME
    with log_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(
                json.dumps(
                    {
                        "uploaded_at": uploaded_at,
                        "source": "ios",
                        "device": device,
                        "entry": entry,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )

    logger.info("ios_logs_upload wrote count=%s path=%s", len(entries), log_path)
    return Response(
        {
            "uploaded_count": len(entries),
            "log_path": str(log_path),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def devices_list(request):
    """Discover tailnet devices and identify Openbase Coder hosts."""
    return Response(tailnet_devices_payload(), status=status.HTTP_200_OK)
