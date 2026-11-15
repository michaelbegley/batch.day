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
- **"No recipe found" (422) does not fall back.** The AI looked and found none; the on-device reader would only return noise. It shows a clear state with "Choose other screenshots" and "Paste text".
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
