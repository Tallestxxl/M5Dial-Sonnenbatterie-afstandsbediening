# Repository Instructions

- Never commit `arduino/sketchbook/SonnenDialRemote/sonnen_config.h`, `config.h`, wifi credentials, Sonnen API tokens, or private IP-specific screenshots.
- Treat `docs/gebruikershandleiding/build_manual.py` as the editable source of the user manual. Do not edit only the generated PDF.
- For every user-visible firmware change, review and update the manual source. This includes controls, labels, signs, limits, timings, refresh behavior, network behavior, power behavior, safety advice, and troubleshooting.
- After changing the manual source, run `scripts/build-manual` and commit the generated PDF together with the source and firmware change.
- Before publishing, render the PDF pages and visually check for clipped text, overlap, unreadable tables, broken images, and exposed secrets.
