# batch.recipes redesign, 13 Nov 2026

## Brief
- **Who, where:** a budget batch cook on a phone, one hand, with TikTok or Reels screenshots already in the camera roll. Later the same person is in the kitchen with messy hands.
- **The one job:** turn my screenshots into a batch day I can shop and cook from.
- **Flow:** Add screenshots → (AI reads) → the recipe page. Two screens, one wait.

## Problems in the old build
1. The good reader was hidden. Screenshots were read on the phone first, and "Read it with AI" was a small link on the second screen.
2. The Check step was a gate. You had to review a parsed list and pick a mode, servings and meals before seeing anything useful, then tap "Plan my batch day".
3. Three-step bar, an Edit button that went back a page, and a long "How it works" that explained what the screen should have shown.
4. The wait was a thin bar and small thumbnails. A failed read vanished after 3.5 seconds.
5. "They never leave your phone" would no longer be true.
6. With two recipes in the screenshots you only got the first; the rest sat in a text box.

## Decisions
- **AI reads by default.** Choose screenshots and it starts. No setting.
- **On-device reading is the silent fallback** when the AI reader errors, is rate-limited (429), times out (75 s) or the device is offline. The recipe page then says what happened in one line, with "Try AI again".
- **"No recipe found" (422) gets one more try.** On a first read, when the AI finds no recipe (or its text has no ingredients), the screenshots are read on this device before the page gives up. If that finds nothing either, it shows a clear state with "Choose other screenshots" and "Paste text". "Try AI again" from the recipe page does not fall back: it comes back to the recipe with "No recipe found". (Changed on 14 Nov; `breakit2.py` checks it.)
- **The wait is its own screen:** the cook's screenshots with a scan line, what is happening now, a bar that fills against the expected time and never claims to be done, "Usually under a minute", and Cancel. After 40 s it says "Taking longer than usual" and offers "Read on this device instead".
- **Check is gone.** The recipe page builds straight away with 14 meals and the servings the recipe states. Meals and "Recipe serves" steppers sit at the top and the whole page updates as you tap. No "Plan" button.
- **One page does everything:** Batch day or Just scale, then Shop, Cook, Store and Recipe tabs. Recipe is the old Check list (amounts read, original on the right, flags, steps, Edit the text).
- **Dock:** Share and Start cooking. Share opens Send, Copy link and Print. Edit left the dock because editing is on the page.
- **Two or more recipes** in one read become chips you can switch between.
- **Home** shows the flow in three icons (Add screenshots, AI reads it, Shop, cook, store) on the first screen. The long how-it-works list is cut; the scaling rules stay as "How it scales".
- **Privacy line under the button:** "Screenshots are sent to an AI reader and not kept." Under paste: "Pasted text stays on this device." Privacy and About pages rewritten to match.
- **Saving:** a recipe is saved as soon as it is read. The sample is not saved unless you change it, cook it or share it, so "Returning visit" keeps meaning a real batch.
- More than 6 screenshots: the first 6 are read and the page says so.
- Spacing is now all on 4/8/12/16/20/24/32/40 (the old file had 2, 3, 7 and 14 px values).

## Analytics
- `Plan {mode, from}` now fires when a recipe page is built from screenshots, paste or the sample. It used to need a tap, so expect it to run higher than before 13 Nov. Filter `from: sample` out for the go/no-go.
- New: `AI read {shots, result}` with result ok, none, limit, timeout, error, cancel or choice.
- New: `Device read {why, ok}` with why offline, limit, timeout, error or choice. This is the fallback event.
- `Read with AI` now means a tap on "Try AI again".
- Unchanged: Cook mode, Share, Open shared link, Reopen saved, Returning visit, Install prompt, Installed.

## Not done
- No change to the scaling engine. Only three strings in engine.js lost their em dashes, which changes two lines of test output.
- No count-up stats row and no steam puff. The big numbers moved into the steppers and the line under the title.
- No two-column desktop layout. Desktop keeps the 640 px column.
- The 30 to 40 second estimate is not shown as a countdown. I only have one data point (4 screenshots), so the copy says "Usually under a minute".
- Old helper scripts (shot.py, shot2.py, shot3.py, even.py, savetest.py, dbg*.py) still point at the old ids. Use shots.py, even2.py, breakit.py and breakit2.py.

