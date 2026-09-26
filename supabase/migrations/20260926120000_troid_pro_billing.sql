-- troid Pro billing: who holds troid Pro, as Stripe reports it. Handoff "Stripe Managed Payments for troid Pro"
-- (2026-09-26). Test mode only until the launch gates clear: Vercel Pro, counsel, updated Terms, the owner's approval.
--
-- One row per Supabase user and Stripe mode, so a test subscription never counts in live mode. Only the Stripe webhook
-- (web/api/stripe-webhook.js, with the service key) writes it, through pro_apply_stripe_event(), which records each
-- Stripe event id and applies the event's change in one transaction: a repeated event changes nothing. A signed-in user
-- reads their own row, through pro_status() or the table, and writes nothing. Access comes from these rows alone, never
-- from Checkout's success page. Tests: web/test_pro.js runs this file in PGlite (real Postgres) behind a fake PostgREST.

create table if not exists public.pro_accounts (
  user_id                uuid        not null references auth.users (id) on delete cascade,
  livemode               boolean     not null,
  stripe_customer_id     text        unique,
  stripe_subscription_id text        unique,
  status                 text,          -- the subscription's status as Stripe last reported it
  price_id               text,
  pro_until              timestamptz,   -- the current period's end; once the subscription has ended, when it ended
  cancel_at_period_end   boolean     not null default false,
  payment_failed_at      timestamptz,   -- the latest invoice.payment_failed; cleared when Stripe reports the subscription active
  subscription_event_at  timestamptz,   -- when Stripe created the newest subscription event applied to this row
  updated_at             timestamptz not null default now(),
  primary key (user_id, livemode)
);

create table if not exists public.stripe_events (
  id          text        primary key,  -- evt_…: recorded once; a repeat is answered "duplicate" and changes nothing
  type        text        not null,
  livemode    boolean     not null,
  created_at  timestamptz not null,     -- the event's own time at Stripe
  received_at timestamptz not null default now(),
  outcome     text        not null      -- linked, applied, past_due, stale, other_subscription, unmatched, conflict, ignored
);

alter table public.pro_accounts enable row level security;
alter table public.stripe_events enable row level security;

drop policy if exists "pro_accounts: a user reads their own" on public.pro_accounts;
create policy "pro_accounts: a user reads their own" on public.pro_accounts
  for select to authenticated using ((select auth.uid()) = user_id);

-- Supabase grants every new table to anon and authenticated by default; RLS already stops them, and this says so twice.
-- The one grant is stated rather than assumed: a signed-in user may read, and the policy above says which row.
revoke all on public.pro_accounts from anon;
revoke insert, update, delete, truncate, references, trigger on public.pro_accounts from authenticated;
grant select on public.pro_accounts to authenticated;
revoke all on public.stripe_events from anon, authenticated;

-- The one entitlement rule. Pro while Stripe reports the subscription active, trialing or past_due (a failed renewal
-- keeps access while Stripe retries; "unpaid" or "canceled" is Stripe giving up) and its period hasn't ended. A
-- subscription set to cancel locks at the end of its period; one set to renew keeps 24 hours past it, so a renewal
-- whose webhook is late doesn't lock out someone who paid.
create or replace function public.pro_entitled(p_status text, p_until timestamptz, p_cancel_at_period_end boolean)
returns boolean
language sql stable
set search_path = ''
as $$
  select coalesce(p_status in ('active', 'trialing', 'past_due'), false)
     and p_until is not null
     and now() < p_until + case when coalesce(p_cancel_at_period_end, false) then interval '0' else interval '24 hours' end
$$;

-- The signed-in user's own row in one mode, with the rule applied. Invoker's rights: RLS decides what it can see.
create or replace function public.pro_status(p_livemode boolean)
returns table (pro boolean, status text, pro_until timestamptz, cancel_at_period_end boolean,
               payment_failed_at timestamptz, stripe_customer_id text)
