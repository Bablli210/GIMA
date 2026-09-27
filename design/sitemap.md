# GIMA website: sitemap v1

Wireframes (desktop 1440 px and phone 390 px, clickable): https://claude.ai/artifact/AVQQBeMjKei4R3Cw1nnuP4
Moodboard: https://claude.ai/artifact/DPecsuSP3CdPFnxHhwSfkW

## Assumptions

- Direction: "Drawn, then built" (see the moodboard).
- Retail leads. Hospitality, corporate, entertainment and residential sit under Work (filters) and Services (sectors). Sector pages are phase 2.
- English at launch. Every layout mirrors for Arabic under `/ar/…` once that is confirmed.
- Anything in [brackets] is for GIMA to supply. Sections without verified content are hidden at launch.

## Pages

```
Home                      /
├── Work                  /work              the register: list · cards · same-scale plan, filters, group by brand or city
│   └── Project page      /work/[project]    one template, ×N
│       ├── Case sheet    PDF, generated from the project data
│       └── 3D model      flagships only, loads on tap
├── Services              /services          five trades · two ways to work · sectors · working in malls · questions
├── Process               /process           example programme in weeks · five stages · mall approvals · handover and aftercare
├── About                 /about             since 1980 · Elbanna Design Group · team · built by our own team · mission and values
└── Contact               /contact           enquiry form (opening date first) · named contact · phone · WhatsApp · office and map link

On every page: header (Work · Services · Process · About · Contact · EN/عربي · Start a project),
footer directory of every project, title block (desktop only).

Utility: /credentials.pdf · /privacy · 404 · /ar/… (Arabic mirror)
Phase 2: sector pages · map view in Work · photoreal store captures · news and press
```

## Page inventory

| Page | Address | Its job | Main action | GIMA to supply |
|---|---|---|---|---|
| Home | `/` | Answer "is this the right company?" in one screen | Start a project | Newest flagship photo, three flagships, brand name permissions |
| Work | `/work` | Show the whole track record, scannable in 30 seconds | Open a project | Project list: brand, client or operator, sector, mall, city, m², trades delivered, year |
| Project page | `/work/[project]` | Answer the shortlisting questions for one store | Download case sheet · Start a project | Photos with year, trade split, programme weeks, drawings, quote with permission, 3D files for 2–3 flagships |
| Services | `/services` | Explain turnkey as a list of trades, honestly | Start a project | What each trade includes, mall experience, answers to the questions |
| Process | `/process` | Show opening on a known date, and who is accountable | Start a project | Typical durations, what the client receives at each stage, aftercare terms |
| About | `/about` | Prove a stable company with its own people | Start a project | Milestones, team names and photos, workshop and in-house trades |
| Contact | `/contact` | Turn interest into a call with a named person | Send enquiry · call · WhatsApp | Contact name and title, numbers, office address, response time |
| Credentials PDF | `/credentials.pdf` | A document to forward internally | Download | Nothing extra: built from site data |
| Privacy · 404 | `/privacy` | Utility | Back to Work | Privacy wording approved by GIMA's legal adviser |

## Key journeys

1. **Head of store development, brand entering Egypt (desktop):** search or LinkedIn → Home → Work, retail, grouped by brand → Project page → Contact.
2. **Mall developer or leasing team (desktop):** referral from a tenant → Home → Process → About → credentials PDF, then Contact.
3. **Colleague shares one project on WhatsApp (phone):** link → Project page → case sheet PDF → Work → call or WhatsApp.

## Project page order

Each section renders only when its data exists.

1. Cover and title block (client, location, area, opened, programme, role per trade)
2. Brief, constraint, response
3. Scope delivered
4. Elevation with keynotes
5. Shell to opening (only with a same-position shell photo)
6. Detail shots
7. Plan (only if drawings are supplied)
8. Programme in weeks
9. 3D model (flagships only)
10. Client's words
11. Case sheet PDF
12. Next project
