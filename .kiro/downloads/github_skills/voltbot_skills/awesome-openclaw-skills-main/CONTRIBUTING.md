# Contributing to Awesome OpenClaw Skills

A curated list of skills for OpenClaw (previously known as OpenClaw, originally Clawdbot... identity crisis included, no extra charge). We organize links to skills hosted in the [official OpenClaw skills repo](https://github.com/openclaw/skills/tree/main/skills).

## Adding a Skill

### Entry Format

Add your skill to the end of the relevant category in `README.md`:

```markdown
- [skill-name](https://github.com/openclaw/skills/tree/main/skills/author/skill-name/SKILL.md) - Short description of what it does.
```

If an author has multiple skills in the same area, please don't add them one by one. Instead, link to the author's parent folder and write a general description. This keeps the list clean and avoids unnecessary clutter.

```markdown
- [author-skills](https://github.com/openclaw/skills/tree/main/skills/author) - Brief summary covering all skills.
```

### Where to Add

- Find the matching category in `README.md` and add your entry at the end of that section.
- If no existing category fits, add to the closest match or suggest a new category in your PR description.

### Requirements

- Skill must be published to the [OpenClaw official skills repo](https://github.com/openclaw/skills/tree/main/skills)
- Has documentation (SKILL.md)
- Description must be concise — 10 words or fewer
- Skill must have real community usage. We focus on community-adopted, proven skills published by development teams and proven in real-world usage. Brand new skills are not accepted — give your skill time to mature and gain users before submitting
- No crypto, blockchain, DeFi, or finance-related skills for now

### PR Title

`Add skill: author/skill-name`

## Updating an Existing Entry

- Fix broken links, typos, or outdated descriptions via PR
- If a skill has been removed or deprecated, open an issue or submit a PR to remove it

## Important

- This repository curates links only. Each skill lives in the official OpenClaw skills repo.
- Verify your links work before submitting.
- We review all submissions and may decline skills that don't meet the quality bar.
- Do not submit duplicate skills that serve the same purpose as an existing entry.

## Help

- Check existing [issues](https://github.com/VoltAgent/awesome-openclaw-skills/issues) and PRs first
- Open a new issue for questions
- Visit the skill's SKILL.md for skill-specific help