language sql stable security invoker
set search_path = ''
as $$
  select public.pro_entitled(a.status, a.pro_until, a.cancel_at_period_end), a.status, a.pro_until,
         a.cancel_at_period_end, a.payment_failed_at, a.stripe_customer_id
    from public.pro_accounts a
   where a.user_id = (select auth.uid()) and a.livemode = p_livemode
$$;

-- The webhook's only write. web/lib/pro.js turns a verified Stripe event into these arguments. Stripe delivers at least
-- once and in no particular order, so: a repeated event id changes nothing; an event older than the newest subscription
-- event already applied changes nothing; an ended subscription never comes back, nor takes the row from a newer one;
-- and, inside one second, a status earlier in a subscription's life (incomplete) doesn't replace a later one (active).
create or replace function public.pro_apply_stripe_event(
  p_event_id             text,
  p_type                 text,
  p_livemode             boolean,
  p_created              timestamptz,
  p_user_id              uuid        default null,
  p_customer             text        default null,
  p_subscription         text        default null,
  p_status               text        default null,
  p_price                text        default null,
  p_pro_until            timestamptz default null,
  p_cancel_at_period_end boolean     default null
) returns text
language plpgsql security definer
set search_path = ''
as $$
declare
  v_user    uuid := p_user_id;
  v_row     public.pro_accounts%rowtype;
  v_outcome text;
