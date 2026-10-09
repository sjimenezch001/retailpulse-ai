"""Exact resource inventory backed by Terraform outputs plus service ownership tags."""

from cloud.aws.contracts import LabError


def require_tags(actual, settings):
    if any(actual.get(k) != v for k, v in settings.tags.items()):
        raise LabError("ownership_tags_mismatch")


def validate_outputs(outputs, settings, *, allow_deferred=False):
    expected = {
        "account": settings.account,
        "region": settings.region,
        "environment": settings.environment,
        "run_id": settings.run_id,
        "lab_id": settings.lab_id,
        "bucket": settings.bucket,
        "database": settings.database,
        "job": settings.name,
        "workgroup": settings.name,
        "glue_role": settings.name + "-glue",
    }
    if any(outputs.get(k) != v for k, v in expected.items()):
        raise LabError("terraform_inventory_mismatch")
    require_tags(outputs.get("tags", {}), settings)
    if (
        outputs.get("owner_managed") != ["bucket", "glue_role", "glue_boundary"]
        or outputs.get("glue_role_arn") != settings.glue_role_arn
        or outputs.get("boundary_arn") != settings.glue_boundary_arn
    ):
        raise LabError("owner_foundation_inventory_mismatch")
    if not allow_deferred and any(
        outputs.get(name) is not None
        for name in ("api_id", "lambda_role", "function", "endpoint")
    ):
        raise LabError("endpoint_deferred")
    endpoint = outputs.get("api_id") is not None if allow_deferred else False
    if outputs.get("lambda_role") != (settings.name + "-metrics" if endpoint else None):
        raise LabError("terraform_lambda_role_mismatch")
    if outputs.get("function") != (settings.name + "-metrics" if endpoint else None):
        raise LabError("terraform_function_mismatch")
    logs = [
        f"/retailpulse/{settings.environment}/glue/error",
        f"/retailpulse/{settings.environment}/glue/output",
    ]
    if endpoint:
        logs += [
            f"/aws/lambda/{settings.name}-metrics",
            f"/retailpulse/{settings.environment}/api",
        ]
    if set(outputs.get("log_groups", [])) != set(logs):
        raise LabError("terraform_log_inventory_mismatch")
    if endpoint:
        import re

        api_id = outputs["api_id"]
        if not re.fullmatch(r"[a-z0-9]{1,20}", api_id):
            raise LabError("api_identity")
        if (
            outputs.get("endpoint")
            != f"https://{api_id}.execute-api.{settings.region}.amazonaws.com"
        ):
            raise LabError("endpoint_identity")
    elif outputs.get("endpoint") is not None:
        raise LabError("unexpected_endpoint")
    return outputs


def verify_bucket(s3, settings):
    s3.head_bucket(Bucket=settings.bucket, ExpectedBucketOwner=settings.account)
    location = (
        s3.get_bucket_location(
            Bucket=settings.bucket,
            ExpectedBucketOwner=settings.account,
        ).get("LocationConstraint")
        or "us-east-1"
    )
    if location != settings.region:
        raise LabError("bucket_region_mismatch")
    bucket_tags = s3.get_bucket_tagging(
        Bucket=settings.bucket,
        ExpectedBucketOwner=settings.account,
    )["TagSet"]
    require_tags({t["Key"]: t["Value"] for t in bucket_tags}, settings)


