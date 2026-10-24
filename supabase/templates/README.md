# Supabase email templates

Branded versions of the one-time-code emails sent by `POST /profile/sync` and `POST /profile/login`.
Paste each file into **Supabase Dashboard → Authentication → Emails → Templates**.

| File | Dashboard template | Sent when | Suggested subject |
| ---- | ------------------ | --------- | ----------------- |
| `confirm_signup.html` | Confirm signup | Syncing an email for the first time (`sign_in_with_otp` creates the auth user) | `Your Jobee code: {{ .Token }}` |
| `magic_link.html` | Magic Link | Logging in, or syncing an email Supabase already knows (`should_create_user: false` on login) | `Your Jobee login code: {{ .Token }}` |

Supabase picks the template by whether the auth user already exists, not by which endpoint sent it, so
`magic_link.html` is worded to also make sense for a repeat sync.

Both show `{{ .Token }}` (the code the app asks for) and no link: the app verifies the code with
`verify_otp`, so a magic link would not log anyone in.

Styles are inline and the layout is tables, for email clients. Nunito loads where the client allows web fonts
and falls back to Segoe UI / Helvetica / Arial elsewhere.
