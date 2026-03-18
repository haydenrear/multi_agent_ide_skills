# Outstanding Ergonomic Issues

Items that were identified during controller sessions but not yet addressed. Add new items as they surface; move to done or delete when fixed.

---

## 1. No by-itemId endpoint for propagation items

**Problem:** `poll.py` shows `itemId` per propagation item and prints a `--limit N` hint to fetch it via `propagation_detail.py`. But the hint is only positionally correct at the moment of that poll — as new items arrive they push older items to higher `--limit` positions, making stale hints wrong.

**Root cause:** There is no `POST /api/propagations/items/by-id` (or equivalent) endpoint. The only fetch path is `POST /api/propagations/items/by-node` which returns the N most recent items. You can't fetch a specific item by its `itemId` directly.

**Workaround:** Re-run `propagation_detail.py <nodeId> --limit <N>` with a limit large enough to include the item you want, then look at position N. If you still have the itemId from poll output, grep the raw output to find it.

**Fix needed:** Add `POST /api/propagations/items/by-id` to `PropagationController.java` accepting `{"itemId": "prop-item-..."}` and returning the single item. Then update `propagation_detail.py` to support `--item-id <id>` and update the poll hint to use `--item-id` instead of `--limit N`.

---

## 2. poll.py --limit hint reuse only valid at time of poll

Related to #1: the `→ python propagation_detail.py <nodeId> --limit N` hint printed per item in `poll.py` reflects the item's position *at the time of that poll*. By the time you act on it, new items may have been added and the position will be wrong.

**Fix:** Blocked on #1 (by-itemId endpoint). Once that exists, the hint can use `--item-id` which is stable across polls.

---

