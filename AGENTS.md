# Repository Instructions

- Never commit `arduino/sketchbook/SonnenDialRemote/sonnen_config.h`, `config.h`, wifi credentials, Sonnen API tokens, or private IP-specific screenshots.
- Treat `docs/gebruikershandleiding/build_manual.py` as the editable source of both the user manual and installer manual. Do not edit only the generated PDFs.
- For every user-visible or installer-relevant firmware change, review and update the manual source. This includes controls, labels, signs, limits, timings, refresh behavior, network behavior, power behavior, configuration, installation, safety advice, and troubleshooting.
- After changing the manual source, run `scripts/build-manual` and commit both generated PDFs together with the source and firmware change.
- Before publishing, render every page of both PDFs and visually check for clipped text, overlap, unreadable tables, broken images, and exposed secrets.