def verify_resources(clients, settings, outputs):
    validate_outputs(outputs, settings)
    from cloud.aws.foundations import verify_foundations

    verify_foundations(clients, settings)
    for service, arn in (
        ("glue", settings.arn("glue", f"job/{settings.name}")),
        ("athena", settings.arn("athena", f"workgroup/{settings.name}")),
    ):
        if service == "glue":
            tags = clients[service].get_tags(ResourceArn=arn)["Tags"]
        else:
            result = clients[service].list_tags_for_resource(
                ResourceARN=arn, MaxResults=50
            )
            if result.get("NextToken"):
                raise LabError("ownership_tag_limit")
            tags = {t["Key"]: t["Value"] for t in result["Tags"]}
        require_tags(tags, settings)
    job = clients["glue"].get_job(JobName=settings.name)["Job"]
    if (
        job.get("SecurityConfiguration")
        or job.get("Role") != settings.glue_role_arn
        or job.get("NumberOfWorkers") != 2
        or job.get("WorkerType") != "G.1X"
        or job.get("Timeout") != 5
        or job.get("MaxRetries") != 0
        or job.get("ExecutionProperty", {}).get("MaxConcurrentRuns") != 1
    ):
        raise LabError("job_security_or_execution_bounds")
    database = clients["glue"].get_database(
        CatalogId=settings.account, Name=settings.database
    )["Database"]
    params = database.get("Parameters", {})
    if (
        params.get("lab_id") != settings.lab_id
        or params.get("run_id") != settings.run_id
    ):
        raise LabError("catalog_database_ownership")
    from cloud.aws.contracts import TABLES

    for name in (*TABLES, "store_units"):
        table = clients["glue"].get_table(
            CatalogId=settings.account, DatabaseName=settings.database, Name=name
        )["Table"]
        params = table.get("Parameters", {})
        if (
            params.get("lab_id") != settings.lab_id
            or params.get("run_id") != settings.run_id
        ):
            raise LabError("catalog_table_ownership")
        if (
            table.get("StorageDescriptor", {}).get("Location")
            != f"s3://{settings.bucket}/{settings.prefix('curated')}{name}/"
        ):
            raise LabError("catalog_location_ownership")
    for name in outputs["log_groups"]:
        arn = settings.arn("logs", f"log-group:{name}")
        require_tags(
            clients["logs"].list_tags_for_resource(resourceArn=arn)["tags"], settings
        )
    return {"verified": True, "lab_id": settings.lab_id, "resource_scope": outputs}


def stop_workloads(clients, settings, *, sleep):
    """Bounded enumeration restricted to one exact job and one workgroup."""
    glue, athena = clients["glue"], clients["athena"]
    runs = glue.get_job_runs(JobName=settings.name, MaxResults=100)
    if runs.get("NextToken"):
        raise LabError("job_inventory_limit")
    running = [
        r["Id"]
        for r in runs["JobRuns"]
        if r["JobRunState"] in {"STARTING", "RUNNING", "STOPPING", "WAITING"}
    ]
    if running:
        result = glue.batch_stop_job_run(JobName=settings.name, JobRunIds=running)
        if result.get("Errors"):
            raise LabError("job_stop_unverified")
    query_list = athena.list_query_executions(WorkGroup=settings.name, MaxResults=50)
    if query_list.get("NextToken"):
        raise LabError("query_inventory_limit")
    active = []
    for query_id in query_list["QueryExecutionIds"]:
        query = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        if query.get("WorkGroup") != settings.name:
            raise LabError("query_ownership_mismatch")
        if query["Status"]["State"] in {"QUEUED", "RUNNING"}:
            athena.stop_query_execution(QueryExecutionId=query_id)
            active.append(query_id)
    for _ in range(30):
        pending_jobs = [
            jid
            for jid in running
            if glue.get_job_run(
                JobName=settings.name,
                RunId=jid,
            )["JobRun"]["JobRunState"]
            in {"STARTING", "RUNNING", "STOPPING", "WAITING"}
        ]
        pending_queries = [
            qid
            for qid in active
            if athena.get_query_execution(
                QueryExecutionId=qid,
            )["QueryExecution"]["Status"]["State"]
            in {"QUEUED", "RUNNING"}
        ]
        if not pending_jobs and not pending_queries:
            return {"stopped_job_runs": len(running), "stopped_queries": len(active)}
        sleep(2)
    raise LabError("workload_stop_timeout")


