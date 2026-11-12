# Publishing AAROH on Google Play

Everything Google asks for is prepared here, except the steps that need your Google account.
Images are in the project files under `aaroh/play-store/`: `icon-512.png`, `feature-graphic-1024x500.png` and six phone screenshots (1080×1920).

## 1. Before you start (one time)

| Step | Cost / time |
|---|---|
| Create a Google Play developer account at https://play.google.com/console (choose **Personal**) | $25 one time (~₹2,100) |
| Verify your identity (government ID) and your Android phone, as the console asks | 1-3 days |
| Have a contact email for the store listing (shown publicly) | |

New personal accounts must run a **closed test with at least 12 testers for 14 days** before the app can go to production. Friends or family with Android phones and a Gmail address are fine.

## 2. Build the upload file

Actions → **Release Android app** → Run workflow. The release contains `aaroh-<version>.aab`, the file Play needs.
Each run gets a higher version code automatically. Keep the signing key from `aaroh/android-signing/` safe; Play App Signing will use it as your upload key.

## 3. Create the app in Play Console

- App name: **AAROH: Personal Life OS**
- Default language: English (India)
- App or game: App. Free or paid: Free.

### Store listing

**Short description** (80 characters max):
> Plan your day, track money, investments, fitness and learning, with an AI coach.

**Full description**:
> AAROH is a personal life operating system: one calm place for the things you are trying to get better at.
>
> • Plan: tasks with priorities, due dates and reminders, a calendar, habits with streaks and goals with milestones. Smart planning fits your open tasks into your day.
> • Money: expenses and income in ₹, monthly budgets, subscriptions and savings goals, with clear charts of where your money goes.
> • Investments: mutual funds and SIPs, stocks, FD, PPF, EPF, NPS, gold and loans in one view. See net worth, allocation, returns and upcoming SIPs and EMIs.
> • Fitness: workouts with sets, protein and calories, steps, water, sleep and weight trend.
> • Learning: skills, roadmaps, daily learning logs, notes and interview preparation.
> • Work journal: what you did, problems solved and learnings, ready for appraisals.
> • Journal: daily reflections with mood, tags and photos.
> • Aaroh AI (optional): morning briefings, evening and weekly reviews, and coaches for career, money, fitness and habits. You choose exactly which sections the AI can read; your journal is private by default.
>
> Your data stays yours: export everything at any time or delete your account from Settings. No ads, no tracking.
>
> AAROH gives general information only. It is not financial, medical or mental-health advice.

- App icon: `icon-512.png`. Feature graphic: `feature-graphic-1024x500.png`. Phone screenshots: the six files in `screenshots/`.
- Category: **Productivity**. Tags: productivity, personal finance, habit tracker.

### App content (Policy section)

| Question | Answer |
|---|---|
| Privacy policy URL | `https://<your-server>/privacy.html` (e.g. https://aaroh-6j4z.onrender.com/privacy.html) |
| App access | Some functionality is restricted → give reviewers the demo login `demo@aaroh.app` / `Aaroh@2026` |
| Ads | No ads |
| Content rating questionnaire | Category "Utility, productivity, communication or other"; answer No to violence, sexual content, gambling, etc. Users can't interact with each other. Expected rating: Everyone / 3+ |
| Target audience | 18 and over |
| News app | No |
| Health apps | Yes, fitness tracking only (no medical features) |
| Financial features | Personal finance tracking only; the app does not provide loans, payments, trading or investment advice |
| Government app | No |
| Account deletion | In the app: Settings → Security & data → Delete account. Web link: `https://<your-server>/privacy.html` (explains deletion on the website) |

### Data safety form

Data is **encrypted in transit**: Yes. Users **can request deletion**: Yes. **Shared with third parties**: Yes, only when the user enables AI (sent to the AI provider to generate a reply). Not sold.

| Data type | Collected | Purpose | Optional? |
|---|---|---|---|
| Email address, name | Yes | Account management | Name optional |
| Financial info (purchase history / other financial info) | Yes | App functionality | Yes |
| Health and fitness | Yes | App functionality | Yes |
| Photos | Yes | App functionality (journal photos) | Yes |
| Other user-generated content (tasks, notes, journal) | Yes | App functionality | Yes |
| Location, contacts, device IDs, app activity, web history | No | | |

## 4. Testing tracks

1. **Internal testing**: upload the `.aab`, add your own Gmail, install from the opt-in link and check sign-in works.
2. **Closed testing**: create a list with 12+ testers, share the opt-in link, keep it running 14 days.
3. **Production**: apply for production access in the console (Google asks a few questions about the test), then roll out.

## 5. Updating later

Merge the change, run **Release Android app** with a higher version (e.g. 1.1.0), upload the new `.aab` to the same track. Phone users with the GitHub APK install the new APK over the old one.
Note: an APK installed from GitHub and one installed from Play are signed by different keys once Play App Signing is on, so a phone should use one source or the other.
