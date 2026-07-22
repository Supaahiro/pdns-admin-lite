# Frontend conventions (UX)

Patterns this codebase expects new frontend code to follow. See the root [README.md](../README.md) for what the app does and how to run it; this file is about how it's built.

- **Destructive actions never use `confirm()`.** `ConfirmDialog.vue` is a single reusable modal with two modes: a plain confirmation showing exactly what's being deleted (record delete — type, name, and every value in the rrset), and a type-the-name mode for zone delete, where the confirm button stays disabled until the typed text matches the zone name exactly.
- **Errors are split by where they belong.** A failed page load (zone/zone-list fetch) surfaces as a dismissible banner at the top of the page — it isn't the user's fault and isn't tied to a field. A failed save/delete surfaces inline, next to the form or inside the still-open confirm dialog, so the user can see what went wrong and immediately retry without losing their place.
- **The record table has a client-side filter** (name/type/content) and a **copy button** on every record value.
- **Pagination is client-side only, via the shared `Paginator.vue`** (used by the zones table and, after filtering, the record table). PowerDNS has no server-side pagination to delegate to — `GET /zones` and a zone's `rrsets` always come back in full — so there's no backend benefit to a paginated endpoint, only a smaller DOM for the browser to render. `Paginator.vue` renders nothing when everything already fits on one page.
- **The zone serial briefly highlights** after any mutation that changes it — visible confirmation that PowerDNS accepted the change and bumped the zone, not just that the request returned 2xx.
