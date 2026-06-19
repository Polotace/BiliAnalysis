# Video Detail Page — Design Spec for 3 Variations

**Product**: BiliInsight · Bilibili "每周必看" content insight platform
**Page**: `/videos/:aid` — single video detail view
**Output**: 3 standalone HTML prototypes (1440px container, matching existing design tokens)

## Target Audience & Context
Users exploring Bilibili weekly must-watch data. They land here from the video library list or a creator page. They want to understand this video's performance, who made it, what category it's in, and which weeks it appeared in.

## Content Hierarchy (from most to least important)
1. Cover image — the video's visual identity
2. Title — what is this video
3. Creator (name + avatar) — who made it
4. Core stats — view count, likes, coins, favorites (the "interaction score")
5. Secondary stats — share, reply, danmaku
6. Category breadcrumb — where it belongs
7. Description — what it's about
8. Appeared weeks — historical context in the "每周必看" system
9. Duration, publish date, AVID/BVID — metadata
10. "Watch on Bilibili" CTA — the primary action

## Emotional Tone
Data-forward, content-first, clean. The video cover is the hero image — large, immersive. Numbers are precise and well-typeset. Not a dashboard, not a CRM — this is a content discovery experience.

## Design Constraints
- Use BiliInsight design tokens: `#00AEEC` blue, `#FAFAFA` bg, `#111827` text, `#6B7280` secondary, Inter + HarmonyOS Sans SC
- Card radius: 12px default, 16px large
- Shadow: `0 2px 8px rgba(0,0,0,0.05)` default, `0 4px 16px rgba(0,0,0,0.08)` hover
- Max content width: 1280px
- 8px grid system
- No dashboard/admin-panel aesthetics, no 3D charts, no neon glows, no purple gradients

## Three Design Directions

### Version A: YouTube Immersive
- Hero cover dominates top 40% of viewport
- Dark overlay on cover with title + creator + stats
- Below: two-column layout — main content (description, stats detail, appeared weeks) + sidebar (creator card, related info)
- "Watch on Bilibili" as a prominent CTA button on the cover overlay
- Reference: YouTube video page, but cleaner and more data-forward

### Version B: Bilibili Data Layout
- Cover left, info right — horizontal split
- Interaction stats displayed prominently with icon + number pairs
- Creator card with avatar, name, face
- Appeared weeks as a horizontal timeline
- "Watch on Bilibili" as a secondary action under the cover
- Reference: Bilibili video page data density, Chinese community-style stat display

### Version C: BiliInsight Native (Spotify/Steam/Notion hybrid)
- Full-bleed cover as page hero with gradient fade to content
- Stats as the primary visual — large tabular numbers with labels
- Creator as a sidebar profile card
- Appeared weeks as a scrollable chip/tag row
- "Watch on Bilibili" as a floating action or hero CTA
- Reference: Spotify album page + Notion data density + Apple card aesthetics

## Image Assets
- Video cover: use a placeholder (gray rectangle with camera icon) — we don't have real covers in the prototype
- Creator avatar: colored circle placeholder with initials
- All icons: CSS-only minimal indicators, no emoji, no SVG illustrations

## Format
Each version: self-contained HTML file at 1440px fixed width, using inline styles with BiliInsight design tokens. No Vue/React — pure HTML/CSS prototypes.
