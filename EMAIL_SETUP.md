# Setting up automatic booking emails

The code side of this is done: whenever a booking is created, cancelled, or
amended (from the site or the dashboard), `apps/dashboard/signals.py` now
calls into `apps/bookings/emails.py`, which renders one of the templates in
`templates/emails/` and sends it to the client. Locally this just prints to
your terminal (the `dev` console email backend) — nothing gets sent until
you complete the steps below in production.

## 1. Sign up with a transactional email provider

Recommended: **Resend** (resend.com) — free for up to 3,000 emails/month on
one verified domain, and gives you both an SMTP relay and a delivery
dashboard. Postmark and SendGrid work the same way if you'd rather use one
of those.

1. Create an account.
2. Add `caldwellcosmetics.co.uk` as a domain and verify it — the provider
   will give you 3–4 DNS records (SPF, DKIM, and usually a return-path/DMARC
   record) to add wherever your domain's DNS is managed (GoDaddy, 123-Reg,
   Cloudflare, etc. — wherever you bought/host the domain, not Render).
   DNS changes can take a few minutes to a few hours to verify.
3. Once verified, generate SMTP credentials (host, port, username,
   password) from the provider's dashboard.

## 2. Set the credentials as Render environment variables

These must be set on Render (not just in your local `.env` — Render does
not read that file). In the Render dashboard, open your web service →
**Environment**, and add these, filling in your real values:

| Key                   | Value                                                |
|-----------------------|------------------------------------------------------|
| `EMAIL_HOST`          | `smtp.resend.com`                                    |
| `EMAIL_PORT`          | `587`                                                |
| `EMAIL_HOST_USER`     | `resend`                                             |
| `EMAIL_HOST_PASSWORD` | your Resend API key                                  |
| `DEFAULT_FROM_EMAIL`  | `Caldwell Cosmetics <info@caldwellcosmetics.co.uk>`  |

(Swap the host/username for whatever your chosen provider's SMTP docs say —
Resend's SMTP username is literally `resend`; Postmark and SendGrid use
different values.)

Saving environment variables triggers a redeploy on Render.

## 3. Test locally first (optional but recommended)

With the `dev` settings (console backend), making a test booking will print
the full email to your terminal instead of sending it — a safe way to check
the wording and layout before touching production:

```
python manage.py runserver
```

Then make a test booking through the site while the server is running and
check the terminal output.

## 4. Deploy and test for real

Once the environment variables are set on Render and the code is deployed:

1. Make a real test booking (or amend/cancel one) using an email address you
   can check.
2. Confirm it arrives, check it doesn't land in spam, and check it renders
   properly on both desktop and mobile mail apps.
3. Keep an eye on your provider's dashboard for the first few days —
   it'll show delivered/bounced/spam-complaint counts.

## Where things live

- `apps/bookings/emails.py` — the three send functions
  (`send_booking_confirmation`, `send_booking_cancelled`, `send_booking_amended`).
- `templates/emails/` — the HTML templates (`_base_email.html` is the shared
  wrapper; the other three extend it).
- `apps/dashboard/signals.py` — `on_booking_saved` calls the right send
  function whenever a booking is created, cancelled, or amended.
- `config/settings/prod.py` — reads the SMTP settings from environment
  variables (set in the Render dashboard).

Sending failures are caught and logged rather than raised, so if the email
provider is ever slow or down, bookings will still go through — clients
just won't get the email until the next successful attempt for a
different booking (there's no automatic retry for a single failed send).