begin
  if p_event_id is null or p_type is null or p_livemode is null or p_created is null then
    raise exception 'pro_apply_stripe_event: the event id, type, mode and time are required';
  end if;

  insert into public.stripe_events (id, type, livemode, created_at, outcome)
  values (p_event_id, p_type, p_livemode, p_created, 'received')
  on conflict (id) do nothing;
  if not found then
    return 'duplicate';
  end if;

  -- whose: the user troid's checkout named on the Stripe object, else the row already linked to it
  if v_user is not null and not exists (select 1 from auth.users u where u.id = v_user) then
    v_user := null;
  end if;
  if v_user is null and p_subscription is not null then
    select a.user_id into v_user from public.pro_accounts a
     where a.stripe_subscription_id = p_subscription and a.livemode = p_livemode;
  end if;
  if v_user is null and p_customer is not null then
    select a.user_id into v_user from public.pro_accounts a
     where a.stripe_customer_id = p_customer and a.livemode = p_livemode;
  end if;

  begin
    if v_user is null then
      v_outcome := 'unmatched';

    elsif p_type = 'checkout.session.completed' then
      insert into public.pro_accounts (user_id, livemode) values (v_user, p_livemode) on conflict do nothing;
      select * into v_row from public.pro_accounts a where a.user_id = v_user and a.livemode = p_livemode for update;
      if v_row.stripe_subscription_id is null or v_row.stripe_subscription_id = p_subscription then
        update public.pro_accounts a
           set stripe_subscription_id = coalesce(p_subscription, a.stripe_subscription_id),
               stripe_customer_id     = coalesce(p_customer, a.stripe_customer_id),
               updated_at             = now()
         where a.user_id = v_user and a.livemode = p_livemode;
        v_outcome := 'linked';
      elsif public.pro_entitled(v_row.status, v_row.pro_until, v_row.cancel_at_period_end) then
        v_outcome := 'other_subscription';   -- a second subscription while the first still grants Pro: for the owner to refund
      else
        -- a new subscription after one that no longer grants Pro: its status and period come with its own events
        update public.pro_accounts a
           set stripe_subscription_id = p_subscription,
               stripe_customer_id     = coalesce(p_customer, a.stripe_customer_id),
               status = null, price_id = null, pro_until = null, cancel_at_period_end = false, payment_failed_at = null,
               updated_at             = now()
         where a.user_id = v_user and a.livemode = p_livemode;
        v_outcome := 'linked';
      end if;

    elsif p_type in ('customer.subscription.created', 'customer.subscription.updated', 'customer.subscription.deleted') then
      insert into public.pro_accounts (user_id, livemode) values (v_user, p_livemode) on conflict do nothing;
      select * into v_row from public.pro_accounts a where a.user_id = v_user and a.livemode = p_livemode for update;
      if v_row.subscription_event_at is not null and p_created < v_row.subscription_event_at then
        v_outcome := 'stale';
      elsif v_row.stripe_subscription_id = p_subscription then
        if v_row.status in ('canceled', 'incomplete_expired') then
          v_outcome := 'stale';
        elsif p_created = v_row.subscription_event_at
              and (case p_status when 'incomplete' then 0 when 'canceled' then 2 when 'incomplete_expired' then 2 else 1 end)
                < (case v_row.status when 'incomplete' then 0 when 'canceled' then 2 when 'incomplete_expired' then 2 else 1 end) then
          v_outcome := 'stale';
        else
          v_outcome := 'applied';
        end if;
      elsif v_row.stripe_subscription_id is not null and p_status in ('canceled', 'incomplete_expired') then
        v_outcome := 'stale';                -- an ended subscription never takes the row from another
      elsif v_row.stripe_subscription_id is not null
            and public.pro_entitled(v_row.status, v_row.pro_until, v_row.cancel_at_period_end) then
        v_outcome := 'other_subscription';
      else
        v_outcome := 'applied';              -- the row's first subscription, or a new one after one that ended
      end if;
      if v_outcome = 'applied' then
        update public.pro_accounts a
           set stripe_subscription_id = p_subscription,
               stripe_customer_id     = coalesce(p_customer, a.stripe_customer_id),
               -- a state from before a failed payment doesn't show the payment made
               status                 = case when p_status = 'active' and a.payment_failed_at is not null
                                                  and p_created < a.payment_failed_at then 'past_due' else p_status end,
               price_id               = coalesce(p_price, a.price_id),
               pro_until              = p_pro_until,
               cancel_at_period_end   = coalesce(p_cancel_at_period_end, false),
               payment_failed_at      = case when p_status = 'active' and (a.payment_failed_at is null
                                                  or p_created >= a.payment_failed_at) then null else a.payment_failed_at end,
               subscription_event_at  = p_created,
               updated_at             = now()
         where a.user_id = v_user and a.livemode = p_livemode;
      end if;

    elsif p_type = 'invoice.payment_failed' then
      -- past due, not locked: access continues while Stripe retries, until it reports the subscription unpaid or canceled
      select * into v_row from public.pro_accounts a where a.user_id = v_user and a.livemode = p_livemode for update;
      if not found then
        v_outcome := 'unmatched';
      elsif v_row.stripe_subscription_id is distinct from p_subscription then
        v_outcome := 'other_subscription';
      elsif v_row.subscription_event_at is not null and p_created < v_row.subscription_event_at then
        v_outcome := 'stale';
      else
        update public.pro_accounts a
           set payment_failed_at = greatest(a.payment_failed_at, p_created),
               status            = case when a.status in ('active', 'trialing') then 'past_due' else a.status end,
               updated_at        = now()
         where a.user_id = v_user and a.livemode = p_livemode;
        v_outcome := 'past_due';
      end if;

    else
      v_outcome := 'ignored';
    end if;
  exception when unique_violation then
    v_outcome := 'conflict';                 -- a customer or subscription already linked to another user: for the owner
  end;

  update public.stripe_events set outcome = v_outcome where id = p_event_id;
  return v_outcome;
end;
$$;

revoke execute on function public.pro_entitled(text, timestamptz, boolean) from public, anon;
grant execute on function public.pro_entitled(text, timestamptz, boolean) to authenticated, service_role;
revoke execute on function public.pro_status(boolean) from public, anon;
grant execute on function public.pro_status(boolean) to authenticated, service_role;
revoke execute on function public.pro_apply_stripe_event(text, text, boolean, timestamptz, uuid, text, text, text, text, timestamptz, boolean)
  from public, anon, authenticated;
grant execute on function public.pro_apply_stripe_event(text, text, boolean, timestamptz, uuid, text, text, text, text, timestamptz, boolean)
  to service_role;
