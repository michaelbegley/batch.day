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
