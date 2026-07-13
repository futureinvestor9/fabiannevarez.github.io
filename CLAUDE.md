# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a static personal portfolio website (a fork/customization of the "Portfolio Template" by Nisar Hassan) hosted via GitHub Pages at `fabiannevarez.github.io`. It is plain HTML/CSS/JS with **no build step, no package manager, and no dependencies** — everything is hand-authored and served as-is.

## Development

There is no build, lint, or test tooling in this repo. To work on it:

- Open `index.html` directly in a browser, or serve the directory with any static file server (e.g. `python3 -m http.server`) to preview changes.
- Edits take effect on page reload — no compilation step.
- Deployment is automatic: GitHub Pages serves directly from this repo (branch `master`), so pushing to `master` publishes the live site.

## Structure

- `index.html` — the entire page markup, organized into sections identified by `id`: `#top` (header/nav), `#work` (project showcase), `#clients`, `#about`, `#contact`, plus a `footer`. Content edits (name, bio, project descriptions, links, images) are made directly in this file; look for HTML comments marking replaceable content.
- `index.css` — single stylesheet for the whole site, organized into clearly delimited comment-banner sections (Basic Setup, Headlines and Paragraphs, Buttons and Links, Navigation, Header, etc.), each followed by its own `@media` breakpoints for responsiveness. Follow this pattern (BEM-style class names like `work__box`, `header__text-box`) and keep new rules under the relevant section banner rather than appending to the end of the file.
- `index.js` — small, dependency-free vanilla JS with two independent behaviors: (1) toggling a `user-is-tabbing` class on `<body>` to show focus outlines only for keyboard users, and (2) showing/hiding the "back to top" button based on scroll position.
- `images/` — all site images/icons/screenshots referenced by `index.html`; has its own `LICENSE.txt` for image assets specifically.
- `fonts/` — self-hosted font files (`HKGrotesk-Regular.woff`, `Jost-Regular.ttf`) referenced via `@font-face` in `index.css`.

## Conventions

- No CSS/JS frameworks or libraries — keep additions dependency-free vanilla HTML/CSS/JS, consistent with the project's stated design goal.
- Class naming follows BEM-like conventions (`block__element`, `block--modifier`), e.g. `work__box`, `btn--pink`.
- Site content (name, bio, project entries, contact email, social links) lives inline in `index.html`; when updating personal/portfolio content, edit the relevant section directly rather than templating it.
- Recommended project screenshot size is 1366×767px, and all project images should share the same dimensions for visual consistency.