## Checks
- build.py clean, 4 script hashes. No console errors or CSP violations in any run.
- breakit.py 71 of 71, breakit2.py 26 of 26 (reader and on-device reader mocked).
- No sideways scroll from 195 to 2560 px, light and dark.
- Evenness (even2.py, 390 / 1440 / 2560): every left/right and top/bottom pair within 1 px; tabs 88×4, flow columns equal, steppers 148×52; no tap target under 44 px.
- Contrast: lowest text pair is secondary text on grey fill, 4.66:1 light, 5.42:1 dark.

## Fixes after stress test (13 Nov 2026, round 2)
Source: `breakit-redesign-report.md`. Every fix has a check in `breakit3.py`.

### Breaks it
1. **Saved batches are never dropped.** The cap is 200 and nothing trims. At 200 a new recipe stays open in memory and the page says "My batches is full. Remove a few to save this one." with a link to My batches. It saves by itself once there is room. Editing an existing batch always saves, even in a list longer than 200. The sample still doesn't count.
2. **Unreadable files are skipped.** Each file is test-opened first. Good ones are read with AI and the page says "1 file couldn't be opened." If none open: "Those files couldn't be opened. Choose screenshots (PNG or JPG)." The AI isn't called or blamed; analytics gets `AI read {result: badfile}`. No broken tiles.
3. **Grocery ticks are saved with the batch** (`k` in the record) and come back on reload and reopen. They survive stepper and mode changes and go only when the item's text changes. The same item listed twice gets its own tick.
4. **Share links are capped at 20 KB of text.** Inflating stops early, so the 14 KB bomb is refused in under 2 s and nothing is stored. Copy link says "Too long for a link" above the cap.

### Looks wrong
1. `[hidden]` now wins, so the copy-text box is invisible and out of the tab order.
2. The reading screen has its own history entry. Back is Cancel and lands on home. A finished read replaces that entry, so one Back from the recipe goes home.
3. 195 px (200% zoom): tabs go 2×2, the cook-order minutes and the amounts table stack, cook-mode and dock buttons shrink, Share shows its icon only, long links wrap on Privacy and About. A long cook step now scrolls from its first line instead of being clipped at the top.
4. Titles keep every script. Only hashtags and control characters are removed. The heading uses `dir="auto"`.
5. Focus goes to the heading when reading starts, on a fail state and when the recipe page builds; back to Start cooking after cook mode; to the next row after removing a batch. Tab stays inside the Share sheet and cook mode. Cook steps are announced through a live region.

### Minor
- `Returning visit` fires once per browser session, and not in the session that made the first batch.
- `AI read` and `Device read` record what the cook ended up seeing (`none` / `no` when nothing usable came back).
- "The steps look cut off" only when the last step ends on a comma or a joining word.
- Odd amounts (over 50 lb, negative, 1e9) get "check amount" on the grocery row and "Check this amount" under Recipe, plus the alert.
- Steppers take whole numbers 1 to 999. Zero and negatives become 1; hex, letters and blanks go back to the last good value.
- Corrupt saved entries are not listed. They are left in storage untouched.
- An empty share link says "That link didn't open".
- A removed batch doesn't reopen with Forward.
- Offline with no on-device reader: "Try again" is the main button.
- Just scale starts at the recipe's own servings, and meals and servings keep separate numbers.
- Closing cook mode no longer jumps the page to the top.

### Not fixed
- M4 (non-English lines parsed as groceries, RTL body text): engine work, skipped as agreed.
- M7 (recipe chips gone after reload) and M8 (reload returns to the Shop tab): skipped as agreed.
- A title made of markup shows as plain text (escaped). Left as is under the "only hashtags and control characters" rule.
- Absurd amounts are warned about, not blocked. "99 lbs" still scales.

### Checks on the final build
- build.py clean. No console errors, CSP violations or dialogs in any run. Engine test output unchanged from the first redesign build.
- breakit.py 71 of 71, breakit2.py 26 of 26, breakit3.py 31 of 31.
- Tester's scripts (copied to `/home/claude/bk2-rerun`, screenshots in `breakit-r2-after/`): a, b, b2, c, d, d2, s, p2 all run. Every B and L finding and the fixed M items now pass. One step in d.py was changed: it tapped a stepper on the deleted recipe, which no longer reopens. b2's `dbl` case errors in the script itself, as it did in the original run.
- No sideways scroll from 195 to 2560 px. Evenness pairs within 1 px at 390, 1440 and 2560; no tap target under 44 px.

