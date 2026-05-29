-- ============================================================================
-- content-calendar-scheduler — Mission Control data-model migration
-- ============================================================================
-- STAGED, NOT APPLIED. Review, then run against the Mission Control Supabase
-- (Projects/missioncontrol/dashboard) ONLY after Mario approves. Mission
-- Control is GitHub + VPS (NO Vercel). Every statement is idempotent so it is
-- safe to re-run.
--
-- Adds a calendar + status-lifecycle layer onto the existing `ad_creatives`
-- table so one trigger can fan a client's pillars into ~30 dated, format-
-- assigned DRAFT rows that the existing Meta Graph API scheduler consumes.
-- Shares the same table as the ad-variant-fanout creative-slate ledger.
-- ============================================================================

-- 1. New columns (additive, non-breaking; existing `status` column untouched) -
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS scheduled_at      timestamptz;
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS lifecycle_status  text NOT NULL DEFAULT 'draft';
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS platform          text NOT NULL DEFAULT 'facebook';
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS content_format    text;          -- remotion_listicle | ugc_variant | before_after | price_card | cinematic_clip
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS calendar_slot     date;          -- the day this piece is planned for
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS posted_at         timestamptz;
ALTER TABLE ad_creatives ADD COLUMN IF NOT EXISTS post_permalink    text;          -- filled after Graph API publish (verification rule)

-- 2. Lifecycle guard. draft -> approved -> scheduled -> posted -> tracked.
--    Added NOT VALID so pre-existing rows are never rejected; validate after backfill.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ad_creatives_lifecycle_status_chk') THEN
    ALTER TABLE ad_creatives
      ADD CONSTRAINT ad_creatives_lifecycle_status_chk
      CHECK (lifecycle_status IN ('draft','approved','scheduled','posted','tracked','archived'))
      NOT VALID;
  END IF;
END $$;

-- 3. Scheduler query index: "give me approved+scheduled rows due now".
CREATE INDEX IF NOT EXISTS idx_ad_creatives_due
  ON ad_creatives (scheduled_at)
  WHERE lifecycle_status = 'scheduled';

-- 4. Per-client month view index.
CREATE INDEX IF NOT EXISTS idx_ad_creatives_calendar
  ON ad_creatives (client_id, calendar_slot);

-- 5. Convenience view the calendar UI + Claude ("what's queued next week?") read.
CREATE OR REPLACE VIEW content_calendar AS
SELECT
  id,
  client_id,
  calendar_slot,
  scheduled_at,
  platform,
  content_format,
  lifecycle_status,
  name,
  copy_headline,
  post_permalink
FROM ad_creatives
WHERE calendar_slot IS NOT NULL
ORDER BY client_id, calendar_slot, scheduled_at;

-- ---------------------------------------------------------------------------
-- ROLLBACK (only if needed):
--   DROP VIEW IF EXISTS content_calendar;
--   DROP INDEX IF EXISTS idx_ad_creatives_due;
--   DROP INDEX IF EXISTS idx_ad_creatives_calendar;
--   ALTER TABLE ad_creatives DROP CONSTRAINT IF EXISTS ad_creatives_lifecycle_status_chk;
--   ALTER TABLE ad_creatives
--     DROP COLUMN IF EXISTS scheduled_at, DROP COLUMN IF EXISTS lifecycle_status,
--     DROP COLUMN IF EXISTS platform,     DROP COLUMN IF EXISTS content_format,
--     DROP COLUMN IF EXISTS calendar_slot, DROP COLUMN IF EXISTS posted_at,
--     DROP COLUMN IF EXISTS post_permalink;
-- ---------------------------------------------------------------------------
