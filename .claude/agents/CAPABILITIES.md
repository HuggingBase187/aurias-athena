# Agent capability matrix

**Last checked: 2026-09-18.** Re-check this file any time an agent's frontmatter (`tools:` or `mcpServers:`) changes — it drifts silently otherwise, which is exactly the bug class this file exists to catch (see "Why this file exists" below).

## Why this file exists

Two real, painful bugs on 2026-09-18 shared one root cause: an agent's frontmatter *listed* an MCP server under `mcpServers:`, but its `tools:` grant didn't include `ToolSearch` — the one tool that actually lets a dispatched agent load and call deferred/MCP tools. Listing an MCP server in `mcpServers:` makes that server's tools *available to be loaded*, but without `ToolSearch` in `tools:`, the agent has no mechanism to load them. The mismatch sat undetected for months of intent (a SKILL.md instruction telling agents to "ToolSearch for Claude-in-Chrome") until a live batch agent reported back "I don't have a ToolSearch function." This file makes that specific mismatch checkable at a glance, for every agent, instead of discovered live.

## Matrix

| Agent | `tools:` (exact) | `mcpServers:` (exact) | `ToolSearch` in `tools:`? | MCP servers actually usable? |
|---|---|---|---|---|
| `sourcing` (`.claude/agents/sourcing.md`) | `WebSearch, WebFetch, Read, Write, Edit, Glob, Grep, Bash, Skill, Agent` | `claude-in-chrome` | **No** | **No — mismatch.** `claude-in-chrome` is listed but unreachable; the agent has no `ToolSearch` to load any `mcp__claude-in-chrome__*` tool. |
| `sourcing-verifier` (`.claude/agents/sourcing-verifier.md`) | `WebSearch, WebFetch, Read, Glob, Grep, Write, Skill, Bash` | `claude-in-chrome` | **No** | **No — mismatch.** Same issue as `sourcing`: `claude-in-chrome` listed, unreachable, no `ToolSearch` grant. |

(Only two agent `.md` files exist in `.claude/agents/` as of this check: `sourcing.md` and `sourcing-verifier.md`. No others found.)

## Confirmed mismatches — instructions pointing at unavailable tools

### 1. `sourcing.md` and `sourcing-verifier.md` frontmatter — the original bug, still structurally present

Both agents' frontmatter lists `claude-in-chrome` under `mcpServers:` while omitting `ToolSearch` from `tools:`. The specific *instruction* that triggered the original incident (a SKILL.md line telling batch agents to `ToolSearch` for Claude-in-Chrome before LinkedIn lookups) was corrected on 2026-09-18 in `.claude/skills/generator-ups-data-enrichment/SKILL.md` (see its "LinkedIn work is Athena's job, not a dispatched batch agent's" section) — enrichment batch agents now leave LinkedIn fields blank and hand off to Athena instead of trying to load the browser tool themselves.

**But the underlying frontmatter mismatch itself was never fixed, only worked around at the instruction level.** `mcpServers: claude-in-chrome` still sits in both agents' frontmatter today, still unreachable by either agent. This isn't urgent to fix (the workaround is sound: Claude-in-Chrome drives Daniel's one real logged-in Chrome session, and giving every dispatched batch agent `ToolSearch` to reach it directly would reintroduce the concurrent-session risk the workaround exists to avoid) — but it means the frontmatter itself is misleading about what these agents can actually do, and a future skill-writer reading `mcpServers: claude-in-chrome` in the frontmatter alone, without reading the SKILL.md-level workaround, would repeat the original mistake.

### 2. `sourcing.md` body — live, uncorrected instances of the same class of bug

Unlike the SKILL.md instruction (fixed 2026-09-18), `sourcing.md`'s own body still directly instructs the agent to do things that depend on the same unreachable `claude-in-chrome` MCP server, with no caveat pointing at the enrichment SKILL.md's workaround:

- **Line 105**: "Only fall back to browser automation (Claude in Chrome) for things the API can't do — renaming/creating tabs, applying cell colours/formatting, or anything genuinely UI-only." As written, this tells `sourcing` to use Claude-in-Chrome directly for spreadsheet UI work — but `sourcing` has no `ToolSearch` to load it.
- **Line 184**: "Use Claude in Chrome (Daniel's own logged-in Chrome, already installed and connected — confirmed 2026-09-15) for anything on LinkedIn, not the sandboxed browser." Same issue — this is the exact instruction class that caused the original incident, just in `sourcing.md`'s own prose rather than the enrichment SKILL.md.

**Net effect:** a `sourcing` agent dispatched directly (not via the `generator-ups-data-enrichment` Skill, which has its own corrected LinkedIn-handling instructions) would still hit the same "I don't have a ToolSearch function" wall these two lines send it toward. Since the enrichment Skill is the actual, current operational path for LinkedIn work (see its SKILL.md), this may be low-impact in practice — but the agent's own `.md` file still tells a bare `sourcing` dispatch to do something it structurally cannot do, and nothing in the file itself flags that. Worth a follow-up: either fix these two lines to point at the same Athena-does-LinkedIn workaround, or fix the frontmatter (add `ToolSearch`) if a bare `sourcing` dispatch doing its own Claude-in-Chrome work is ever actually wanted again — but the second option reopens the concurrent-session risk noted above, so the first is the safer fix.

### 3. `sourcing-verifier.md` — same frontmatter mismatch, no body instruction found

`sourcing-verifier.md`'s frontmatter has the identical `mcpServers: claude-in-chrome` / no-`ToolSearch` mismatch, but its own body text (as of this check) doesn't itself instruct the agent to use Claude-in-Chrome — it points to the `generator-ups-data-verification` Skill's SKILL.md as its operational playbook instead. That SKILL.md does say (section 3, "LinkedIn data") to "reload the company's LinkedIn page via Claude-in-Chrome" — worth flagging as the same class of issue, one file removed: a Skill instructing a `sourcing-verifier`-run task to use a tool that agent can't load. Since `sourcing-verifier` is meant to run as its own subagent specifically *because* it lacks Edit/Bash write access (a deliberate structural boundary — see that SKILL.md's "What you never do" section), it likely also lacks any real path to Claude-in-Chrome for the same reason `sourcing` does. Not yet confirmed against a live failure the way the original bug was — flagging here so it's checked before it causes one.

## How to check this yourself, going forward

For any agent `.md` file:
1. Read its frontmatter `tools:` line. Does it contain `ToolSearch`? If not, it cannot load any MCP/deferred tool, no matter what `mcpServers:` lists.
2. Read its frontmatter `mcpServers:` list. Anything there is a promise, not a guarantee — it only becomes real if `ToolSearch` is also granted.
3. Grep the agent's own `.md` body, and any SKILL.md that dispatches this agent type, for instructions to use a specific tool (`ToolSearch`, an `mcp__*` tool by name, "Claude in Chrome," "browser automation," etc.) and cross-check each one against steps 1-2.
4. Update the table above and note the date.