## Small touches (14 Nov)
Batch 1 of `batch-recipes-microinteractions-plan.md`: items 1, 2, 3, 4, 6, 7. CSS and a little JS in `template.html`; engine untouched; no new libraries or requests. Checks in `breakit4.py`.

- **Tick draws itself, with a count.** Circle fills (150 ms), the check wipes in left to right (180 ms, a mask on the checkbox), a line runs across the words (250 ms). The line is a background on an inline `.tx` span, so it follows wrapped lines; print falls back to line-through. The heading shows "3 of 17", then "All set" (`#gcount`, `aria-live="polite"`, empty at zero).
- **Hold speeds up, soft stop.** Hold repeats at 110 ms, then 60 ms once the button has been held 1.5 s. While held only the number changes; the page is drawn once on release. At 1 or 999 the number nudges 4 px and settles (200 ms) and that button dims to 40% (class `end`, not `disabled`, so it still answers a tap with the nudge).
- **Things close the way they opened.** Share sheet: box drops 12 px and fades (250 ms), backdrop fades (200 ms). Cook mode drops 12 px and fades (250 ms). Both get class `out`, then `hidden` when the animation is over; `menuOpen()` and `cookOpen()` treat `out` as closed. Focus, scroll lock, wake lock and history are put back straight away. A removed batch row: the list, storage and focus update at once, and an `aria-hidden` copy of the row (`li.gone`, no controls in it) folds shut in 200 ms.
- **Amounts show they changed.** Every amount carries `data-a` (shop amount, recipe amount, cook minutes and notes, pots, freezer and fridge lines). After a stepper or number-box redraw, the ones on screen whose text changed get `.chg`: up 6 px and fade in, 180 ms. So does the "3.5× the recipe" line. Runs once on release after a hold. Mode, tab and recipe changes don't trigger it.
- **Recipe name in the top bar.** When the title scrolls under the bar, "batch.recipes" cross-fades (200 ms) to the recipe name: one line, ellipsis, tap to go to the top. The copy is `aria-hidden` and not focusable; the logo link comes back if it gets keyboard focus.
- **Rows respond to touch.** Grocery rows, saved batches, share rows, chips, tabs and the remove button fill grey (`--press`) at once and fade over 150 ms on release. Text links dim. Tap flash is off site-wide. Hover fills only apply on devices that hover. An empty `touchstart` listener makes `:active` work on iOS. Copy swaps to a drawn check and "Copied" for 1.6 s. Grocery rows and saved rows got 12 px side padding (negative margin) so the fill has room; the divider moved from the label to the `li`.
- **Reduced motion:** end states with a 0.2 s fade, no movement. The removed row just goes (no fold).
- **Also fixed:** closing cook mode moved the recipe page to an old scroll position (the browser restoring scroll on the history step back). `history.scrollRestoration='manual'` is set when cook mode opens.
- **Not tested here:** real iOS Safari. Check on the phone: press fills on rows, the check wipe (CSS mask), the strike line on a wrapped item, hold on + (finger drift cancels the hold and redraws), and the top-bar title with the address bar collapsing.

## Phase 1 (14 Nov): backup, staples, aisle order
From `batch-recipes-features-plan.md`. Checks in `breakit6.py` (81) and `test_aisle.js` (11, run by breakit6). Not committed or deployed by the builder.

