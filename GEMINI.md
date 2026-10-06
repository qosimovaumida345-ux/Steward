# Workspace Directives & Engineering Standards (Steward / CustomAgent)

## 1. Code Integrity & Verification Mandate
- Always verify all imports, syntax, and dependencies before declaring work complete.
- Run `python -m py_compile <file>` on touched Python files.
- Run `python -m pytest` to ensure full test suite passes.
- Zero tolerance for unresolved `ImportError`, `SyntaxError`, or hallucinated symbols.

## 2. Premium UI Design & Anti-AI-Slop
- No raw emojis as substitute icons in buttons, headers, or navbars.
- Use Lucide icons / SVG vector assets with crisp rendering.
- Add physical micro-interactions: tactile button press (downward Y translation), hover glow, spring animations.

## 3. Roblox Elite UI Guidelines
- When authoring Luau UI: use 3D mechanical button geometry, SoundService click and hover sound feedback, tiled stud textures (`ImageLabel.ScaleType = Tile`), and production-grade responsive layouts.
- Refer to `.agents/skills/roblox-elite-ui/SKILL.md`.

## 4. Advanced Computer Use & Desktop Control
- For desktop control and GUI automation: use Desktop_Control MCP and the Perception-Action-Verification (PAV) loop.
- Refer to `.agents/skills/advanced-computer-use/SKILL.md`.
