with src as (

    select
        player_id,
        analysis_text,
        news_text,
        news_updated_at,
        raw_latest_news,

        injury_text,
        injury_msgs_raw,
        is_injured,

        source_event_date,
        inserted_at,
        updated_at
    from {{ source('landing', 'fantrax_player_news') }}
),

clean as (

    select
        player_id::text as player_id,

        nullif(trim(analysis_text), '') as analysis_text,
        nullif(trim(news_text), '') as news_text,

        -- Some payloads store timestamps as strings; stage as text if uncertain
        -- If your landing column is timestamptz, this will just pass through.
        news_updated_at,

        raw_latest_news::jsonb as raw_latest_news,

        -- Injury text is already stripped of HTML in ingestion, but keep it defensive.
        nullif(regexp_replace(coalesce(injury_text, ''), '<[^>]+>', '', 'g'), '') as injury_text,

        injury_msgs_raw::jsonb as injury_msgs_raw,
        coalesce(is_injured, false) as is_injured,

        source_event_date,
        inserted_at,
        updated_at

    from src
),

parsed as (

    select
        c.*,

        -- Extract expected return date string after "Expected to return on "
        -- Example: "Expected to return on Tue Jan 20 - Late fitness test (Game-time decision)."
        case
            when c.injury_text ilike 'Expected to return on %' then
                nullif(
                    split_part(
                        replace(c.injury_text, 'Expected to return on ', ''),
                        ' - ',
                        1
                    ),
                    ''
                )
            else null
        end as injury_expected_return_raw,

        -- Everything after " - " becomes the status message
        case
            when c.injury_text ilike 'Expected to return on % - %' then
                nullif(split_part(c.injury_text, ' - ', 2), '')
            else
                -- If there's no prefix, treat full string as message
                nullif(c.injury_text, '')
        end as injury_message

    from clean c
),

normalized as (

    select
        p.*,

        -- Normalize to a small set of statuses you can use in projections.
        case
            when p.injury_message is null then 'healthy'

            -- Hard out / unavailable signals
            when p.injury_message ilike '%out for next game%' then 'out'
            when p.injury_message ilike '%out%' and p.injury_message not ilike '%game-time decision%' then 'out'

            -- Game-time decisions / late tests are typically doubtful/questionable
            when p.injury_message ilike '%game-time decision%' then 'doubtful'
            when p.injury_message ilike '%late fitness test%' then 'doubtful'

            -- Additional common phrasing (optional but useful)
            when p.injury_message ilike '%questionable%' then 'doubtful'
            when p.injury_message ilike '%doubtful%' then 'doubtful'
            when p.injury_message ilike '%probable%' then 'limited'
            when p.injury_message ilike '%fit%' then 'healthy'

            else 'unknown'
        end as injury_status,

        -- Convert expected return date if present. Fantrax string lacks year.
        -- We assume current season year based on today; if parsing fails, null.
        -- NOTE: Postgres to_date() cannot parse weekday tokens reliably; strip weekday.
        case
            when p.injury_expected_return_raw is null then null
            else
                -- injury_expected_return_raw example: "Tue Jan 20" or "Sat Apr 11"
                -- Remove leading weekday and parse "Mon DD"
                -- We then append a guessed year based on current_date:
                -- if return month < current month and we're in late year, assume next year.
                (
                    case
                        when length(p.injury_expected_return_raw) >= 7 then
                            -- remove weekday (first 3 chars) and any extra space
                            trim(substring(p.injury_expected_return_raw from 5))
                        else null
                    end
                )
        end as injury_expected_return_monthday

    from parsed p
),

final as (

    select
        n.player_id,

        n.analysis_text,
        n.news_text,
        n.news_updated_at,
        n.raw_latest_news,

        n.is_injured,
        n.injury_text,
        n.injury_expected_return_raw,
        n.injury_message,
        n.injury_status,

        -- Minutes multiplier to apply downstream (conservative defaults)
        case
            when n.injury_status = 'out' then 0.0
            when n.injury_status = 'doubtful' then 0.6
            when n.injury_status = 'limited' then 0.85
            when n.injury_status = 'healthy' then 1.0
            when n.injury_status = 'unknown' and n.is_injured = true then 0.85
            else 1.0
        end::numeric(6,3) as injury_minutes_multiplier,

        n.injury_msgs_raw,

        n.source_event_date,
        n.inserted_at,
        n.updated_at

    from normalized n
)

select * from final