- **Aisle order.** The grocery list is grouped under small grey labels in store order: Produce, Meat & seafood, Dairy & eggs, Bakery, Canned & jarred, Dry goods & grains, Spices & oils, Frozen, Other. Empty sections don't show. The keyword map is in `engine.js` (`AISLES`, `aisleOf`, `aisles`, `shopList`): first match wins, so "garlic powder" is a spice before "garlic" is produce and "chicken broth" is a can before "chicken" is meat. No lookbehind in the patterns (old iPhones). Ticks are still saved by item name, so old saved ticks keep working. Copy has the section names; Add to list and the Send text don't.
- **Staples.** "Mark staples" under the list shows an "Always have" button on every row; it turns into "Done". A marked item moves to "Check your pantry (N)" at the bottom, closed until tapped. In there each row keeps a pressed "Always have" to undo it, and can still be ticked. Stored by folded name in `bd-staples` (`stapleKey`: lower case, no punctuation, simple plurals), so it holds for every recipe. Staples aren't in the "N of M" count or in Add to list; Copy puts them last under "Check your pantry". Marking a staple doesn't save the sample.
- **Backup.** My batches has quiet "Back up" and "Restore" links. With no batches the card is hidden, so the footer shows "Restore backup". The file is `{app, v:1, at, batches, settings:{theme, staples}}`, named `batch-recipes-backup-YYYY-MM-DD.json`. Touch devices that can share a file get the share sheet; everything else downloads. Restore takes a `.json` up to 2 MB, refuses it whole unless the app, version, settings and every batch check out, merges by id (or the very same text), keeps the newer copy, removes nothing, and stops at 200 with "My batches is full. Added 2 of 5." Staples are added to; the theme is only applied when none is chosen here.
- **Nudge.** From the third batch a small card in My batches says "Back up your batches. They're only on this device." with Back up and Not now. It goes for good after either (`bd-bkn`, `bd-bk`) and waits while the iPhone Home Screen tip is showing.
- **Persist.** `navigator.storage.persist()` is asked once, after the first saved batch (`bd-ps`). Firefox may show its own permission prompt for this.
- **Events:** `Backup {how: share|download}`, `Restore {ok: yes|no, n}`.
- **Spacing:** label to rows 0, section to next label 16, heading to first label 8, pantry line 8 above, rows 48, "Always have" 44 high and flush with the card edge, links 44 high with 24 between.
- **Tests changed:** breakit3 (B3) and breakit4 (hold) picked "the first row" and meant the chicken; they now pick it by name.
- **Not tested here:** real iPhone and Android. See the builder's report.

## Phase 1b (14 Nov): share picture, freezer labels, store links
Checks in `breakit7.py` (109). Numbers from `p1b_even.py`. Screenshots in `phase1b-shots/` (`p1b_shots.py`). Not committed or deployed by the builder.

