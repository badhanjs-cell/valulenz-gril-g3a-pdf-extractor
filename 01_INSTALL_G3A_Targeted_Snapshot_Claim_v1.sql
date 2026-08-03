-- ============================================================================
-- VALULENZ GRIL G3A — TARGETED SNAPSHOT EXTRACTION CLAIM v1.0
-- Additive, service-role only, and safe for controlled Make runs.
-- ============================================================================

begin;

create or replace function gril.claim_text_extraction_job_by_snapshot_v1(
    p_snapshot_id bigint,
    p_worker_id text,
    p_lease_seconds integer default 3600
)
returns jsonb
language plpgsql
security definer
set search_path = gril, public, pg_temp
as $function$
declare
    v_job gril.text_extraction_job%rowtype;
    v_snapshot gril.document_snapshot%rowtype;
    v_document gril.regulatory_document%rowtype;
begin
    if p_snapshot_id is null then
        raise exception using
            errcode = 'G3AT1',
            message = 'Snapshot ID is required.';
    end if;

    if nullif(btrim(p_worker_id), '') is null then
        raise exception using
            errcode = 'G3AT2',
            message = 'Worker ID is required.';
    end if;

    if p_lease_seconds < 300 or p_lease_seconds > 7200 then
        raise exception using
            errcode = 'G3AT3',
            message = 'Lease must be between 300 and 7200 seconds.';
    end if;

    select *
    into v_job
    from gril.text_extraction_job
    where snapshot_id = p_snapshot_id
      and job_status in ('PENDING', 'RETRY_WAIT')
      and next_attempt_at <= clock_timestamp()
    for update skip locked
    limit 1;

    if not found then
        return jsonb_build_object(
            'success', true,
            'claimed', false,
            'status', 'GRIL_G3A_TARGET_EXTRACTION_JOB_NOT_AVAILABLE',
            'snapshot_id', p_snapshot_id
        );
    end if;

    update gril.text_extraction_job
    set
        job_status = 'LEASED',
        lease_token = gen_random_uuid(),
        leased_by = p_worker_id,
        lease_started_at = clock_timestamp(),
        lease_expires_at =
            clock_timestamp() + make_interval(secs => p_lease_seconds),
        attempt_count = attempt_count + 1,
        updated_at = clock_timestamp()
    where id = v_job.id
    returning *
    into v_job;

    select *
    into strict v_snapshot
    from gril.document_snapshot
    where id = v_job.snapshot_id;

    select *
    into strict v_document
    from gril.regulatory_document
    where id = v_job.regulatory_document_id;

    return jsonb_build_object(
        'success', true,
        'claimed', true,
        'status', 'GRIL_G3A_TARGET_TEXT_EXTRACTION_JOB_CLAIMED',
        'job_id', v_job.id,
        'lease_token', v_job.lease_token,
        'lease_expires_at', v_job.lease_expires_at,
        'snapshot_id', v_snapshot.id,
        'regulatory_document_id', v_document.id,
        'source_id', v_document.source_id,
        'document_title', v_document.document_title,
        'document_version', v_document.document_version,
        'original_language', v_document.original_language,
        'mime_type', v_snapshot.mime_type,
        'byte_size', v_snapshot.byte_size,
        'content_sha256', v_snapshot.content_sha256,
        'storage_bucket', v_snapshot.storage_bucket,
        'storage_object_path', v_snapshot.storage_object_path,
        'resolved_url', v_snapshot.resolved_url,
        'extraction_profile', v_job.extraction_profile
    );
end;
$function$;

create or replace function public.claim_text_extraction_job_by_snapshot_v1(
    p_snapshot_id bigint,
    p_worker_id text,
    p_lease_seconds integer default 3600
)
returns jsonb
language sql
security definer
set search_path = ''
as $function$
    select gril.claim_text_extraction_job_by_snapshot_v1(
        p_snapshot_id,
        p_worker_id,
        p_lease_seconds
    );
$function$;

revoke all
on function public.claim_text_extraction_job_by_snapshot_v1(
    bigint, text, integer
)
from public, anon, authenticated;

grant execute
on function public.claim_text_extraction_job_by_snapshot_v1(
    bigint, text, integer
)
to service_role;

notify pgrst, 'reload schema';

commit;

select jsonb_pretty(
    jsonb_build_object(
        'success', true,
        'status', 'GRIL_G3A_TARGETED_CLAIM_INSTALLED',
        'rpc', 'public.claim_text_extraction_job_by_snapshot_v1(bigint,text,integer)'
    )
);
