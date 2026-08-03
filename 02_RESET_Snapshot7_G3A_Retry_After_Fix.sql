-- Run only after the new Railway PDF extractor and Make blueprint are ready.
-- Preserves attempt_count and prior error evidence.

begin;

update gril.text_extraction_job
set
    job_status = 'PENDING',
    priority = 1,
    next_attempt_at = clock_timestamp(),
    lease_token = null,
    leased_by = null,
    lease_started_at = null,
    lease_expires_at = null,
    last_error_code = null,
    last_error_message = null,
    updated_at = clock_timestamp()
where id = 'ff02a098-d4d7-4aa4-b500-bb2581d5c140'::uuid
  and snapshot_id = 7
  and job_status = 'RETRY_WAIT'
  and attempt_count < maximum_attempts;

select
    id as job_id,
    snapshot_id,
    regulatory_document_id,
    job_status,
    priority,
    attempt_count,
    maximum_attempts,
    next_attempt_at,
    last_error_code,
    last_error_message
from gril.text_extraction_job
where id = 'ff02a098-d4d7-4aa4-b500-bb2581d5c140'::uuid;

commit;
