# Arm B: fix an issue inside an existing codebase

Workspace: the `inflection` 0.5.1 source tree (MIT), pinned by sha256, with one seeded bug.

**Issue:** `inflection.ordinal(112)` returns `"nd"`, so `ordinalize(112)` gives `"112nd"`. It should be `"112th"`. Same for 111 and 113 (`"111th"`, `"113th"`), and for negatives like -112. 1, 2, 3, 21, 102 must keep working.

Done = the project's own test suite (`test_inflection.py`) passes plus the hidden regression checks. `twoarm finish` runs both.