def empty_owned_bucket(s3, settings):
    """Verify owner, region and tags again before any destructive bucket call."""
    verify_bucket(s3, settings)
    from cloud.aws.foundations import verify_bucket_security

    verify_bucket_security(s3, settings)
    bucket = {"Bucket": settings.bucket, "ExpectedBucketOwner": settings.account}
    pages, versions, next_key, next_version = 0, [], None, None
    while True:
        args = {**bucket, "MaxKeys": 1000}
        if next_key:
            args["KeyMarker"] = next_key
        if next_version:
            args["VersionIdMarker"] = next_version
        page = s3.list_object_versions(**args)
        pages += 1
        versions += [
            {"Key": v["Key"], "VersionId": v["VersionId"]}
            for v in page.get("Versions", []) + page.get("DeleteMarkers", [])
        ]
        if pages > 2 or any(not settings.owned_key(v["Key"]) for v in versions):
            raise LabError("unexpected_object_or_inventory_limit")
        if not page.get("IsTruncated"):
            break
        if pages == 2:
            raise LabError("object_inventory_limit")
        next_key, next_version = page["NextKeyMarker"], page.get("NextVersionIdMarker")
    uploads = s3.list_multipart_uploads(**bucket, MaxUploads=100)
    if uploads.get("IsTruncated") or any(
        not settings.owned_key(v["Key"]) for v in uploads.get("Uploads", [])
    ):
        raise LabError("multipart_ownership_or_limit")
    # Validate every key before the first destructive call.
    for upload in uploads.get("Uploads", []):
        s3.abort_multipart_upload(
            **bucket, Key=upload["Key"], UploadId=upload["UploadId"]
        )
    for start in range(0, len(versions), 1000):
        response = s3.delete_objects(
            **bucket,
            Delete={"Objects": versions[start : start + 1000], "Quiet": True},
        )
        if response.get("Errors"):
            raise LabError("object_deletion_unverified")
    remaining = s3.list_object_versions(**bucket, MaxKeys=1)
    incomplete = s3.list_multipart_uploads(**bucket, MaxUploads=1)
    if (
        remaining.get("Versions")
        or remaining.get("DeleteMarkers")
        or incomplete.get("Uploads")
    ):
        raise LabError("bucket_not_empty")
    return {
        "object_versions_removed": len(versions),
        "multipart_uploads_aborted": len(uploads.get("Uploads", [])),
    }


MANAGED_TYPES = frozenset(
    {
        "aws_glue_job",
        "aws_glue_catalog_database",
        "aws_glue_catalog_table",
        "aws_athena_workgroup",
        "aws_cloudwatch_log_group",
    }
)
FOUNDATION_DATA_TYPES = frozenset(
    {
        "aws_s3_bucket",
        "aws_s3_bucket_policy",
        "aws_iam_role",
        "aws_iam_policy",
    }
)


def verify_state(state, settings, outputs):
    """Reject legacy managed foundations and foreign state before plan/destroy."""
    root = state.get("values", {}).get("root_module", {})
    if root.get("child_modules") or not root.get("resources"):
        raise LabError("unsupported_or_empty_state")
    managed = 0
    for resource in root["resources"]:
        kind = resource.get("type", "")
        value = resource.get("values", {})
        if resource.get("mode") == "data":
            if kind not in FOUNDATION_DATA_TYPES:
                raise LabError("foreign_foundation_data")
            if kind == "aws_s3_bucket":
                valid = (
                    value.get("bucket") == settings.bucket
                    and value.get("arn") == f"arn:aws:s3:::{settings.bucket}"
                )
            elif kind == "aws_s3_bucket_policy":
                valid = value.get("bucket") == settings.bucket
            elif kind == "aws_iam_role":
                valid = value.get("arn") == settings.glue_role_arn
            else:
                valid = value.get("arn") == settings.glue_boundary_arn
            if not valid:
                raise LabError("foreign_foundation_data")
            continue
        if resource.get("mode") != "managed" or kind not in MANAGED_TYPES:
            raise LabError("foreign_or_owner_managed_terraform_state")
        managed += 1
        valid = False
        if kind in {"aws_glue_job", "aws_athena_workgroup"}:
            valid = (
                value.get("name") == settings.name and value.get("id") == settings.name
            )
        elif kind == "aws_glue_catalog_database":
            valid = (
                value.get("name") == settings.database
                and value.get("catalog_id") == settings.account
                and value.get("id") == f"{settings.account}:{settings.database}"
            )
        elif kind == "aws_glue_catalog_table":
            from cloud.aws.contracts import TABLES

            name = value.get("name")
            valid = (
                name in {*TABLES, "store_units"}
                and value.get("database_name") == settings.database
                and value.get("catalog_id") == settings.account
                and value.get("id") == f"{settings.account}:{settings.database}:{name}"
            )
        elif kind == "aws_cloudwatch_log_group":
            valid = value.get("name") in outputs["log_groups"] and value.get(
                "id"
            ) == value.get("name")
        if not valid:
            raise LabError("foreign_or_unexpected_terraform_state")
        tags = value.get("tags_all") or value.get("tags")
        if tags:
            require_tags(tags, settings)
    if not managed:
        raise LabError("unsupported_or_empty_state")
    return True
