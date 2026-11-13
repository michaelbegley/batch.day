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
