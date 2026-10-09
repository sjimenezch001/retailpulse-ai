# Offline placeholders only; the runner generates fresh owner verification.
aws_region              = "sa-east-1"
aws_profile             = "REPLACE_WITH_TEMPORARY_NON_ROOT_PROFILE"
account_id              = "000000000000"
environment             = "rp12-demo"
expires_on              = "2099-01-01" # Runner requires an approved date within seven days.
run_id                  = "000000000000000000000000"
code_digest             = "0000000000000000000000000000000000000000000000000000000000000000"
owner_bucket_name       = "retailpulse-rp12-demo-000000000000-sa-east-1"
owner_glue_role_arn     = "arn:aws:iam::000000000000:role/retailpulse-rp12-demo-glue"
owner_glue_boundary_arn = "arn:aws:iam::000000000000:policy/retailpulse-rp12-demo-glue-boundary"
bucket_policy_sha256    = "0000000000000000000000000000000000000000000000000000000000000000"
boundary_policy_sha256  = "0000000000000000000000000000000000000000000000000000000000000000"
enable_endpoint         = false
