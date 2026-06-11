"""Shared tag option API views."""

from __future__ import annotations

from rest_framework.decorators import api_view
from rest_framework.response import Response

from openbase_coder_cli.openbase_coder_cli_app.item_tags import tag_options_payload


@api_view(["GET"])
def tag_options(request):
    """List local tag options shared by threads and reports."""
    return Response(tag_options_payload())
