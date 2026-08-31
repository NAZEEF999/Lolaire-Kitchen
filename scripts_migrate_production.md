# Running migrations against production (Vercel)

`vercel.json`'s `buildCommand` already tries to run `migrate`
automatically on every deploy. **Don't rely on that alone** — Vercel's
Python builds run in an ephemeral, serverless environment, and
whether a build-time command reliably keeps its database connection
open long enough, or runs in an environment that can actually reach
your database, is a known rough edge for Django-on-Vercel specifically
(this is very likely what caused the "relation menu_menuitem does not
exist" error before: migrations never actually ran against the real
production database).

**The dependable way**: run migrations yourself, from your own
machine, against the production database, right after each deploy
that adds a migration:

```bash
DATABASE_URL="<paste your production DATABASE_URL here>" python manage.py migrate
```

Get the real `DATABASE_URL` value from your Vercel project's
Environment Variables page (or your Postgres provider's dashboard —
Neon, Supabase, Vercel Postgres, etc.) — don't hardcode it in any file.

Do this once, manually, after every deploy that includes a new
migration, until/unless you set up a proper CI step to automate it.
It takes 10 seconds and directly prevents the exact error you already
hit once.
