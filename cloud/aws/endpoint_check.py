"""Eventual SigV4 smoke test. Only an exact inventoried API host is accepted."""

import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cloud.aws.contracts import MAX_ARTIFACT_BYTES, LabError
from cloud.aws.ownership import validate_outputs


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise LabError("endpoint_redirect_rejected")


def smoke_test(session, settings, outputs, expected, *, opener=None, signer=None):
    validate_outputs(outputs, settings)
    if not outputs["endpoint"]:
        raise LabError("endpoint_disabled")
    store = sorted(expected["stores"])[0]
    url = outputs["endpoint"] + "/metrics/units?store=" + quote(store, safe="")
    opener = opener or build_opener(NoRedirect())
    try:
        with opener.open(Request(url, method="GET"), timeout=10) as response:
            response.read(1024)
        raise LabError("unsigned_request_was_not_rejected")
    except HTTPError as exc:
        if exc.code != 403:
            raise LabError("unsigned_denial_not_confirmed") from exc
        exc.close()
    headers = (signer or signed_headers)(session, settings, url)
    with opener.open(
        Request(url, headers=headers, method="GET"), timeout=10
    ) as response:
        raw = response.read(MAX_ARTIFACT_BYTES + 1)
        if response.status != 200 or len(raw) > MAX_ARTIFACT_BYTES:
            raise LabError("signed_endpoint_failure")
    payload = json.loads(raw)
    if (
        payload.get("value") != expected["stores"][store]
        or payload.get("store") != store
        or payload.get("mode") != "synthetic"
        or payload.get("period") != expected["period"]
        or payload.get("run_id") != settings.run_id
        or payload.get("provenance") != expected["provenance"]
        or payload.get("metric") != "units"
        or payload.get("unit") != "units"
        or payload.get("dataset_version") != expected["dataset_version"]
    ):
        raise LabError("endpoint_reference_mismatch")
    return {
        "unsigned_status": 403,
        "signed_status": 200,
        "store": store,
        "value": payload["value"],
        "live": True,
    }


def signed_headers(session, settings, url):
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    request = AWSRequest(method="GET", url=url)
    SigV4Auth(
        session.get_credentials().get_frozen_credentials(),
        "execute-api",
        settings.region,
    ).add_auth(request)
    return dict(request.headers)
