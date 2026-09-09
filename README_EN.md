# Tongyu AI Customer Service

> A universal, standalone, zero-dependency website AI chatbot. Any website can embed it with a single `<script>` line.

![license](https://img.shields.io/badge/license-MIT-green)
![deps](https://img.shields.io/badge/dependencies-none-blue)

## What it solves

Small teams want an AI chatbot but are put off by "buy a SaaS, paste an API key, send data to a third party, lock into one vendor". Tongyu AI Customer Service flips that:

- **Universal**: config-driven. Edit `config.json` for your company / product / language / prompt — no code changes.
- **Standalone**: pure Python standard library, `python server.py` just runs. No third-party packages.
- **Embed anywhere**: paste the `widget/embed.js` `<script>` into your page; a chat bubble appears bottom-right.
- **Multilingual**: auto-detect zh / en / ru; add or remove any language in config.
- **Lead capture**: visitor contact info is saved to `leads.jsonl` for sales follow-up.
- **Optional RAG**: drop `.md` files in `knowledge/`; the bot cites your docs instead of guessing.
- **Swappable brain**: defaults to the local Tongyu Engine (Ollama-compatible, 11434); one config line switches to OpenAI / Qwen / SiliconFlow or any OpenAI-compatible endpoint. Runs on a low-spec PC with a local model.

## Quick start

```bash
cp config.example.json config.json
# edit config.json: site name, contact, system prompt (optional knowledge/)
python server.py
```

Open `http://127.0.0.1:8787` for the demo site.

## Embed in your site

```html
<script src="http://YOUR_SERVER:8787/embed.js"
        data-server="http://YOUR_SERVER:8787"
        data-title="Chat" data-lang="zh" async></script>
```

## About shipping to App Stores

MIT licensed: you may build closed-source commercial products on top of it and publish to app stores **without open-sourcing your derivative** — just keep the original MIT copyright notice. Open-sourcing this core does not block your future paid / shipped product.

## License

MIT

---

## Knowledge Planet · 零基础AI造应用·同宇圈

Want structured tutorials on building AI apps, AI audiobooks, and local-model setups? Join my Knowledge Planet for full guides, Q&A, and source updates:

https://wx.zsxq.com/group/48882488185118

Brought to you by Tongyu (AI Audiobook · Tongyu Productions). MIT licensed — free to use, modify, commercialize, and publish.
