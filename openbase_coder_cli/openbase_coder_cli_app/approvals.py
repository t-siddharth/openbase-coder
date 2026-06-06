"""Super Agents approval request API views."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from openbase_coder_cli.mcp.session_manager import get_session_manager


class ApprovalRequestActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accept", "decline", "cancel"])


@api_view(["GET"])
def approval_requests(request):
    """List currently pending Super Agents approval requests across threads."""
    manager = get_session_manager()
    requests = async_to_sync(manager.list_approval_requests)()
    return Response({"requests": requests}, status=status.HTTP_200_OK)


@api_view(["POST"])
def approval_request_detail(request, request_id):
    """Approve or deny one pending Super Agents approval request."""
    serializer = ApprovalRequestActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    manager = get_session_manager()
    try:
        result = async_to_sync(manager.answer_approval_request)(
            request_id,
            serializer.validated_data["decision"],
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response({"success": True, "result": result}, status=status.HTTP_200_OK)