- **Share picture.** New "Share picture" row in the Share sheet. It opens a sheet with Story / Pinterest, the picture itself (the PNG that will be sent, shown as an image so a long press can save it), one button and Cancel. Story (1080x1920) is the default; Pinterest is 1000x1500. Drawn on a canvas: the pot (same six paths as `brand/mark.py`, 56 grid, weight 2), the dish, "14 meals" (servings in Just scale, "1 meal" for one) and batch.recipes with the accent dot. A white card on the grey ground (#f5f5f7), always light. The story card keeps 256 px clear top and bottom for the apps' own buttons. Titles balance over up to 3 lines, shrink from 88 to 64, then end in an ellipsis; the count shrinks to fit.
- **Cost per meal (Phase 2)** has its place: the line under the count (`cost` and `slot` in `drawPic`). While `cost` is null nothing is drawn and the block is centred without it.
- **Font:** a loaded Inter face from `document.fonts` if there is one, else the page's own system stack. The page loads no web font today, so phones draw it in their system font.
- **Out:** phones that can share a file get the share sheet with the PNG alone (`navigator.share({files})`); everything else downloads. The PNG is made when the sheet opens, so the tap goes straight to the share sheet. `Share picture {size: story|pin, how: share|download}`.
- **Freezer labels.** New card on the Store tab: the label at real size, a Cooked date (today, editable), "Print labels" and "Save as image". One label per meal: dish, "1 of 14", Cooked date, "Use by" with a line to write on, and a third row that is the recipe's own reheat sentence if its text has one (110 characters or fewer), else a line to write on. No storage times are printed anywhere on a label.
- **Print:** Avery 5160 on US letter, 3 across and 10 down, labels 2.625 x 1 in, 0.5 in top, 0.1875 in sides, 0.125 in between columns, no gap between rows, 30 to a sheet. `body.plabels` hides everything but `#labels`; the `@page{size:8.5in 11in;margin:0}` rule is added for that print only and removed on `afterprint`, so printing the recipe keeps its margins. No borders on printed labels.
- **Image:** one PNG strip, one label per row, 788 x 300 px each (300 dpi), a hairline between rows, 30 rows to a file. `Labels {how: print|share|download}`.
- **Store links.** `const AFF={instacart:'',amazonTag:'batchrecipes-20'}` next to `AD_SLOT`. An empty value means the row isn't on the page. `window.__BD_AFF` overrides it on localhost only (tests). Values are checked: https URL, tag of letters, digits and hyphens.
  - Shop tab, under the list: "Shop on Instacart" / "We may earn from purchases". **Off** (empty URL). When on: the unticked, non-staple list goes to the clipboard, toast "List copied", the URL opens in a new tab. With `AFF.instacartApi=true` it POSTs `{title, items:[{name,text}]}` to `/api/shop-list` and opens the returned https link; 503, a bad answer or 8 s of silence falls back to the URL.
  - Store tab, under Where it goes: "Freezer containers" to an Amazon search with the tag, with "As an Amazon Associate I earn from qualifying purchases." under it. **On.** Only when the plan has portions (not on a bake).
  - Both: `rel="sponsored noopener"`, new tab, at most one each, not printed, never on home, in Just scale or in cook mode. `Shop link {to: instacart|amazon}`.
- **Privacy page:** new "Affiliate links" section with the Amazon sentence; date now 14 November 2026.
- **Spacing:** sheet pad 16, gaps 16, Cancel 8 from the button and the sheet's foot; labels card gaps 8; store link 8 above and below its hairline (16 under the Store blocks), 4 px pad inside the 44 px target.
- **Not tested here:** real iPhone and Android, a real printer and a real sheet of 5160. See the builder's report.

## First-visit tour (14 Nov)
Checks in `breakit8.py` (182). Numbers from `tour_even.py`. Screenshots in `tour-shots/` (`tour_shots.py`). Video script in `tour-video-script.md`. Not committed or deployed by the builder.

- **Offered, never started.** On a first visit a small grey card sits under "Choose screenshots", inside the same white card: "New here? Quick tour", Show me, Skip. Nothing overlays the page. One row on desktop, two on a phone.
- **First visit means:** nothing of ours (`bd-` keys) was stored on this device before this session, no saved batches, no shared link, and `bd-tour` not set. `bd-seen` marks the device; `bd-new` (session) keeps the answer for reloads in the same visit. If storage is blocked the card is not shown, because it couldn't be dismissed for good. People who came before 14 Nov and never stored anything get the offer once.
- **Skip:** card goes, toast for 4 s: "Tour's at the bottom of the page anytime." The footer always has "Take the tour".
- **Show me:** five bubbles, each on the real control with a pointer and a 2 px accent ring 4 px outside it.
  1. Choose screenshots: "Add screenshots of any recipe. Here's a sample." Next loads the sample.
  2. Meals stepper: "Set how many meals."
  3. Shop tab (bubble above it, so the list shows below): "Your grocery list. Tick as you shop, or send it to your list app." Without a share sheet the second half is left out.
  4. Start cooking: "Cook one step at a time. The screen stays on." Without Wake Lock the second sentence is left out.
  5. Share: "Save it or share it." The button says Done.
- **Bubble:** 320 wide (window minus 32 on small phones), pad 16, text to buttons 12, Skip tour and Next 44 high, 8 between them, five 8 px dots with "2 of 5" as their label. 16 from the control. It goes below the control, or above when there is no room (step 3 prefers above), and stays 16 from the window edge with the pointer on the control's middle. Its place is worked out every frame, so it follows scroll, rotation and the dock sliding in.
- **Dim:** 12% black around the ring. Everything stays readable. A tap anywhere off the bubble, Escape or the phone's Back ends the tour. The tap is swallowed, so it doesn't press what is under it. (Round 3: not a tap that lands where the bubble just was; see the last section.)
- **The sample in the tour** is opened with `from: 'tour'`, in Batch day. It is not saved and `Plan` fires with `from: tour`, so filter it out with `sample`. After the tour it follows the sample rule: saved only once you change it, cook it or share it.
- **End:** `bd-tour` = `done` or `skip` (outside counts as skip). The card never comes back. On the plan, focus goes to the recipe title; on home, to the button that started it. Ending early shows the toast (on the plan it says "the home page"), except when the tour was started from the footer.
- **Access:** the bubble is a dialog labelled "Tour", described by its text; the text is `aria-live`; focus moves to the bubble; Tab stays on its two buttons. Reduced motion: no rise, it just appears.
- **Events:** `Tour {step:0, choice: show|skip|link}` (link = the footer), `Tour {step, end: done|skip|outside}` with the step it ended on.
- **Clear of the rest:** the offer needs zero batches and the Home Screen tip and backup nudge need at least one, so they never share a screen. The tour sits above everything (z 70) and clears any toast when it starts. The sample has no saved id, so the install tip doesn't show on it.
- **Spacing:** hint to offer 16, offer pad 16, text to buttons 12, Show me to Skip 16.
- **Not tested here:** real iPhone and Android. See the builder's report.

## My freezer, QR on labels, the lost tap (14 Nov)
Checks in `breakit9.py`. Numbers from `freezer_even.py`. Screenshots in `freezer-shots/` (`freezer_shots.py`). Not committed or deployed by the builder.

- **The lost tap.** Typing in Meals or Recipe serves and then tapping a button lost the tap: the box's `change` (on blur) rebuilt the page under the finger. Now, when the change arrives during a press, the plan and the saved batch are updated at once (`build(false, true)`, no page writes) and the page is drawn after the click has been handled. So the button that was tapped is still there, and it acts on the new number (cook mode, Print labels and I cooked this all use 20, not 14). A press runs from `pointerdown` until its click; 400 ms after `pointerup` or 1.5 s after the change are the backstops. Enter, Tab and the steppers redraw at once as before.
- **I cooked this.** New "My freezer" card at the end of the Store tab: the split in words ("10 meals for the freezer, 4 for the fridge."), a Cooked date (the same date as the labels; the two boxes move together) and the button. Also a quiet pill on cook mode's last screen. Batch day only. It saves the batch if it wasn't saved (the sample too). Toast "Added to My freezer" with Undo; "See My freezer" then shows under the button.
- **Twice on one day** for the same batch asks first, inline, no dialog: "Already added for Nov 14. Add it again?" Add again / Cancel.
- **Storage:** `bd-freezer`, a list of `{id, bid, title, date, fz, fr, fz0, fr0, at}`: batch id, cooked date (YYYY-MM-DD), meals left in the freezer and fridge, as cooked, last change. `zx` / `rx` mark a removed row. Cap 500. Entries that can't be read are skipped and left in storage. The split comes from the engine: `plan.portions = {fridge, freezer}` (new, the same numbers as the Store text).
- **Home card.** "My freezer" sits under Paste text / Try a sample, above the three icons, so it shows on the first screen of a phone. Only when it has something. Total line "12 meals in the freezer" (fridge count when the freezer is at 0, "Nothing left" at 0 and 0). "In the fridge" group first, then "In the freezer", each oldest first. A row: dish, "9 left · Cooked Nov 12" (year only when it isn't this year), tap the dish to open the batch, "Ate one" on the right.
- **Ate one** counts down, the number and the total flash, a light buzz, toast "Ate one. 9 left" with Undo for 4 s. At 0 the row says "None left" and the button is "Remove". Remove takes that row (toast with Undo); the entry goes when both its rows have.
- **No storage or use-by times** in any of this. The label still has "Use by" as a line to write on. (The engine's Store text still says "eat within 4 days", from before; untouched.)
- **Backup and Restore** carry `freezer` (same file, still `v: 1`; older backups without it still restore). Merged by entry id, the copy with the later `at` wins, nothing here is removed. One bad entry refuses the whole file, like batches. A row whose batch is already here under another id (same text) is pointed at that one.
- **QR on labels.** Every label has a code that opens `https://batch.recipes/#b=<batch id>`. Encoder is `qr.js`, written for this page (byte mode, versions 1 to 6, levels M, Q, H, all 8 masks with the standard penalty pick), inlined by `build.py` in the same script as the engine, so still 4 script hashes and no new host. A batch link is version 3, level M: 29 modules.
- **Label layout with the code** (2.625 x 1 in): code 0.62 in square, top right on the label's own padding (0.08 in top, 0.14 in right). "1 of 14" centred under it. Words on the left in four rows, 0.08 in apart: dish, Cooked, Use by, then the reheat line or a line to write on. 0.1 in between words and code. The dish goes from 11pt down to 9pt to fit, then an ellipsis. The image strip draws the same layout at 300 dpi (code 186 px). An id too long for version 6 prints the old label without a code.
- **Ids hold still.** The id a label carries is the one the batch is saved under, even on the sample before it is saved (`batchId()`). Pasting or reading a recipe whose text is already saved keeps that batch's id instead of making a new one, so old labels and freezer rows still open it.
- **Opening `#b=`.** Same path as My batches (`openRec`). Not found: a line on the home page, above the button, that stays: "This batch isn't saved on this phone." ("device" on a computer). It goes once a recipe is opened. A first visit from a label doesn't get the tour offer.
- **Events:** `Cooked {portions}`, `Ate one`, `Freezer open {from: card|label, ok: yes|no}` (a batch opened from the home card or from a label's code).
- **Spacing:** home card 24 above and below, heading to total 0, total to group label 16, label to rows 0, group to next label 16, Ate one 44 high and 8 from the dish. Store card: 8 between heading, line, date row and button; 16 from the labels card.
- **Tests changed:** breakit6 (backup keys now include `freezer`) and breakit7 (label rows: the count moved under the code, Cooked and Use by are on their own rows).
- **Not tested here:** a real phone camera on a printed label, real iPhone and Android taps. See the builder's report. One known limit: on iPhone, a camera scan opens Safari, and a Home Screen copy of the site keeps its own storage, so batches saved in the Home Screen app won't be found from a scan.

## Guides: search pages (14 Nov)
Checks in `breakit10.py` (351) and `test_guides.js` (run by breakit10). Screenshots in `guide-shots/` (`guide_shots.py`). Not committed or deployed by the builder.

- **What they are.** Ten pages, one question each, at clean URLs (`/how-much-rice-for-meal-prep`). H1 is the question, the first paragraph is the answer with numbers, then a small calculator, a table where it helps, How it works, Questions, "Plan your own recipe" and three more guides. `/guides` lists them; About has the list; both footers link to Guides.
- **Where the numbers come from.** `guides.js` (run by `build.py` with node) holds each page's `calc()`. It runs on `engine.js` at build time to write the answer paragraph, tables and the calculator's first state into the HTML, and the same `calc()` runs in the browser when a stepper moves. So a page with scripts off already has the numbers. No number is typed by hand; percentages and pot sizes are measured off the engine.
- **Engine.** Untouched. Pages load `site/engine.js`, a copy `build.py` writes. Each page has one inline script (the calc and the stepper wiring), hashed into that page's own CSP meta, the same model as home.
- **No portion rule.** The engine has none for meat, so the chicken page scales the recipe's own amount. Rice uses the engine's ⅓ cup dry a meal, and says it's an estimate.
- **Common amounts tables** (double, triple) only list rows the engine's rounding gets exactly right. ⅓ cup doubled is left out: the engine rounds cups to the nearest quarter and gives ¾ cup.
- **No keep times** on any guide, and no diet or health claims. The engine's "eat within 4 days" is not shown.
- **Shell.** `pages/_shell.html` got `{{HEAD}}` and `{{CSS}}` slots, the card and stepper colours, and 44 px footer links. Guide styles are in `pages/_guide.css` (also used by About for the list). Steppers are the home page's: 148 x 52, hold to repeat, whole numbers, dim at the ends.
- **Also new:** `sitemap.xml` (14 URLs) and `robots.txt` (allow all, points to the sitemap). "Plan your own recipe" sends `Guide plan {guide}`.
- **Spacing:** h1 to answer 16, answer to card 24, card pad 20, rows 8, result 16 under its hairline, sections 32, question to answer 4, button 32 above.
- **Not tested here:** real iPhone and Android.

## Break test round 3 fixes (15 Nov)
Report: `breakit-batch.recipes-20261115.md` (2 breaks it, 5 looks wrong, 8 minor). Checks in `breakit11.py`: every finding is run on the old build (a copy of the site at 6049b1c, `/tmp/r3-base` or `BD_OLD`), where it must show the break, and on this build, where it must pass. Not committed or deployed by the builder.

- **Stray second taps (B-01).** Three layers, because the same thing can happen anywhere a tap moves the page:
  1. *Everywhere:* a tap within half a second of the last one, within 30 px of it, on a different control, when the first control is no longer under that spot, is dropped. Tapping the same control twice still counts twice (Meals +, Ate one, a tick), and a redrawn button counts as the same button (it is matched by its id or its `data-` values). Keyboard presses are never dropped. This also stopped a double tap on a saved batch from opening cook mode (the second tap used to land on Start cooking).
  2. *Lists that lose or move a row* (My batches x, My freezer Remove, Always have): that list's row buttons wait 0.8 s after a row goes, so a slower second tap (the report tried up to 0.6 s) does nothing either.
  3. *The row keeps its place.* The removed row's copy fades at once, holds its height for 0.45 s, then folds shut in 0.2 s. So nothing slides under a finger that is still there. Hidden from screen readers, nothing in it to tap. Reduced motion: it holds, then goes, no fold. My freezer rows now do this too (only when their group is still there).
- **Ate one on the last meal** turns the button into Remove under the finger; Remove on that row waits 0.8 s.
- **One Undo for a run.** Removals (or Ate one taps) made while the Undo toast of the same kind is still up share one Undo, which takes all of them back, newest first, to their old places. The toast says "Removed 2 batches", "Removed 2" (freezer rows), "Ate 3. 7 left". A different kind of toast starts a new run, as before.
- **I cooked this when My batches is full (B-02).** Nothing is added to My freezer, because the row would point at a batch that isn't saved. The card shows the same words as the note at the top of the page, "My batches is full. Remove a few to save this one.", with the My batches link, above the button. Cook mode's pill shows the same line and link (the link leaves cook mode first). Once there is room (here or in another tab) the batch saves and the note goes. A freezer row is now always tied to a saved batch, so the same-day question always runs.
- **Tour (L-01, L-03).** Next ignores a second press within a third of a second, so a double tap is one step. A tap off the bubble still ends the tour, except in the first 1.2 s of a step when it lands where the bubble (or Show me) was: that tap was meant for Next. On resize or rotation the control is scrolled back on screen and the bubble's side is chosen again (and once more 0.35 s later, when the browser's bars have settled); the bubble is clamped to the window, 8 px from top and bottom.
- **Cooked date (L-02, M-08).** One date for the labels and My freezer, and it is always a real day from two years back to the end of next year. While typing, only a full date in that range is taken (a year passes through 0002, 0020, 0202), so 1926 or 9999 never reaches a label or a row. On leaving the box a two-digit year becomes this century (26 is 2026), anything else goes back to the last good date, and the box shows the date in use. An emptied box means today, for both. (Before, an emptied date left a line to write on; that is gone.)
- **404 (L-04).** `404.html` is a real page from the shell: "Page not found", "Go to the home page", "See the guides", `noindex`, not in the sitemap. All its addresses start at the root, so it works at any depth. Vercel serves it with status 404 for any address that isn't a file; `cleanUrls` is unchanged.
- **Backups (M-01).** A file is refused whole, with the usual one line, when a batch has meals or servings that aren't whole numbers 1 to 999 or a save time past 2099, or a freezer row has a day that isn't on the calendar (31 Feb). Entries already in storage are read as before.
- **Tiny factor (M-02).** Under 0.1× the factor shows two figures ("0.012× the recipe"), never "0×".
- **Two tabs (M-03).** The page listens for `storage`: My batches, My freezer, staples and the theme follow the other tab. A batch removed in another tab is closed here (home, toast "Removed Chili in another tab"), so this tab can't save it back. Two tabs changing the same batch: the later change wins.
- **Add to list (M-05).** One share sheet at a time: a tap while one is open does nothing (all share buttons), and the second tap of a double tap on Add to list is ignored even on phones that answer `share()` at once.
- **Save as image (M-06).** More than 3 files (90 labels) asks first, in the card: "That's 34 images, 30 labels each." Save 34 images / Cancel. Strips are drawn and turned into files one at a time, so a long run never holds every canvas at once.
- **Canonical links (M-07)** on home, About and Privacy.
- **Printing never saves the sample.** Print labels no longer saves a sample that was only looked at, the same as Print in the Share sheet. Cooking, sharing and Save as image still do. So that labels printed that way still work, the untouched sample has one fixed id, `sample`: its code is `#b=sample`, which opens the saved copy if there is one and otherwise the sample itself, on any phone. (An edited sample is a different text and gets a normal id.)
- **"No recipe found" (422)** line under Decisions corrected: a first read does fall back to this device.
- **Spacing:** full note 8 under the date row and 8 above the button, link 44 high; labels question 8 under the hint, pad 16, buttons 44; 404 page h1 to line 16, line to button 32, button to link 8.
- **Tests changed** (they tapped faster than the new guards allow, or checked behaviour that changed on purpose): breakit3 (one pause before Update), breakit4 (wait for the held row), breakit6 (staple taps paced 0.9 s), breakit7 (emptied date is today), breakit8 (Next paced 0.65 s; 12 presses at once is one step), breakit9 (pauses before Add again, Cancel and a second Remove; printing doesn't save the sample; the hidden row copy is skipped).
- **Not tested here:** real iPhone and Android taps, rotation and share sheets; the date picker on phones; the live 404. See the builder's report.
